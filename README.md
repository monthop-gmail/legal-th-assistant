# Legal-TH Assistant

ผู้ช่วยด้านกฎหมายไทย (Thai Legal Assistant) ใช้ RAG Pipeline ค้นหามาตรากฎหมายด้วย semantic search แล้วตอบผ่าน Claude Code

## สถาปัตยกรรม

```
ผู้ใช้ถาม
    ↓
Claude Code → เรียก MCP tool: search_law("คำถาม")
    ↓
MCP Server (Streamable HTTP) → ค้น ChromaDB
    ↓
ได้มาตราที่เกี่ยวข้อง → Claude ตอบพร้อมอ้างอิง
```

## Docker Compose — 3 Services

| Service | Port | หน้าที่ |
|---|---|---|
| `chromadb` | 8100 | Vector DB เก็บ embedding |
| `app` | - | Ingest กฎหมาย (แยกทีละมาตรา → embedding) |
| `mcp-server` | 8200 | MCP Streamable HTTP server |

## เริ่มต้นใช้งาน

### 1. Clone และตั้งค่า

```bash
git clone https://github.com/monthop-gmail/legal-th-assistant.git
cd legal-th-assistant

# สร้างไฟล์ .env สำหรับ Hugging Face token (ไม่บังคับ แต่แนะนำ)
echo "HF_TOKEN=hf_your_token_here" > .env
```

### 2. รัน Docker Compose

```bash
# เริ่มทุก service + ingest กฎหมาย
docker compose up --build -d

# รอ ingest เสร็จ (ครั้งแรกต้องดาวน์โหลด model ~1.1GB)
docker logs -f legal-th-app

# เช็คว่า MCP server พร้อม
docker logs legal-th-mcp
```

### 3. เชื่อมกับ Claude Code

ไฟล์ `.mcp.json` มีมาให้แล้ว เปิด Claude Code ในโฟลเดอร์นี้จะเชื่อมอัตโนมัติ:

```json
{
  "mcpServers": {
    "legal-th": {
      "type": "http",
      "url": "http://localhost:8200/mcp"
    }
  }
}
```

### 4. ใช้งาน

เปิด Claude Code แล้วถามคำถามกฎหมายได้เลย เช่น:

- "ถูกเลิกจ้างไม่เป็นธรรม ทำอย่างไรได้บ้าง?"
- "PDPA มีโทษอะไรบ้าง?"
- "ทำร้ายร่างกายมีโทษอะไร?"

Claude จะเรียก `search_law` อัตโนมัติเพื่อค้นหามาตราที่เกี่ยวข้อง

## MCP Tools

| Tool | คำอธิบาย |
|---|---|
| `search_law(query, n_results)` | ค้นมาตรากฎหมายด้วย semantic search |
| `list_laws()` | แสดงรายชื่อกฎหมายทั้งหมดในระบบ |

## ค้นหาผ่าน CLI

```bash
# ค้นหามาตราที่เกี่ยวข้อง
docker compose run --rm app python scripts/search_law.py "เลิกจ้างไม่เป็นธรรม"

# ค้นหาแบบระบุจำนวนผลลัพธ์
docker compose run --rm app python scripts/search_law.py "ข้อมูลส่วนบุคคลรั่วไหล" 3
```

## กฎหมายในระบบ

| กฎหมาย | จำนวนมาตรา |
|---|---|
| พ.ร.บ.คุ้มครองแรงงาน พ.ศ. 2541 | 17 |
| พ.ร.บ.คุ้มครองข้อมูลส่วนบุคคล พ.ศ. 2562 (PDPA) | 14 |
| ประมวลกฎหมายอาญา | 26 |
| **รวม** | **57** |

## เพิ่มกฎหมายใหม่

1. เพิ่มไฟล์ `.txt` ในโฟลเดอร์ `laws/` (ใช้รูปแบบ `มาตรา XX:` ขึ้นต้น)
2. เพิ่ม mapping ใน `scripts/ingest_laws.py` → `LAW_NAMES`
3. รัน ingest ใหม่:

```bash
docker compose run --rm app python scripts/ingest_laws.py
```

## เทคโนโลยี

- **Embedding:** [intfloat/multilingual-e5-base](https://huggingface.co/intfloat/multilingual-e5-base) (รองรับภาษาไทย)
- **Vector DB:** [ChromaDB](https://www.trychroma.com/)
- **MCP Server:** [FastMCP](https://github.com/modelcontextprotocol/python-sdk) (Streamable HTTP)
- **AI:** [Claude Code](https://claude.ai/claude-code)

## โครงสร้างไฟล์

```
legal-th-assistant/
├── .mcp.json              ← MCP config สำหรับ Claude Code
├── .env                   ← HF_TOKEN (ไม่ push ขึ้น git)
├── CLAUDE.md              ← System prompt
├── docker-compose.yml     ← 3 services
├── Dockerfile             ← app (ingest)
├── Dockerfile.mcp         ← MCP server
├── requirements.txt
├── requirements.mcp.txt
├── laws/
│   ├── labor_protection_2541.txt
│   ├── pdpa_2562.txt
│   └── criminal_code_common.txt
├── scripts/
│   ├── ingest_laws.py     ← แยกมาตรา → embedding → ChromaDB
│   ├── search_law.py      ← CLI search
│   └── mcp_server.py      ← MCP server (Streamable HTTP)
└── docs/
    ├── how-mcp-server-works.md      ← อธิบายการทำงานของ MCP server
    └── legal-th-knowledge-base.md   ← สถาปัตยกรรม, มาตราสำคัญ, TODO
```

## เอกสารเพิ่มเติม

- [MCP Server ทำงานอย่างไร](docs/how-mcp-server-works.md) — Flow การทำงาน, MCP Protocol, Semantic Search
- [Knowledge Base & Architecture](docs/legal-th-knowledge-base.md) — สถาปัตยกรรม, มาตราสำคัญ, TODO

## License

MIT
