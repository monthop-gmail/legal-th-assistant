"""
Ingest law files into ChromaDB — แยกทีละมาตรา แล้วสร้าง embedding
"""

import os
import re
import time
import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
LAWS_DIR = os.getenv("LAWS_DIR", "/app/laws")
COLLECTION_NAME = "thai_laws"

# Mapping filename -> law name
LAW_NAMES = {
    "labor_protection_2541.txt": "พ.ร.บ.คุ้มครองแรงงาน พ.ศ. 2541",
    "pdpa_2562.txt": "พ.ร.บ.คุ้มครองข้อมูลส่วนบุคคล พ.ศ. 2562 (PDPA)",
    "criminal_code_common.txt": "ประมวลกฎหมายอาญา",
}


def chunk_by_section(text: str, law_name: str) -> list[dict]:
    """แยกตัวบทกฎหมายทีละมาตรา"""
    # Pattern: "มาตรา XX" at start of line
    pattern = r"(มาตรา\s+\d+[/\d]*\s*:?)"
    parts = re.split(pattern, text)

    chunks = []
    current_section = None
    current_text = ""

    for part in parts:
        if re.match(pattern, part):
            # Save previous chunk
            if current_section and current_text.strip():
                chunks.append({
                    "section": current_section.strip(),
                    "text": f"{current_section.strip()} {current_text.strip()}",
                    "law_name": law_name,
                })
            current_section = part
            current_text = ""
        else:
            current_text += part

    # Last chunk
    if current_section and current_text.strip():
        chunks.append({
            "section": current_section.strip(),
            "text": f"{current_section.strip()} {current_text.strip()}",
            "law_name": law_name,
        })

    return chunks


def wait_for_chroma(client, max_retries=30, delay=2):
    """Wait for ChromaDB to be ready"""
    for i in range(max_retries):
        try:
            client.heartbeat()
            print("ChromaDB is ready!")
            return True
        except Exception:
            print(f"Waiting for ChromaDB... ({i+1}/{max_retries})")
            time.sleep(delay)
    raise ConnectionError("ChromaDB is not available")


def main():
    print(f"Connecting to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}")
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    wait_for_chroma(client)

    # Load embedding model
    print("Loading embedding model: intfloat/multilingual-e5-base ...")
    model = SentenceTransformer("intfloat/multilingual-e5-base")

    # Delete existing collection if exists
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"Deleted existing collection: {COLLECTION_NAME}")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    print(f"Created collection: {COLLECTION_NAME}")

    # Process each law file
    all_chunks = []
    for filename, law_name in LAW_NAMES.items():
        filepath = os.path.join(LAWS_DIR, filename)
        if not os.path.exists(filepath):
            print(f"  SKIP: {filepath} not found")
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        chunks = chunk_by_section(text, law_name)
        all_chunks.extend(chunks)
        print(f"  {law_name}: {len(chunks)} มาตรา")

    if not all_chunks:
        print("No chunks found!")
        return

    # Create embeddings and add to ChromaDB
    print(f"\nTotal chunks: {len(all_chunks)}")
    print("Creating embeddings...")

    # e5 model needs "passage: " prefix for documents
    texts = [f"passage: {c['text']}" for c in all_chunks]
    embeddings = model.encode(texts, show_progress_bar=True).tolist()

    ids = [f"law_{i}" for i in range(len(all_chunks))]
    documents = [c["text"] for c in all_chunks]
    metadatas = [{"law_name": c["law_name"], "section": c["section"]} for c in all_chunks]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    print(f"\nIngested {len(all_chunks)} sections into ChromaDB!")
    print("Done.")


if __name__ == "__main__":
    main()
