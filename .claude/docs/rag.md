# rag.md — RAG, Chunking, Retrieval, KB

## How RAG works in Garnet

```
Ingestion (on upload):
  upload → OWU parse → RecursiveCharacterTextSplitter → embed (all-MiniLM-L6-v2) → Chroma
  proxy NOT involved. Chroma stores RAW text (no pseudonymization).

Retrieval (every query):
  query → embed → top-K chunks → OWU builds <source> system message
  → proxy pseudonymizes chunks → LLM → proxy depseudonymizes → user
```
⚠️ Pseudonymization runs on user query BEFORE retrieval (architectural limit). Long-term fix: post-retrieval pseudonymization.

## Current config

| Setting | Value | Note |
|---|---|---|
| splitter | RecursiveCharacterTextSplitter | \n\n → \n → space → char |
| chunk_size | 1000 | was 1500 |
| chunk_overlap | 100 | was 200 |
| markdown splitter | OFF | ON caused 67k-char chunk bug |
| embedding | sentence-transformers/all-MiniLM-L6-v2 | local CPU, privacy-safe |
| bypass embedding | OFF | must stay OFF |
| full context mode | OFF | ON caused Opus 400 |
| search | hybrid BM25 + semantic | BM25 catches exact names |
| BM25 weight | 0.5 | |
| top_k | 15 | was 3 |
| reranker | BAAI/bge-reranker-v2-m3 | local, free |
| reranker top_k | 6 | was 3 |
| relevance threshold | 0 | |
| RAG_SYSTEM_CONTEXT | True | forces chunks into role:system |

## Query Expansion (replaced HyDE)

Calls `gpt-4o-mini` → 3 search variants → concatenated with pseudonymized question → enriched string injected. Togglable via localStorage store with (i) tooltip. ~7s/request → parallel execution proposed (pending Seb).

## Problems fixed

1. **Product names pseudonymized as ORG** — "Buckypaper", "Dyneemes", "what products and solutions" flagged ORG (spaCy threshold 0.5 too low). Fix in `pseudonymizer.py`: drop ORG if lowercase start OR score ≤ 0.85. → lowercase phrase filtered, weak score filtered, "Enclaive GmbH" kept. (Full code in proxy.md.)
2. **Only 3 sources retrieved** — top_k 3 → 15, reranker 3 → 6.
3. **KB docs don't list products explicitly** — RAG answers only from docs. Ask Alexa to add a product catalog doc.

## Opus + large context (chunks fix)

Opus + KB → 400. OWU injected full KB as system message (67k chars); Anthropic stricter than GPT (128k). Old proxy had `if len > 50000: skip` → sent RAW text to Anthropic → 400.

Fix (deployed) in `main.py` — chunked pseudonymization, NOT skip:
```python
if len(content_text) > 50000:
    chunks = [content_text[i:i+10000] for i in range(0, len(content_text), 10000)]
    pseudo = "".join(pseudonymize(c, session_id, store.get_store(), enabled_types=enabled_types) for c in chunks)
    msg["content"] = rebuild_content(msg["content"], pseudo)
    continue
```
Same `session_id` → same entity = same token across chunks.
OWU config also: full context OFF, markdown splitter OFF, top_k 6.
Note: `split_at_safe_boundary` splits LLM **output** (SSE); this splits file **input** before pseudonymization — two different things.
Side effect: Opus sees top-6 chunks, not full KB → slightly less context on huge KBs.

Pending better fix (Seb): per-provider context cap (Anthropic 40k, GPT full) · upgrade embedding to `text-embedding-3-small` (needs reindex).

## Roadmap

| Step | Status |
|---|---|
| RecursiveCharacterTextSplitter | ✅ |
| hybrid + top_k=15 | ✅ |
| reranking bge-v2-m3 | ✅ |
| ORG false-positive fix | ✅ |
| chunk_size 1000 + markdown OFF + full-context OFF | ✅ |
| nomic-embed-text / text-embedding-3-small | ⏳ needs reindex |
| semantic chunking | ⏳ future |

## Key commands

```bash
# RAG config in OWU DB
ssh root@65.108.38.50 "docker exec garnet-open-webui-1 python3 -c \"
import sqlite3,json
c=json.loads(sqlite3.connect('/app/backend/data/webui.db').execute('SELECT data FROM config').fetchone()[0])
[print(k,':',v) for k,v in c.get('rag',{}).items()]
\""

# test pseudonymization
ssh root@65.108.38.50 "docker exec garnet-privacy-proxy-1 python3 -c \"
from app.pseudonymizer import pseudonymize
print(pseudonymize('Garnet, Buckypaper, Dyneemes, Enclaive GmbH','test',{}))
\""

# local RAG test on cVM
ssh root@65.108.38.50 "docker exec garnet-open-webui-1 pip install pymupdf rank-bm25 --quiet"
scp yourfile.pdf root@65.108.38.50:/opt/garnet/
ssh root@65.108.38.50 "docker cp /opt/garnet/yourfile.pdf garnet-open-webui-1:/tmp/ && docker exec garnet-open-webui-1 python3 /tmp/test_rag_current.py"
```

## k8s note

ChromaDB KB empty in k8s — Alexa must re-upload docs after migration.
