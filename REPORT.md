# Assignment 3 Report

- **Name**: Adolfo Gutierrez de Gandarilla Domínguez
- **Student ID**: 19003
- **Group**: BBADBA 5B

## Use case

**Who asks.** Staff of Spanish sports clubs, federations and event
organisers who are not lawyers: club managers, team delegates, federation
administrators, organisers of a race or a match. They ask practical questions
about their legal obligations, for example *"¿Qué sanción tiene un club si sus
aficionados lanzan objetos al campo?"*, *"¿Puede un deportista negarse a un
control de dopaje fuera de competición?"* or *"¿Qué requisitos tiene una
competición para ser oficial?"*. Questions and answers are in Spanish, like
the laws.

**What they do with the answer.** They decide what to do next: prepare a
document, accept or refuse a request, warn an athlete, or call the
federation's lawyer.

**What a wrong answer costs compared with "I don't know".**

| Answer | What happens | Rough cost |
|---|---|---|
| Correct, with citation | They act correctly and can check the article cited | Saves a lawyer's consultation (~€150) |
| **"The laws I have don't answer this, ask a lawyer / the federation"** | One consultation with a lawyer or the federation | **~€150 and a few days** |
| **Wrong but confident** | They act on it: an event without the required measures, a missed deadline, an athlete told something false about doping controls | **Fines from a few thousand to hundreds of thousands of euros, a club sanctioned, an athlete banned for years** |

A confident wrong answer is **far worse** than a refusal, so the assistant
must **only answer from the text of the laws, cite the article for every
claim, and say "I don't know" whenever the laws it has don't cover the
question**. A useful refusal is a success, not a failure. This is why the
evaluation counts wrong answers and unsupported claims separately from
refusals, and why the ship decision looks first at how often it makes things
up.

**What it is not.** It is not legal advice and it doesn't know case law,
regional laws or federation rules, only the three national laws below.

## Corpus

Three Spanish national laws on sport, downloaded as **consolidated
text** (the current version, with all amendments applied) from the open-data
API of the *Boletín Oficial del Estado* (BOE). The API returns the law already
divided into blocks (preamble, headings, articles), each with its title.

