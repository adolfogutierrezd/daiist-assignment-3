"""
Assignment 3: build the index (`main.py index`).

Downloads the three Spanish sports laws from the BOE open-data API into
corpus/ (git-ignored), extracts and cleans the current text of every article,
chunks it with two designs, embeds the chunks with Gemini and stores them in
index/ (ChromaDB). Every vector is saved as soon as it arrives, and only chunks
without a saved vector are embedded, so a crash or the daily quota loses nothing.

server.py's add_document tool imports chunk_file() and embed_and_store().
"""

import hashlib
import re
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

import chromadb
import httpx
from google import genai
from google.genai import types

from api_key import load_api_key

ROOT = Path(__file__).resolve().parent
CORPUS = ROOT / "corpus"
INDEX = ROOT / "index"

LAWS = {  # BOE id -> short name used as the citation source
    "BOE-A-2022-24430": "Ley 39/2022 del Deporte",
    "BOE-A-2021-21650": "LO 11/2021 de lucha contra el dopaje en el deporte",
    "BOE-A-2007-13408": "Ley 19/2007 contra la violencia en el deporte",
}
BOE_API = "https://www.boe.es/datosabiertos/api/legislacion-consolidada/id/{id}/texto"

EMBED_MODEL = "gemini-embedding-2"
DIMENSIONS = 768
BATCH = 20

# Two chunking designs, compared in evaluate.py
DESIGNS = ["article", "fixed"]
ARTICLE_MAX_WORDS = 350        # "article": one chunk per article, long ones split at paragraph ends
FIXED_WORDS, FIXED_OVERLAP = 300, 50  # "fixed": 300-word windows over the whole law, 50 words overlap


def log(*args):
    print(*args, file=sys.stderr, flush=True)  # stdout belongs to the MCP protocol in server.py


# ---------------------------------------------------------------------------
# Extract and clean
# ---------------------------------------------------------------------------
def clean(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)  # "Artículo\xa01" -> "Artículo 1"
    return re.sub(r"\s+", " ", text).strip()


def location_of(title: str) -> str:
    """'Artículo 23' / 'Disposición adicional primera' / 'Anexo' from a BOE block title."""
    title = clean(title or "")
    m = re.match(r"(Artículo \d+(?: (?:bis|ter|quater))?)", title, re.I)
    return m.group(1) if m else title


def parse_boe(path: Path) -> list[dict]:
    """Articles of one consolidated BOE law: [{source, location, heading, paragraphs}].

    Keeps only the current version of each block. Drops the preamble, the
    signatures, the initial note and the BOE's editorial notes about amendments,
    which are comments on the law, not the law itself.
    """
    source = LAWS.get(path.stem, path.stem)
    root = ET.parse(path).getroot()
    articles, titulo, capitulo = [], "", ""
    for block in root.iter("bloque"):
        kind, version = block.get("tipo"), block.findall("version")[-1]
        texts = [(el.tag, el.get("class"), clean("".join(el.itertext()))) for el in version]
        if kind == "encabezado":
            name = " ".join(t for tag, cls, t in texts if tag == "p")
            if "TÍTULO" in name.upper() and "CAPÍTULO" not in name.upper():
                titulo, capitulo = name, ""
            elif "CAPÍTULO" in name.upper():
                capitulo = name
            continue
        if kind != "precepto":
            continue  # preamble, signature, initial note
        paragraphs = []
        for tag, cls, t in texts:
            if not t or cls == "articulo":
                continue  # the article title is kept in `heading`
            if tag == "blockquote" and cls is None:
                continue  # BOE editorial note ("Se añade una letra f) por ...")
            paragraphs.append(t)
        title = next((t for tag, cls, t in texts if cls == "articulo"), clean(block.get("titulo") or ""))
        if paragraphs:
            articles.append({"source": source, "location": location_of(block.get("titulo") or title),
                             "heading": " > ".join(x for x in (titulo, capitulo, title) if x),
                             "paragraphs": paragraphs})
    return articles


def parse_other(path: Path) -> list[dict]:
    """Any other file added through add_document: PDF (one unit per page), HTML or text."""
    source = path.stem
    if path.suffix.lower() == ".xml":
        return parse_boe(path)
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        pages = PdfReader(str(path)).pages
        return [{"source": source, "location": f"página {i}", "heading": f"{source}, página {i}",
                 "paragraphs": [clean(p) for p in (page.extract_text() or "").split("\n\n") if clean(p)]}
                for i, page in enumerate(pages, 1)]
    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() in (".html", ".htm"):
        from bs4 import BeautifulSoup
        raw = BeautifulSoup(raw, "html.parser").get_text("\n\n")
    paragraphs = [clean(p) for p in re.split(r"\n\s*\n", raw) if clean(p)]
    return [{"source": source, "location": "texto", "heading": source, "paragraphs": paragraphs}]


# ---------------------------------------------------------------------------
# Chunk
# ---------------------------------------------------------------------------
def chunk_id(design: str, c: dict) -> str:
    return hashlib.sha1(f"{design}|{c['source']}|{c['location']}|{c['text']}".encode()).hexdigest()[:20]


