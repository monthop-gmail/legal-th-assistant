"""
MCP Server (Streamable HTTP) — Thai Legal Search
เรียกค้นมาตรากฎหมายไทยจาก ChromaDB ผ่าน MCP Protocol
"""

import os
import chromadb
from sentence_transformers import SentenceTransformer
from mcp.server.fastmcp import FastMCP

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
COLLECTION_NAME = "thai_laws"

# Init MCP server (stateless for Docker/production)
mcp = FastMCP(
    "legal-th",
    stateless_http=True,
    json_response=True,
    host="0.0.0.0",
    port=8200,
)

# Load model once at startup
print("Loading embedding model...")
model = SentenceTransformer("intfloat/multilingual-e5-base")
print("Model loaded!")

client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)


@mcp.tool()
def search_law(query: str, n_results: int = 5) -> list[dict]:
    """ค้นหามาตรากฎหมายไทยที่เกี่ยวข้องกับคำถาม

    Args:
        query: คำค้นหา เช่น "เลิกจ้างไม่เป็นธรรม", "ข้อมูลส่วนบุคคลรั่วไหล"
        n_results: จำนวนผลลัพธ์ที่ต้องการ (ค่าเริ่มต้น 5)

    Returns:
        รายการมาตรากฎหมายที่เกี่ยวข้อง พร้อม score ความเกี่ยวข้อง
    """
    collection = client.get_collection(COLLECTION_NAME)
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


@mcp.tool()
def list_laws() -> list[dict]:
    """แสดงรายชื่อกฎหมายทั้งหมดที่มีในระบบ พร้อมจำนวนมาตรา

    Returns:
        รายชื่อกฎหมายและจำนวนมาตราในแต่ละฉบับ
    """
    collection = client.get_collection(COLLECTION_NAME)
    all_data = collection.get(include=["metadatas"])

    law_counts: dict[str, int] = {}
    for meta in all_data["metadatas"]:
        name = meta["law_name"]
        law_counts[name] = law_counts.get(name, 0) + 1

    return [
        {"law_name": name, "section_count": count}
        for name, count in law_counts.items()
    ]


if __name__ == "__main__":
    print("Starting MCP Server (Streamable HTTP) on port 8200...")
    mcp.run(transport="streamable-http")
