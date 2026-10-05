---
name: network-map
description: Use when Ahmed says "network map", "show architecture", "map services", "draw the system". Reads docker-compose + proxy code to generate an accurate ASCII network/service map showing all containers, ports, and data flow.
---

# network-map Skill

> Generate a live-accurate ASCII network/service map from actual config.
> Never invents — reads docker-compose and proxy code.

---

## Steps Claude follows

### 1. Read sources
In parallel:
- `/opt/garnet/docker-compose.yml` (from cVM) OR `~/Desktop/garnet/docker-compose.yml`
- `.env` → URLs and ports
- `.claude/docs/proxy.md` → data flow description

### 2. Build map

Output two views:

#### View 1 — Service topology
```
┌─────────────────────────────────────────────────────────────┐
│                    GARNET — Service Map                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Browser ──HTTPS──► [Caddy :443]                            │
│                           │                                  │
│                           ▼                                  │
│                   [open-webui :8080]                        │
│                   garnet-webui:21b68b8b7                    │
│                           │                                  │
│            ┌──────────────┤                                  │
│            │              │                                  │
│            ▼              ▼                                  │
│   [privacy-proxy :8080]  [ollama :11434]                    │
│   garnet-webui@sha256    (via proxy)                        │
│            │                                                 │
│   ┌────────┼────────┐                                       │
│   ▼        ▼        ▼                                       │
│ [Ollama] [OpenAI] [Anthropic]                               │
│  :11434   api.openai  api.anthropic                         │
│                                                             │
│  [Redis :6379] ◄── session mappings                        │
│  [Dashboard :8081] ◄── internal only                       │
└─────────────────────────────────────────────────────────────┘
```

#### View 2 — Request flow (privacy)
```
User sends:    "Max Mustermann at Enclaive"
       │
       ▼
[open-webui] → POST /openai/chat/completions
       │
       ▼
[privacy-proxy] → pseudonymize PII
       │         "PERSON_cc75 at ORG_bd3a"
       ▼
[LLM provider] → responds with tokens
       │
       ▼
[privacy-proxy] → restore real values
       │         "Max Mustermann at Enclaive"
       ▼
[open-webui] → user sees real names
```

### 3. Show network details
```
Network: garnet_default (Docker bridge)
Internal DNS:
  privacy-proxy → 172.18.0.x
  open-webui    → 172.18.0.x
  redis         → 172.18.0.x
  ollama        → 172.18.0.x

External ports:
  :443  → Caddy (HTTPS)
  :80   → Caddy (HTTP redirect)
  :8081 → Dashboard (127.0.0.1 only)
```

### 4. Flag mismatches
If actual docker-compose differs from CLAUDE.md architecture diagram → flag it.

---

## Rules
- Read actual docker-compose — never hardcode service names.
- Flag if a port is exposed that shouldn't be (0.0.0.0 on internal services).
- Show BOTH topology and data flow — they serve different audiences.