def article_chunks(articles: list[dict]) -> list[dict]:
    """One chunk per article; articles longer than ARTICLE_MAX_WORDS are split at paragraph ends."""
    chunks = []
    for a in articles:
        parts, current = [], []
        for p in a["paragraphs"]:
            if current and len(" ".join(current + [p]).split()) > ARTICLE_MAX_WORDS:
                parts.append(current)
                current = []
            current.append(p)
        parts.append(current)
        for i, part in enumerate(parts, 1):
            loc = a["location"] + (f" (parte {i}/{len(parts)})" if len(parts) > 1 else "")
            chunks.append({"source": a["source"], "location": loc, "articles": a["location"],
                           "text": f"{a['source']} — {a['heading']}\n" + "\n".join(part)})
    return chunks


def fixed_chunks(articles: list[dict]) -> list[dict]:
    """300-word windows over the whole law in order, ignoring article boundaries."""
    words, owner = [], []  # every word remembers which article it came from
    for a in articles:
        for w in (a["location"] + ". " + " ".join(a["paragraphs"])).split():
            words.append(w)
            owner.append(a["location"])
    chunks, step = [], FIXED_WORDS - FIXED_OVERLAP
    for start in range(0, max(len(words) - FIXED_OVERLAP, 1), step):
        span = owner[start:start + FIXED_WORDS]
        locs = list(dict.fromkeys(span))
        chunks.append({"source": articles[0]["source"], "location": "; ".join(locs), "articles": "; ".join(locs),
                       "text": f"{articles[0]['source']}\n" + " ".join(words[start:start + FIXED_WORDS])})
    return chunks


def chunk_file(path, design: str = "article") -> list[dict]:
    """Extract, clean and chunk one file. Each chunk: source, location, articles, text, id."""
    path = Path(path)
    articles = parse_boe(path) if path.suffix.lower() == ".xml" else parse_other(path)
    articles = [a for a in articles if a["paragraphs"]]
    if not articles:
        return []
    chunks = article_chunks(articles) if design == "article" else fixed_chunks(articles)
    for c in chunks:
        c["id"] = chunk_id(design, c)
        c["words"] = len(c["text"].split())
    return chunks


# ---------------------------------------------------------------------------
# Embed and store
# ---------------------------------------------------------------------------
_client = None


def client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=load_api_key())
    return _client


def embed(texts: list[str], task: str) -> list[list[float]]:
    """Embed with retries: the free tier answers 429 when a per-minute limit is hit."""
    for attempt in range(6):
        try:
            r = client().models.embed_content(
                # One Content per text: a plain list of strings is embedded as ONE combined input
                model=EMBED_MODEL, contents=[types.Content(parts=[types.Part(text=t)]) for t in texts],
                config=types.EmbedContentConfig(task_type=task, output_dimensionality=DIMENSIONS))
            if len(r.embeddings) != len(texts):
                raise RuntimeError(f"Asked for {len(texts)} embeddings, got {len(r.embeddings)}")
            return [e.values for e in r.embeddings]
        except Exception as error:  # noqa: BLE001
            if "429" in str(error) or "RESOURCE_EXHAUSTED" in str(error):
                if "PerDay" in str(error) or "per day" in str(error).lower():
                    raise RuntimeError("Daily embedding quota used up. Run again after 09:00 (Spain).") from error
                wait = 20 * (attempt + 1)
                log(f"  rate limited, waiting {wait}s ...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Embedding kept failing after retries.")


def embed_query(text: str) -> list[float]:
    return embed([text], "RETRIEVAL_QUERY")[0]


def collection(design: str = "article"):
    db = chromadb.PersistentClient(path=str(INDEX))
    return db.get_or_create_collection(f"sports_law_{design}", metadata={"hnsw:space": "cosine"})


def embed_and_store(chunks: list[dict], design: str = "article") -> int:
    """Embed only the chunks whose id isn't stored yet; save every batch as soon as it arrives."""
    col = collection(design)
    have = set(col.get(ids=[c["id"] for c in chunks], include=[])["ids"]) if chunks else set()
    todo = [c for c in chunks if c["id"] not in have]
    for i in range(0, len(todo), BATCH):
        batch = todo[i:i + BATCH]
        vectors = embed([c["text"] for c in batch], "RETRIEVAL_DOCUMENT")
        col.add(ids=[c["id"] for c in batch], embeddings=vectors, documents=[c["text"] for c in batch],
                metadatas=[{k: c[k] for k in ("source", "location", "articles", "words")} for c in batch])
        log(f"  [{design}] stored {min(i + BATCH, len(todo))}/{len(todo)} new chunks")
    return len(todo)


def download() -> list[Path]:
    CORPUS.mkdir(exist_ok=True)
    paths = []
    for boe_id in LAWS:
        path = CORPUS / f"{boe_id}.xml"
        if not path.exists():
            r = httpx.get(BOE_API.format(id=boe_id), headers={"Accept": "application/xml"}, timeout=60)
            r.raise_for_status()
            path.write_bytes(r.content)
            log(f"downloaded {boe_id}")
        paths.append(path)
    return paths


if __name__ == "__main__":
    paths = download()
    for design in DESIGNS:
        chunks = [c for p in paths for c in chunk_file(p, design)]
        words = sum(c["words"] for c in chunks)
        log(f"[{design}] {len(chunks)} chunks, {words:,} words, {len(set(c['source'] for c in chunks))} documents")
        new = embed_and_store(chunks, design)
        log(f"[{design}] embedded {new} new chunks; collection now holds {collection(design).count()}")
