---
name: enclaive-tech
description: >
  Use this skill for ANY question about Enclaive technologies: vHSM (Virtual HSM), Vault,
  Nitride, Buckypaper VMs, attestation, confidential computing, workload identity, secret
  management, or any enclaive.cloud product. Also use when working on the health-checker
  project for enclaive.cloud production services. Triggers include: "vhsm", "enclaive",
  "nitride", "buckypaper", "vault sealed", "attestation", "vault agent", "enclaivelet",
  "provision secrets", "health check enclaive", or any question about enclaive.cloud
  infrastructure. Always consult this skill before answering Enclaive-related questions —
  answers must be grounded in official documentation, not general Vault/HSM knowledge.
---

# Enclaive Tech Skill

This skill ensures all answers about Enclaive technologies are grounded in the **official
documentation** from these four sources:

| Source | URL | Content |
|---|---|---|
| **vHSM docs** | https://docs.enclaive.cloud/virtual-hsm | Full vHSM reference |
| **Nitride docs** | https://docs.enclaive.cloud/nitride | Workload identity & attestation |
| **Vault Agent docs** | https://docs.enclaive.cloud/vault/cli/agent | Agent daemon reference |
| **vHSM sitemap** | https://docs.enclaive.cloud/virtual-hsm/sitemap.md | All vHSM pages index |

---

## Step 1 — Check the reference file first

Before answering, `view` the bundled reference:

```
/path-to-skill/references/enclaivetech.md
```

This file contains pre-fetched content from all four documentation sources, organized into
8 parts:
- Part 1: Ecosystem overview (Vault + Nitride + Buckypaper)
- Part 2: vHSM — concept, 3D encryption, attestable boot, features
- Part 3: Vault — all commands, health check API, production config
- Part 4: Vault Agent — auto-auth, proxy, caching, templating, config
- Part 5: Nitride — workload identity, attestation flow, enclaivelet
- Part 6: Project context — production instances, alert rules, health checker design
- Part 7: Troubleshooting reference
- Part 8: All documentation links

---

## Step 2 — If the reference file doesn't answer the question

Use Firecrawl MCP to fetch live docs. Prefer this over raw web_fetch — it returns clean markdown.

```
# Get the full page list
mcp__firecrawl__firecrawl_scrape { "url": "https://docs.enclaive.cloud/virtual-hsm/sitemap.md", "formats": ["markdown"] }

# Fetch a specific page
mcp__firecrawl__firecrawl_scrape { "url": "https://docs.enclaive.cloud/virtual-hsm/documentation/how-does-it-work", "formats": ["markdown"] }
mcp__firecrawl__firecrawl_scrape { "url": "https://docs.enclaive.cloud/nitride/documentation/concepts/attestation", "formats": ["markdown"] }
mcp__firecrawl__firecrawl_scrape { "url": "https://docs.enclaive.cloud/vault/cli/agent", "formats": ["markdown"] }

# Search across enclaive docs for a specific topic
mcp__firecrawl__firecrawl_search { "query": "<topic> site:docs.enclaive.cloud", "limit": 5 }
```

Or use the GitBook ask API for targeted questions:
```
mcp__firecrawl__firecrawl_scrape { "url": "https://docs.enclaive.cloud/virtual-hsm/virtual-hsm.md?ask=<your question>", "formats": ["markdown"] }
```

---

## Step 3 — Answer rules

1. **Ground answers in documentation** — never answer from general Vault/HashiCorp knowledge
   alone; Enclaive has differences (ENCLAIVE_LICENCE, vhsm vs vault CLI prefix, Nitride
   integration, Buckypaper specifics).

2. **Note the CLI prefix difference** — Enclaive uses `vhsm` not `vault`:
   ```bash
   vhsm server -dev        # correct
   vault server -dev       # wrong for this project
   ```

3. **For health check questions** — always reference `/v1/sys/health` endpoint behavior:
   - HTTP 200 + initialized=true + sealed=false = healthy
   - HTTP 503 = sealed (critical alert needed)
   - No auth token required for this endpoint

4. **For the monitoring project** — reference Part 6 of the reference file for the list
   of production instances, alert rules, and health checker API design.

5. **If a page is missing or outdated** — use the GitBook ask API, which queries the
   full documentation corpus dynamically.

---

## Quick reference — most-used commands

```bash
# Server lifecycle
ENCLAIVE_LICENCE=<key> vhsm server -dev
vhsm operator init
vhsm operator unseal
vhsm status

# Auth
vhsm login
vhsm login -method=userpass username=<user>

# Secrets
vhsm kv get -mount=secret <path>
vhsm kv put -mount=secret <path> key=value
vhsm read secret/data/<path>

# Policy
vhsm policy write <name> <file.hcl>
vhsm policy read <name>

# Health check (no auth needed)
curl https://<instance>/v1/sys/health

# Nitride / attestation
vhsm nitride init -namespacing @policy.hcl
vhsm nitride attestation list
```

---

## Key concepts cheat sheet

| Term | One-line definition |
|---|---|
| vHSM | Vault + Nitride + Buckypaper in one — cloud-native Hardware Security Module |
| Sealed | Server started but locked — cannot serve requests until unsealed |
| Buckypaper VM | Confidential VM with 3D encryption (at rest + in transit + in use) |
| Nitride | Gives each workload a cryptographic identity via CPU attestation |
| enclaivelet | Shim that runs inside a workload to request attestation from Nitride |
| RA-TLS | Remote Attestation TLS — how Nitride proves workload identity |
| Policy (HCL) | Rules defining which paths/operations a token can access |
| Lease | Time-to-live on a secret — expires automatically |
| Unseal key | One of N key shares needed to unseal after restart (Shamir secret sharing) |
| ENCLAIVE_LICENCE | Required env var — licence key for running vHSM |

---

## Production instances (this project)

```
vhsm:     shareddev.gtp.vhsm.enclaive.cloud       → GET /v1/sys/health
vhsm:     medicus.gtp.vhsm.enclaive.cloud          → GET /v1/sys/health
vhsm:     deutschlandplatform.gtp.vhsm.enclaive.cloud → GET /v1/sys/health
vhsm:     internaltest.gtp.vhsm.enclaive.cloud     → GET /v1/sys/health
vhsm:     vhsm.enclaive.cloud                      → GET /v1/sys/health
nextcloud: next.enclaive.cloud                     → GET /status.php
vaultwarden: vaultwarden.enclaive.cloud            → GET /alive
mattermost: mattermost.enclaive.cloud              → GET /api/v4/system/ping
console:   console.enclaive.cloud                  → GET /health (TBD)
```