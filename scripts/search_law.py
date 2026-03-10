"""
Search Thai law sections from ChromaDB
Usage: python scripts/search_law.py "คำค้นหา" [จำนวนผลลัพธ์]
"""

import os
import sys
import json
import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
COLLECTION_NAME = "thai_laws"


def search(query: str, n_results: int = 5) -> list[dict]:
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    collection = client.get_collection(COLLECTION_NAME)

    # Load model
    model = SentenceTransformer("intfloat/multilingual-e5-base")

    # e5 model needs "query: " prefix for queries
    query_embedding = model.encode(f"query: {query}").tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    output = []
    for i in range(len(results["ids"][0])):
        output.append({
            "section": results["metadatas"][0][i]["section"],
            "law_name": results["metadatas"][0][i]["law_name"],
            "text": results["documents"][0][i],
            "score": round(1 - results["distances"][0][i], 4),
        })

    return output


def main():
    if len(sys.argv) < 2:
        print("Usage: python search_law.py <query> [n_results]")
        sys.exit(1)

    query = sys.argv[1]
    n_results = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    print(f"Searching: \"{query}\" (top {n_results})\n")

    results = search(query, n_results)

    for i, r in enumerate(results, 1):
        print(f"--- ผลลัพธ์ที่ {i} (score: {r['score']}) ---")
        print(f"กฎหมาย: {r['law_name']}")
        print(f"มาตรา: {r['section']}")
        print(f"เนื้อหา: {r['text'][:200]}...")
        print()

    # Also output JSON for programmatic use
    print("=== JSON ===")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
