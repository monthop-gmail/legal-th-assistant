# MCP Server ทำงานอย่างไร

## ภาพรวม

`mcp_server.py` เป็นตัวกลางระหว่าง **Claude Code** กับ **ChromaDB**
ทำหน้าที่รับคำถาม → ค้นหามาตรากฎหมาย → ส่งผลลัพธ์กลับให้ Claude

---

## Flow การทำงาน

### 1. ตอน Docker เริ่มต้น (`docker compose up`)

```
mcp-server container เริ่มทำงาน
    │
    ├── 1. โหลด embedding model (intfloat/multilingual-e5-base ~1.1GB)
    ├── 2. เชื่อมต่อ ChromaDB
    ├── 3. เปิด HTTP server ที่ port 8200
    └── 4. รอรับ request (ทำงานตลอด 24 ชม.)
```

### 2. ตอนผู้ใช้ถามคำถามกฎหมาย

```
ผู้ใช้: "ถูกเลิกจ้างไม่เป็นธรรม ทำยังไงดี?"
    │
    ▼
Claude Code
    │  อ่าน CLAUDE.md → เห็นว่าต้องเรียก search_law ก่อนตอบ
    │
    ▼
HTTP POST → http://localhost:8200/mcp
    │  method: search_law
    │  params: { query: "ถูกเลิกจ้างไม่เป็นธรรม", n_results: 5 }
    │
    ▼
┌─── mcp_server.py ───────────────────────────────┐
│                                                   │
│  1. รับคำถาม "ถูกเลิกจ้างไม่เป็นธรรม"             │
│          ↓                                        │
│  2. แปลงเป็น embedding vector (768 มิติ)           │
│     ด้วย multilingual-e5-base                      │
│          ↓                                        │
│  3. ค้น ChromaDB ด้วย cosine similarity            │
│     หา 5 มาตราที่ความหมายใกล้เคียงที่สุด             │
│          ↓                                        │
│  4. ส่งผลลัพธ์กลับ:                                 │
│     - ม.17/1 (score: 0.83)                        │
│     - ม.17  (score: 0.82)                         │
│     - ม.120 (score: 0.82)                         │
│     - ม.119 (score: 0.81)                         │
│     - ม.118 (score: 0.81)                         │
└───────────────────────────────────────────────────┘
    │
    ▼
Claude Code
    │  ได้มาตราที่เกี่ยวข้อง
    │  เรียบเรียงคำตอบ + อ้างอิงมาตรา
    │
    ▼
ผู้ใช้ได้คำตอบพร้อมอ้างอิงกฎหมาย
```

### 3. ตอนไม่มีคนถาม

```
mcp-server รอเฉย ๆ (idle)
ไม่ใช้ CPU/RAM เพิ่ม — แค่เปิด port ฟังอยู่
```

---

## MCP Protocol คืออะไร

**MCP (Model Context Protocol)** เป็นมาตรฐานที่ให้ AI เรียกใช้ tools ภายนอกได้

### เปรียบเทียบ: ไม่มี MCP vs มี MCP

| | ไม่มี MCP | มี MCP |
|---|---|---|
| Claude ค้นกฎหมาย | ต้องรัน bash script เอง | เรียก tool โดยตรง |
| Claude รู้จัก tool | ไม่รู้ ต้องบอกใน prompt | รู้จักอัตโนมัติ (tool discovery) |
| Parameter | ต้องประกอบ command เอง | มี schema ชัดเจน |
| Error handling | parse stdout เอง | มาตรฐาน JSON-RPC |

### Streamable HTTP Transport

```
Claude Code                          MCP Server
    │                                    │
    ├── POST /mcp ──────────────────────►│  initialize
    │◄──────────────────────── JSON ──── │
    │                                    │
    ├── POST /mcp ──────────────────────►│  tools/list
    │◄──────────────────────── JSON ──── │  → search_law, list_laws
    │                                    │
    ├── POST /mcp ──────────────────────►│  tools/call (search_law)
    │◄──────────────────────── JSON ──── │  → มาตราที่เกี่ยวข้อง
    │                                    │
```

- ใช้ HTTP POST ธรรมดา (ไม่ต้อง WebSocket)
- Stateless — ไม่เก็บ session (scale ได้ง่าย)
- JSON response — อ่านง่าย debug ง่าย

---

## Semantic Search ทำงานอย่างไร

### ทำไมไม่ใช้ keyword search?

```
คำถาม: "โดนไล่ออกจากงาน"
    │
    ├── keyword search: ค้นคำว่า "ไล่ออก" → ไม่เจอ (กฎหมายใช้คำว่า "เลิกจ้าง")
    │
    └── semantic search: เข้าใจความหมาย → เจอ ม.118 "เลิกจ้าง" (score: 0.81)
```

### ขั้นตอน Semantic Search

```
1. INGEST (ตอน ingest_laws.py รัน)
   ┌────────────────────────────────────────────┐
   │ "มาตรา 118: เมื่อนายจ้างเลิกจ้างลูกจ้าง    │
   │  ให้จ่ายค่าชดเชยดังนี้..."                    │
   └────────────┬───────────────────────────────┘
                │  embedding model
                ▼
   [0.023, -0.156, 0.089, ... 768 ตัวเลข]  ← vector
                │
                ▼
        บันทึกลง ChromaDB

2. SEARCH (ตอนผู้ใช้ถาม)
   ┌────────────────────────────────────────────┐
   │ "โดนไล่ออกจากงาน"                            │
   └────────────┬───────────────────────────────┘
                │  embedding model
                ▼
   [0.019, -0.148, 0.092, ... 768 ตัวเลข]  ← query vector
                │
                ▼
        เทียบกับทุก vector ใน ChromaDB (cosine similarity)
                │
                ▼
        ได้ 5 มาตราที่ใกล้เคียงที่สุด
```

---

## ไฟล์ที่เกี่ยวข้อง

| ไฟล์ | หน้าที่ | ถูกเรียกเมื่อ |
|---|---|---|
| `scripts/mcp_server.py` | MCP server — รับคำถาม ค้น ChromaDB | Docker container ทำงานตลอด |
| `scripts/ingest_laws.py` | แยกมาตรา → embedding → เก็บ ChromaDB | รันครั้งเดียวตอน ingest |
| `scripts/search_law.py` | CLI search (ไม่ผ่าน MCP) | รันด้วยมือจาก terminal |
| `.mcp.json` | บอก Claude Code ว่า MCP server อยู่ที่ไหน | Claude Code อ่านตอนเริ่ม |
| `CLAUDE.md` | บอก Claude ว่าต้องเรียก search_law ก่อนตอบ | ทุกครั้งที่เริ่ม session |

---

## คำสั่งที่เกี่ยวข้อง

```bash
# ดู logs ของ MCP server
docker logs -f legal-th-mcp

# ทดสอบ MCP server ด้วย curl
curl -s http://localhost:8200/mcp \
  -X POST \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

# restart MCP server
docker compose restart mcp-server

# rebuild MCP server (หลังแก้โค้ด)
docker compose up --build mcp-server -d
```