| Document | BOE identifier and URL | Published | Consolidated text updated | Licence | Words (current text, without preamble) |
|---|---|---|---|---|---|
| Ley 39/2022, de 30 de diciembre, del Deporte | [BOE-A-2022-24430](https://www.boe.es/buscar/act.php?id=BOE-A-2022-24430) | 31/12/2022 | 19/11/2026 | Not subject to copyright; BOE reuse conditions | ~40,700 |
| Ley Orgánica 11/2021, de 28 de diciembre, de lucha contra el dopaje en el deporte | [BOE-A-2021-21650](https://www.boe.es/buscar/act.php?id=BOE-A-2021-21650) | 29/12/2021 | 20/12/2025 | Not subject to copyright; BOE reuse conditions | ~28,700 |
| Ley 19/2007, de 11 de julio, contra la violencia, el racismo, la xenofobia y la intolerancia en el deporte | [BOE-A-2007-13408](https://www.boe.es/buscar/act.php?id=BOE-A-2007-13408) | 12/07/2007 | 19/12/2025 | Not subject to copyright; BOE reuse conditions | ~14,400 |
| **Total** | | | | | **~83,800** |

**Licence.** Laws and regulations are **excluded from copyright** in Spain
(article 13 of the *Ley de Propiedad Intelectual*: *"No son objeto de
propiedad intelectual las disposiciones legales o reglamentarias…"*), and
the BOE allows its content to be reused provided the source and the date of
the version are cited. The texts contain **no personal data** (only the
names of the King and the ministers who signed them, in the signature block,
which I drop).

**Why these three.** Together they cover the main legal obligations of a
club or federation: how sport is organised (licences, competitions,
federations, sports justice), anti-doping (controls, sanctions, health of
athletes), and violence and racism at events (security measures, sanctions
for clubs and spectators).

**Why I leave out the preambles.** The preamble explains *why* the law was
made but contains no binding rule. It mentions many of the topics without
stating the rule, so it would compete with the actual articles in the search
and could lead to unsupported answers. It also saves embedding quota.
Including the preambles, the three texts have ~100,700 words.

## Ingestion

**Extract.** `index.py` downloads each law from the BOE open-data API
(`/datosabiertos/api/legislacion-consolidada/id/{BOE id}/texto`) as XML. The
XML is already split into blocks (*preámbulo*, *encabezado* for Título and
Capítulo headings, *precepto* for articles and *disposiciones*), and each block
keeps every historical version. I keep **only the latest version** of each
block, and **only the articles and disposiciones**: the preamble, signatures
and initial note are dropped.

**Clean.**
- **BOE editorial notes removed.** The consolidated text contains 13 notes
  written by the BOE about amendments (e.g. *"Se añade una letra f) al
  apartado 1 por la disposición final 8.1 de la Ley 4/2023…"*). They are not
  law and would add dates and article numbers that don't apply, so I drop
  `<blockquote>` notes without a class. I keep the one marked "always show",
  which says that the *Comité Español de Disciplina Deportiva* was abolished.
- **Unicode normalisation.** Article titles contain a non-breaking space
  ("Artículo\xa01"), so "Artículo 1" in a question or in my test set did not
  match the metadata. NFKC normalisation and whitespace collapsing fix it.
- **One extraction problem I fixed: article 33 of Ley 19/2007** is titled
  *"Articulo 33"* (without the accent) in the BOE, so my first version stored
  its location as the whole title. The parser now accepts both spellings, and
  `main.py index` deletes the outdated chunk and embeds the corrected one.

**Chunk metadata.** Every chunk stores `source` (short name of the law, e.g.
*LO 11/2021 de lucha contra el dopaje en el deporte*), `location` (e.g.
*Artículo 15 (parte 2/2)*), `articles` (the articles it contains, used to
score retrieval) and `words`. The text of each chunk starts with the law's
name and, in the article design, the Título > Capítulo > article title, so the
embedding knows the context of the paragraph.

**Two chunkings** (compared in *Retrieval*):

| Design | How | Chunks | Median words |
|---|---|---|---|
| **article** | One chunk per article; articles longer than 350 words are split at paragraph ends into "parte 1/n, 2/n…" | **384** | 227 |
| **fixed** | 300-word windows over each law in order, 50 words overlap, ignoring article boundaries | **308** | 304 |

**Embedding and storage.** `gemini-embedding-2`, 768 dimensions, task type
`RETRIEVAL_DOCUMENT` for chunks and `RETRIEVAL_QUERY` for questions, stored
in ChromaDB in `index/` (one collection per design, cosine distance, 15 MB).
Each batch of 20 is stored as soon as it arrives; a chunk's id is a hash of
its design, source, location and text, so `main.py index` only embeds chunks
that don't have a saved vector yet. Rebuilding everything costs ~692
embeddings; a rerun costs 0. **A problem I hit:** passing a plain list of
strings to `gemini-embedding-2` returned **one** vector for 20 texts (it
treats the list as one multimodal input). I now send one `Content` per text
and check that the number of vectors equals the number of texts.

## Test set

I wrote the questions from the text of the laws, **before** running any
retrieval, imagining what a club manager, team delegate or federation
administrator would actually ask. For every answerable question I looked up
the article and wrote the reference answer from its text. For the
unanswerable ones I searched the three laws for the key words first, to make
sure they really are not covered, and kept them **close to the topic**.

| Kind | Count |
|---|---|
| single (one article) | 22 |
| multi (two articles, sometimes from two different laws) | 6 |
| unanswerable | 7 |
| **Total** | **35** |

By law: 11 questions on the Ley del Deporte, 11 on the anti-doping law and
8 on the violence law (multi questions counted under each law they use).

**Two examples:**

- **multi, q24:** *"¿Cuánto tiempo hay para sancionar una infracción
  disciplinaria muy grave y una infracción de dopaje?"* → needs the Ley del
  Deporte, art. 112 (**3 years**) **and** the anti-doping law, art. 33
  (**10 years**). An answer from one passage only would be half right.
- **unanswerable, q35:** *"¿Qué indemnización mínima cubre el seguro
  obligatorio deportivo en caso de fallecimiento?"* → the Ley del Deporte
  (art. 23) **requires** the insurance but leaves the minimum amounts to a
  future regulation, which is not in the corpus. A good assistant should say
  that the insurance is mandatory but that the amount is not in these laws,
  not invent a figure.

## Retrieval

**Metric.** For each answerable question (28), a hit at k means that one of
the top-k chunks comes from the expected law **and** contains the expected
article. For the 6 multi questions I also report whether **both** expected
articles are in the top k. Question vectors are computed once and cached in
`eval/query_vectors.json`, so every design is compared on the same vectors.

| Design | Hit@1 | Hit@3 | Hit@5 | Multi, both passages @5 | Words added to the prompt @1 / @3 / @5 |
|---|---|---|---|---|---|
| Fixed 300-word windows, vector search | 82% | 96% | 100% | **83%** | 307 / 922 / 1,537 |
| **One chunk per article, vector search** | **93%** | **100%** | **100%** | 67% | **251 / 779 / 1,310** |
| One chunk per article, hybrid (vector + BM25 keywords, reciprocal rank fusion) | 64% | 79% | 82% | 67% | 253 / 801 / 1,334 |

**What the numbers say.**

- **Chunking by article wins.** It puts the right article first 93% of the
  time and always within the top 3, with 15% fewer words in the prompt. A
  legal question is almost always about one article, so a chunk that is
  exactly one article is the right unit. Fixed windows cut articles in two and
  mix neighbouring articles, so the right one is more often 2nd–5th.
- **Hybrid search made it worse**, which I didn't expect. Looking at the
  misses: (1) there is no stemming, so *"¿Cuándo **prescribe**…?"* doesn't
  match *"**prescribirán**"* / *"**prescripción**"* in art. 112, and the keyword
  ranking prefers arts. 104–108, which repeat *"infracción muy grave"* many
  times; (2) legal vocabulary (*sanción, infracción, deportista*) appears in
  dozens of articles, so the keyword ranking adds noise that outweighs the
  meaning-based ranking.
- **Where article chunking fails: two multi questions** (q23, q27). Both ask
  for a sanction *and* a fine; the sanction article (21 or 22) is found but
  the fines article (24) is not in the top 5. Fixed windows do better here
  (83%) because one window can span two neighbouring articles. The agent can
  compensate by searching once per part of the question.

**Chosen design: one chunk per article, vector search, k = 5.** Best hit@1
and hit@3, and fewest words per result. Hit@3 is already 100% on my test
set, but I keep k = 5 as a margin for differently phrased real questions; it
adds ~530 words (~700 tokens) per search.

## Tools and subagent

*Your tools' descriptions, one search result, the subagent's instructions, one transcript from your editor.*

## Adding a document

*What happens when a document is already indexed. The unanswerable question, the document you added, the answer before and after.*

## Harness and guardrails

*Your AGENTS.md rules, the approval step, and your extra guardrail with one case where it fired.*

## Evaluation

*Code checks, the judge's rubric, your agreement with the judge, and results: correct, unsupported, correct refusals, wrong refusals.*

## Failures

*Failed questions by cause, with counts, and what to fix first.*

## Decision

*Would you let users rely on it, for what, with which safeguard? Cost and latency per question.*

## AI use

*What you used and how, or "none".*
