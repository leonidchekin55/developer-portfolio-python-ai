#!/usr/bin/env python3
"""Compare lexical, hash-vector and optional FastEmbed retrieval on the public synthetic set."""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

ROOT=Path(__file__).parents[1]
sys.path.insert(0,str(ROOT))
from shared.core import settings
from shared.embeddings import cosine_similarity, embed_texts

DATASET = ROOT / "apps" / "02_knowledge_base" / "eval_dataset.json"
STOP = {"как", "что", "где", "когда", "может", "ли", "мои", "мое", "мой", "для", "или", "это", "будет", "если", "после", "снова", "в", "на", "и", "а", "из", "по", "до", "не"}

def tokenize(text: str) -> list[str]:
    return [term for term in re.findall(r"[\w]+", text.casefold(), flags=re.UNICODE) if len(term) > 1 and term not in STOP]

def lexical_score(query: str, document: str, doc_freq: Counter[str], total: int) -> float:
    query_terms = set(tokenize(query))
    document_terms = Counter(tokenize(document))
    score = 0.0
    for term in query_terms & document_terms.keys():
        idf = math.log(1 + (total - doc_freq[term] + 0.5) / (doc_freq[term] + 0.5))
        tf = document_terms[term]
        score += idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * len(document_terms) / 80))
    return score

def metrics(ranked_ids: list[list[str]], relevant_ids: list[str]) -> dict[str, float]:
    reciprocal_ranks=[]; hits_at_1=0; hits_at_3=0
    for ranked, relevant in zip(ranked_ids, relevant_ids):
        rank=ranked.index(relevant)+1 if relevant in ranked else 0
        reciprocal_ranks.append(1/rank if rank else 0)
        hits_at_1 += rank == 1
        hits_at_3 += 0 < rank <= 3
    count=max(1,len(relevant_ids))
    return {"recall_at_1":round(hits_at_1/count,4),"recall_at_3":round(hits_at_3/count,4),"mrr":round(sum(reciprocal_ranks)/count,4)}

def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode",choices=["hash","fastembed"],default="fastembed",help="semantic model is local and downloads once on first run")
    parser.add_argument("--output",type=Path,help="optional path for the JSON report")
    args=parser.parse_args()
    data=json.loads(DATASET.read_text(encoding="utf-8")); docs=data["documents"]; queries=data["queries"]
    doc_freq=Counter(term for doc in docs for term in set(tokenize(doc["text"])))
    lexical_rankings=[]
    for query in queries:
        ranked=sorted(docs,key=lambda doc:(-lexical_score(query["text"],doc["text"],doc_freq,len(docs)),doc["id"]))
        lexical_rankings.append([doc["id"] for doc in ranked])
    previous_mode=settings.embedding_mode; settings.embedding_mode=args.mode
    try:
        passage_vectors=embed_texts([doc["text"] for doc in docs],input_type="passage")
        query_vectors=embed_texts([query["text"] for query in queries],input_type="query")
    finally:
        settings.embedding_mode=previous_mode
    semantic_rankings=[]
    for query_vector in query_vectors:
        indices=sorted(range(len(docs)),key=lambda index:(-cosine_similarity(query_vector,passage_vectors[index]),docs[index]["id"]))
        semantic_rankings.append([docs[index]["id"] for index in indices])
    relevant=[query["relevant_document_id"] for query in queries]
    try: fastembed_version=version("fastembed")
    except PackageNotFoundError: fastembed_version=None
    report={"dataset_version":data["version"],"queries":len(queries),"documents":len(docs),"embedding_mode":args.mode,"model":settings.fastembed_model if args.mode=="fastembed" else "feature-hash baseline","fastembed_version":fastembed_version if args.mode=="fastembed" else None,"metrics":{"lexical_bm25_like":metrics(lexical_rankings,relevant),"dense_retrieval":metrics(semantic_rankings,relevant)},"cases":[{"query":q["text"],"relevant":q["relevant_document_id"],"lexical_top3":lexical_rankings[i][:3],"dense_top3":semantic_rankings[i][:3]} for i,q in enumerate(queries)],"note":"Small synthetic diagnostic set; results are not a general quality guarantee."}
    rendered=json.dumps(report,ensure_ascii=False,indent=2)
    if args.output: args.output.write_text(rendered+"\n",encoding="utf-8")
    print(rendered)

if __name__ == "__main__":
    main()
