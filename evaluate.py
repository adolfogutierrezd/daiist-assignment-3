"""
Assignment 3: evaluation (`main.py evaluate`).

1. Retrieval: hit rate at k = 1, 3, 5 for each design, on the answerable questions.
(End-to-end evaluation of the agent is added below in the next step.)

Question vectors are cached in eval/query_vectors.json, so every design and
every rerun reuses them instead of spending embedding quota.
"""

import csv
import json
import sys
from pathlib import Path

import pandas as pd

from index import embed_query, search

ROOT = Path(__file__).resolve().parent
EVAL = ROOT / "eval"
QUESTIONS = EVAL / "questions.csv"
VECTOR_CACHE = EVAL / "query_vectors.json"

DESIGNS = {  # name -> (chunking design, hybrid search?)
    "fixed 300 words, vector": ("fixed", False),
    "one chunk per article, vector": ("article", False),
    "one chunk per article, hybrid": ("article", True),
}
KS = [1, 3, 5]


def load_questions() -> list[dict]:
    with QUESTIONS.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def query_vectors(questions: list[dict]) -> dict:
    cache = json.loads(VECTOR_CACHE.read_text()) if VECTOR_CACHE.exists() else {}
    for q in questions:
        if q["question"] not in cache:
            cache[q["question"]] = embed_query(q["question"])
            VECTOR_CACHE.write_text(json.dumps(cache))  # save each one as it arrives
    return cache


def expected(q: dict) -> list[tuple[str, str]]:
    return list(zip([s.strip() for s in q["expected_source"].split(";")],
                    [l.strip() for l in q["expected_location"].split(";")]))


def is_hit(chunk: dict, source: str, location: str) -> bool:
    """The chunk comes from the expected law and contains the expected article."""
    return chunk["source"] == source and location in [a.strip() for a in chunk["articles"].split(";")]


def retrieval_eval(questions: list[dict], vectors: dict) -> pd.DataFrame:
    answerable = [q for q in questions if q["kind"] != "unanswerable"]
    rows, per_question = [], []
    for name, (design, hybrid) in DESIGNS.items():
        results = {q["id"]: search(q["question"], design, k=max(KS), hybrid=hybrid,
                                   query_vector=vectors[q["question"]]) for q in answerable}
        row = {"design": name}
        for k in KS:
            any_hit, all_hit, words = [], [], []
            for q in answerable:
                top, exp = results[q["id"]][:k], expected(q)
                found = [any(is_hit(c, s, l) for c in top) for s, l in exp]
                any_hit.append(any(found))
                if q["kind"] == "multi":
                    all_hit.append(all(found))
                words.append(sum(len(c["text"].split()) for c in top))
            row[f"hit@{k}"] = round(sum(any_hit) / len(any_hit), 3)
            row[f"multi_both@{k}"] = round(sum(all_hit) / len(all_hit), 3)
            row[f"words@{k}"] = round(sum(words) / len(words))
        rows.append(row)
        for q in answerable:
            per_question.append({"design": name, "id": q["id"], "kind": q["kind"],
                                 "top5": " | ".join(f"{c['source'].split()[0]} {c['source'].split()[1]} {c['location']}"
                                                    for c in results[q["id"]]),
                                 "rank_of_first_hit": next((c["rank"] for c in results[q["id"]]
                                                            if any(is_hit(c, s, l) for s, l in expected(q))), None)})
    pd.DataFrame(per_question).to_csv(EVAL / "retrieval_per_question.csv", index=False)
    table = pd.DataFrame(rows)
    table.to_csv(EVAL / "retrieval_results.csv", index=False)
    return table


if __name__ == "__main__":
    questions = load_questions()
    vectors = query_vectors(questions)
    table = retrieval_eval(questions, vectors)
    print("\nRetrieval (answerable questions, n =", sum(q["kind"] != "unanswerable" for q in questions), ")")
    print(table.to_string(index=False))
    if "--retrieval-only" in sys.argv:
        raise SystemExit(0)
