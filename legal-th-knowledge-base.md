# Legal-TH Bot — Knowledge Base & Architecture Notes

> บันทึกจากการออกแบบระบบ Legal-TH Assistant บน Claude Code
> อัปเดตล่าสุด: 2026-03-10

---

## 1. ภาพรวมโปรเจกต์

Bot ผู้ช่วยด้านกฎหมายไทย (Thai Legal Assistant) บน Claude Code
- `CLAUDE.md` เป็น System Prompt หลัก
- ใช้ RAG Pipeline ระดับ 2 (ChromaDB + MCP Server)

---

## 2. โครงสร้างไฟล์

```
legal-th/
├── .mcp.json                  ← MCP config (type: http, port 8200)
├── .env                       ← HF_TOKEN (gitignore แล้ว)
├── .gitignore
├── .claude/settings.local.json
├── CLAUDE.md                  ← System prompt หลัก
├── docker-compose.yml         ← 3 services: chromadb, app, mcp-server
├── Dockerfile                 ← app container (ingest script)
├── Dockerfile.mcp             ← MCP server container
├── requirements.txt           ← app dependencies
├── requirements.mcp.txt       ← MCP server dependencies
├── laws/                      ← ตัวบทกฎหมาย (mount เข้า container)
│   ├── labor_protection_2541.txt
│   ├── pdpa_2562.txt
│   └── criminal_code_common.txt
├── scripts/
│   ├── ingest_laws.py         ← แยกทีละมาตรา → embedding → ChromaDB
│   ├── search_law.py          ← CLI search
│   └── mcp_server.py          ← MCP Streamable HTTP server (FastMCP)
└── legal-th-knowledge-base.md ← ไฟล์นี้
```

---

## 3. Docker Compose — 3 Services

| Service | Container | Port | หน้าที่ |
|---|---|---|---|
| chromadb | legal-th-chromadb | 8100→8000 | Vector DB เก็บ embedding |
| app | legal-th-app | - | Ingest กฎหมาย (รันครั้งเดียว) |
| mcp-server | legal-th-mcp | 8200→8200 | MCP Streamable HTTP server |

### คำสั่งที่ใช้บ่อย:
```bash
docker compose up -d                    # เริ่มทุก service
docker compose up --build mcp-server -d # rebuild MCP server
docker compose run --rm app python scripts/ingest_laws.py  # ingest ใหม่
docker compose run --rm app python scripts/search_law.py "คำค้น"  # ค้นหา CLI
docker compose down                     # หยุดทุก service
```

---

## 4. MCP Server

- **Framework:** FastMCP (mcp>=1.26.0)
- **Transport:** Streamable HTTP (stateless, json_response)
- **Endpoint:** `http://localhost:8200/mcp`
- **Embedding model:** `intfloat/multilingual-e5-base` (รองรับภาษาไทย)
- **Config:** `.mcp.json` → `{ "type": "http", "url": "http://localhost:8200/mcp" }`

### MCP Tools:
| Tool | คำอธิบาย |
|---|---|
| `search_law(query, n_results=5)` | ค้นมาตรากฎหมายด้วย semantic search |
| `list_laws()` | แสดงรายชื่อกฎหมายทั้งหมดในระบบ |

---

## 5. กฎหมายในระบบ (57 มาตรา)

### พ.ร.บ.คุ้มครองแรงงาน พ.ศ. 2541 (17 มาตรา)
- ม.5 (นิยาม), ม.17 (บอกเลิกสัญญา), ม.17/1 (สินจ้างแทนการบอกกล่าว)
- ม.23 (วันหยุดประจำสัปดาห์), ม.24 (ชั่วโมงทำงาน), ม.27 (วันหยุดพักผ่อน)
- ม.29 (ลาป่วย), ม.30 (ลาคลอด), ม.34 (ลาทหาร)
- ม.56 (ห้ามหักค่าจ้าง), ม.61-63 (ค่าล่วงเวลา/OT)
- ม.118 (ค่าชดเชยตามอายุงาน), ม.119 (ไม่ต้องจ่ายค่าชดเชย), ม.120 (ย้ายสถานที่)

### พ.ร.บ.คุ้มครองข้อมูลส่วนบุคคล พ.ศ. 2562 — PDPA (14 มาตรา)
- ม.6 (ขอบเขตบังคับใช้), ม.19 (สิทธิเจ้าของข้อมูล)
- ม.22-24 (การเก็บรวบรวม/ความยินยอม), ม.26 (ข้อมูลอ่อนไหว)
- ม.37 (หน้าที่ผู้ควบคุมข้อมูล), ม.73 (การร้องเรียน)
- ม.77 (โทษแพ่ง), ม.79 (โทษอาญา), ม.90-92 (โทษปกครอง สูงสุด 5 ล้านบาท)

### ประมวลกฎหมายอาญา (26 มาตรา)
- ม.59 (เจตนา), ม.68 (ป้องกันโดยชอบ)
- ม.288-297 (ชีวิต/ร่างกาย), ม.326-330 (หมิ่นประมาท)
- ม.334-352 (ทรัพย์: ลักทรัพย์, ชิงทรัพย์, ปล้น, ฉ้อโกง, ยักยอก)
- ม.264-265 (ปลอมเอกสาร)

---

## 6. Architecture — 3 ระดับ

### ระดับ 1: ไฟล์ตรง ๆ (เสร็จแล้ว)
```
ผู้ใช้ถาม → Claude อ่านไฟล์ laws/ → ตอบ
```

### ระดับ 2: RAG + MCP (ปัจจุบัน ✅)
```
กฎหมาย → ตัดทีละมาตรา → Embedding → ChromaDB (Docker)
ผู้ใช้ถาม → Claude เรียก MCP search_law → ได้มาตราที่ตรง → ตอบ
```

### ระดับ 3: RAG — Cloud (อนาคต)
```
ย้าย ChromaDB → Supabase+pgvector / Pinecone (cloud)
เพิ่ม auto-update จากเว็บกฤษฎีกา
```

---

## 7. TODO

- [x] Setup ChromaDB + ingest scripts
- [x] สร้าง MCP Server (Streamable HTTP)
- [x] เชื่อม Claude Code ผ่าน .mcp.json
- [x] อัปเดต CLAUDE.md ให้ใช้ MCP แทนอ่านไฟล์
- [ ] เพิ่มกฎหมายเพิ่มเติม (ป.แพ่ง สัญญา/ครอบครัว/มรดก, พ.ร.บ.คอมพิวเตอร์)
- [ ] ทดสอบถาม-ตอบ กฎหมายหลาย ๆ ฉบับ
- [ ] (Production) ย้าย Vector DB ไป Cloud
- [ ] (Production) เพิ่ม auto-update จากเว็บกฤษฎีกา
