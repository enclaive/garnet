# Enclaive Technology — Knowledge Base for Claude

> Sources: docs.enclaive.cloud/virtual-hsm, docs.enclaive.cloud/nitride, docs.enclaive.cloud/vault/cli/agent
> Purpose: Reference file so Claude can answer questions about Enclaive technologies accurately, based on official documentation.
> Project context: Health checker service for enclaive.cloud production infrastructure

---

## PART 1 — THE ENCLAIVE ECOSYSTEM (Big Picture)

Enclaive builds a **confidential computing platform**. Three main products work together:

```
┌─────────────────────────────────────────────────────────────┐
│                  ENCLAIVE PLATFORM                          │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │    VAULT     │  │   NITRIDE    │  │   BUCKYPAPER VM  │  │
│  │ Key/Secret   │  │  Workload    │  │  Confidential    │  │
│  │ Management   │  │  Identity +  │  │  Virtualization  │  │
│  │              │  │  Attestation │  │  (3D encryption) │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│                                                             │
│  Combined = vHSM (Virtual Hardware Security Module)         │
└─────────────────────────────────────────────────────────────┘
```

| Product | What it does | Analogy |
|---|---|---|
| **Vault** | Stores and manages secrets (passwords, keys, certs) | A safe for your secrets |
| **Nitride** | Gives each workload a cryptographic identity | Like a passport for your app/VM |
| **Buckypaper VM** | Encrypted VM — data protected at rest, in transit, in use | A sealed vault box that runs code |
| **vHSM** | All three combined in one service | Hardware HSM, but in the cloud |

---

## PART 2 — vHSM (Virtual HSM)

### What is vHSM?

A **Virtual Hardware Security Module** = cloud-native replacement for physical HSMs.

Physical HSMs are secure but:
- Fixed on-premises (hard to cloud-migrate)
- Expensive
- Not scalable

vHSM gives the same security guarantees but:
- Runs in the cloud (AWS, Azure, GCP)
- Scalable and elastic
- Supports compliance: GDPR, ISO 27001, NIST 800-53, FIPS 203/204/205

**Technical stack:**
```
vHSM = Vault (key mgmt) + Nitride (workload identity) + Buckypaper VM (confidential compute)
```

### Why vHSM? (3 cloud problems it solves)

| Problem | Description |
|---|---|
| **Single Point of Trust** | With classic cloud KMS, you must trust the CSP and their staff |
| **Single Point of Attack** | CSPs serve thousands of clients — one breach hits everyone |
| **Vendor Lock-in** | CSP proprietary APIs make switching expensive |

### Why BYOK (Bring Your Own Key) is not enough

BYOK = you generate your key and upload it to the CSP. But:
- Once uploaded, CSP infrastructure manages it
- CSP admins could access your keys
- Shared hardware (hypervisor breach) exposes both key and data
- No visibility into CSP operations (backups, replication)

vHSM solves this with **Confidential Computing**: data stays encrypted even while being processed.

### 3D Encryption (Buckypaper)

Data is encrypted at ALL three stages:

| Stage | What it means |
|---|---|
| **At rest** | Disk/storage encrypted inside the VM (NOT by the CSP — they have no access to the key) |
| **In transit** | All network traffic encrypted |
| **In use** | Data stays encrypted even while being processed in memory (Confidential Computing) |

Key principle: **no key material leaves the enclave in cleartext.**

### Attestable Boot (Integrity)

Ensures the system was not tampered with during boot:

1. VM starts → memory region selected (already encrypted)
2. Security Processor (SP) measures UEFI firmware (cryptographic hash)
3. UEFI verifies kernel signature
4. Kernel loads disk encryption engine
5. SP derives **binding/sealing key** from measured state + CPU identity
   - **Platform Binding**: key only works on this exact machine
   - **Key Sealing**: key only works if boot state matches expected trusted state
6. vHSM services start — all data written is encrypted before leaving the enclave

### vHSM Features

- Elastic secret provisioning
- Identity management
- Credential-based access control
- Multi-cloud: AWS, Azure, GCP
- 3D encrypted: in-use, at-rest, in-transit
- High-available RAFT cluster
- NIST FIPS 203/204/205 Post-Quantum Cryptography
- PKCS11 HSM integration
- Compliance: GDPR, C5, ISO 27001, NIST 800-53

### Key Concepts

| Term | Definition |
|---|---|
| **Sealed** | vHSM starts in this state — cannot handle any requests |
| **Unsealed** | Normal operating state |
| **Root Token** | Master token generated at init — has full access |
| **Unseal Key** | One of N key shares needed to unseal (Shamir secret sharing) |
| **Policy** | HCL rules defining what paths/operations a token can access |
| **Namespace** | Isolated environment with its own policies and secrets |
| **Lease** | Time-to-live attached to a secret — expires automatically |
| **Secret Engine** | Plugin that provides a category of secrets (kv, pki, ssh, transit…) |

---

## PART 3 — VAULT (Key & Secret Management)

Vault is the secret management layer inside vHSM. Based on HashiCorp Vault with Enclaive extensions.

### Environment Variables

```bash
export VAULT_ADDR='https://your-vhsm-instance:8200'   # server address
export VAULT_TOKEN='hvs.xxxxxxxxxxxx'                   # auth token
export ENCLAIVE_LICENCE='abcd-efgh-ijkl-mnop'          # required licence key
```

### Server Commands

```bash
# Dev server (local only — NOT production)
ENCLAIVE_LICENCE=<key> vhsm server -dev

# Dev server with TLS (staging)
ENCLAIVE_LICENCE=<key> vhsm server -dev-tls

# Production server with config file
vhsm server -config /path/to/config.json
```

### Docker (dev)
```bash
docker run --cap-add=IPC_LOCK -p 8200:8200 \
    -e ENCLAIVE_LICENCE=<key> \
    harbor.enclaive.cloud/enclaive-dev/vhsm:latest \
    server -dev -dev-listen-address="0.0.0.0:8200"
```

### Operator Commands (lifecycle)

```bash
vhsm operator init          # initialize cluster → generates unseal keys + root token
vhsm operator unseal        # unseal (run 3x with different keys by default)
vhsm operator seal          # seal the server
vhsm operator rotate        # rotate encryption key
vhsm operator generate-root # generate new root token
vhsm operator members       # list cluster nodes
vhsm operator diagnose      # troubleshoot startup problems
```

Init output example:
```
Unseal Key 1: sP/4C/fwIDjJmHEC2bi/1Pa43uKhsUQMmiB31GRzFc0R
Unseal Key 2: kHkw2xTBelbDFIMEgEC8NVX7NDSAZ+rdgBJ/HuJwxOX+
Unseal Key 3: +1+1ZnkQDfJFHDZPRq0wjFxEuEEHxDDOQxa8JJ/AYWcb
Initial Root Token: 6662bb4a-afd0-4b6b-faad-e237fb564568
```

### Status Command

```bash
vhsm status
```

Exit codes: `0` = unsealed (healthy), `1` = error, `2` = sealed

Output fields: Seal Type, Initialized, Sealed, Total Shares, Threshold, Version, Storage Type, HA Enabled

### Authentication & Login

```bash
# Login with token (interactive)
vhsm login

# Login with token directly
vhsm login s.3jnbMAKl1i4YS3QoKdbHzGXq

# Login with username/password
vhsm login -method=userpass username=my-username

# Login with GitHub
vhsm login -method=github -path=github-prod
```

Login flags: `-method`, `-path`, `-no-store`, `-token-only`, `-no-print`

### Policy Commands

Policies use HCL syntax to define access rules per path.

```bash
vhsm policy list
vhsm policy read my-policy
vhsm policy write my-policy /tmp/policy.hcl
vhsm policy delete my-policy
vhsm policy fmt my-policy.hcl
```

Example policy (HCL):
```hcl
path "secret/data/my-app/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
path "secret/data/config" {
  capabilities = ["read", "list"]
}
path "auth/token/lookup-self" {
  capabilities = ["read"]
}
```

Minimal policy for health checker monitoring:
```hcl
path "sys/health" {
  capabilities = ["read"]
}
```

### Secret Management Commands

```bash
# Read a secret
vhsm read secret/data/my-app

# Write a secret
vhsm write secret/data/my-app key=value

# Delete a secret
vhsm delete secret/data/my-app

# List secrets at a path
vhsm list secret/data/

# KV engine (recommended for key-value secrets)
vhsm kv get -mount=secret my-app
vhsm kv put -mount=secret my-app key=value
vhsm kv delete -mount=secret my-app
```

Equivalent curl:
```bash
curl --request GET --header "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/secret/data/my-app
```

### Namespace Commands

```bash
vhsm namespace create my-namespace
vhsm namespace list
```

### Production Config (config.json)

```json
{
  "storage": {
    "file": { "path": "/vhsm/data" }
  },
  "listener": [{
    "tcp": {
      "address": "0.0.0.0:8200",
      "tls_cert_file": "/vhsm/tls/server.crt",
      "tls_key_file": "/vhsm/tls/server.key"
    }
  }],
  "api_addr": "https://your-domain.com:8200",
  "cluster_addr": "https://your-domain.com:8201",
  "ui": true
}
```

Production checklist:
- Enable TLS
- Use persistent storage (file, Consul, DynamoDB — not inmem)
- Enable auth methods (not just root token)
- Define policies per workload
- Enable audit logging

### Health Check API (for monitoring — no auth required)

```
GET /v1/sys/health
```

```bash
curl https://shareddev.gtp.vhsm.enclaive.cloud/v1/sys/health
```

Expected healthy response (HTTP 200):
```json
{
  "initialized": true,
  "sealed": false,
  "standby": false
}
```

HTTP response codes:
| Code | Meaning |
|---|---|
| `200` | Initialized, unsealed, active — HEALTHY |
| `429` | Unsealed but in standby |
| `472` | DR (disaster recovery) mode |
| `501` | Not initialized |
| `503` | Sealed — UNHEALTHY |

Python health check:
```python
import httpx

async def check_vault(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{url}/v1/sys/health", timeout=5)
        data = r.json()
        healthy = (
            r.status_code == 200
            and data.get("initialized") == True
            and data.get("sealed") == False
        )
        return {
            "service": url,
            "status": "healthy" if healthy else "unhealthy",
            "sealed": data.get("sealed"),
            "initialized": data.get("initialized"),
            "http_code": r.status_code
        }
```

---

## PART 4 — VAULT AGENT

Vault Agent is a client daemon that runs alongside applications to handle authentication and secret delivery automatically — without the app needing to talk to Vault directly.

### What Vault Agent does

| Feature | Description |
|---|---|
| **Auto-Auth** | Automatically authenticates to Vault and renews tokens |
| **API Proxy** | Acts as a local proxy — app talks to agent, agent talks to Vault |
| **Caching** | Caches tokens and leased secrets locally |
| **Templating** | Renders secrets into config files using templates |
| **Process Supervisor** | Injects secrets as environment variables into a child process |

### Typical use case

Without agent:
```
App → must authenticate → Vault → get token → request secret
```

With agent:
```
App → Agent (local) → Agent handles auth + renewal → Vault
```

The app just reads from a file or local socket — no Vault code needed.

### Start Vault Agent

```bash
vault agent -config=/etc/vault/agent-config.hcl
```

### Agent config file (HCL) — example

```hcl
pid_file = "./pidfile"

vault {
  address = "https://vault-fqdn:8200"
  retry {
    num_retries = 5
  }
}

auto_auth {
  method "aws" {
    mount_path = "auth/aws-subaccount"
    config = {
      type = "iam"
      role = "foobar"
    }
  }
  sink "file" {
    config = {
      path = "/tmp/vault-token"
    }
  }
}

cache {}

api_proxy {
  use_auto_auth_token = true
}

listener "tcp" {
  address    = "127.0.0.1:8100"
  tls_disable = true
}

template {
  source      = "/etc/vault/server.key.ctmpl"
  destination = "/etc/vault/server.key"
}
```

### Agent config options

| Option | Description |
|---|---|
| `vault.address` | vHSM/Vault server URL |
| `auto_auth` | Auth method + sink (where to write the token) |
| `cache` | Enable local caching |
| `api_proxy` | Proxy Vault API via agent |
| `listener` | Local address agent listens on |
| `template` | Render secrets into files |
| `exec` | Run a child process with secrets as env vars |
| `exit_after_auth` | Exit after first successful auth (useful for one-shot tasks) |

### CLI flags

```bash
-log-level=info|debug|trace|warn|error
-log-format=standard|json
-log-file=/var/log/vault-agent.log
-log-rotate-bytes=<bytes>
-log-rotate-duration=24h
-log-rotate-max-files=5
```

### Agent API endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/agent/v1/quit` | Shutdown the agent (disabled by default) |

### Agent telemetry metrics

| Metric | Type | Description |
|---|---|---|
| `vault.agent.auth.failure` | counter | Auth failures |
| `vault.agent.auth.success` | counter | Auth successes |
| `vault.agent.proxy.success` | counter | Requests successfully proxied |
| `vault.agent.cache.hit` | counter | Cache hits |
| `vault.agent.cache.miss` | counter | Cache misses |

---

## PART 5 — NITRIDE (Workload Identity)

### What is Nitride?

Nitride = **workload identity management** — gives each VM, container, or serverless function its own cryptographic identity.

Analogy: like a TLS certificate for your workload, but issued by the **CPU itself** acting as a trusted notary.

### Problem Nitride solves

In cloud environments, many workloads need secrets:
- Database passwords
- API keys
- TLS certificates
- Disk encryption keys

Traditional IAM systems grant access to **users**. Nitride grants access to **certified, attestable workloads** — the first system to do this.

### How Nitride works (secret provisioning flow)

```
1. Workload starts in Buckypaper VM
        ↓
2. enclaivelet (attestation shim) runs
        ↓
3. enclaivelet attests environment to Nitride
   (proves: "I am a trusted, unmodified workload")
        ↓
4. Nitride validates attestation
        ↓
5. enclaivelet receives JWT auth token
        ↓
6. Workload uses JWT to request secrets from Vault
        ↓
7. Vault checks JWT + access policies → delivers secrets
        ↓
8. Secrets are provisioned into the workload (via TLS)
```

### Key components

| Component | Role |
|---|---|
| **enclaivelet** | Attestation shim running inside the workload — talks to Nitride |
| **provision** | Binary that delivers secrets into the workload after attestation |
| **Nitride server** | Validates attestation reports, issues JWT tokens |
| **RA-TLS** | Remote Attestation TLS — the protocol used for secure identity proofs |

### Nitride CLI (via vhsm nitride)

```bash
# Initialize auth, identities, policies, attestation
vhsm nitride init -namespacing @policy.hcl

# List attestations
vhsm nitride attestation list

# Check attestation report for a workload
vhsm nitride attestation -provider=local-none-debug report <uuid>
```

### Cloud-init integration (env vars)

When deploying a Buckypaper VM, these env vars configure Nitride:

```bash
export ENCLAIVE_PROTOCOL=sev-snp          # AMD SEV-SNP, Intel TDX, etc.
export ENCLAIVE_SOURCE=azure              # cloud provider: azure, aws, gcp
export ENCLAIVE_INSTANCE=<uuid>           # unique workload instance ID
export ENCLAIVE_RESOURCE=azure-vm         # resource name/label
export ENCLAIVE_NITRIDE=http://localhost:8200   # Nitride server
export ENCLAIVE_KEYSTORE=http://localhost:8200  # Vault server
export ENCLAIVE_FEATURES=ssh-pw:azure:user:root # optional features
```

### Nitride features

- AMD, Intel, ARM, NVIDIA GPU platform support
- AWS, Azure, GCP and other cloud providers
- Local, remote, and runtime workload attestation
- Policy-based attestation verification
- Quantum Enclave ready
- PKCS HSM integration for FIPS compliance

---

## PART 6 — PROJECT CONTEXT (health-checker service)

### Production instances to monitor

| Service | Health endpoint | Check |
|---|---|---|
| vhsm shareddev | `https://shareddev.gtp.vhsm.enclaive.cloud/v1/sys/health` | initialized=true, sealed=false |
| vhsm medicus | `https://medicus.gtp.vhsm.enclaive.cloud/v1/sys/health` | initialized=true, sealed=false |
| vhsm deutschlandplatform | `https://deutschlandplatform.gtp.vhsm.enclaive.cloud/v1/sys/health` | initialized=true, sealed=false |
| vhsm internaltest | `https://internaltest.gtp.vhsm.enclaive.cloud/v1/sys/health` | initialized=true, sealed=false |
| Nextcloud | `https://next.enclaive.cloud/status.php` | installed=true, maintenance=false |
| Vaultwarden | `https://vaultwarden.enclaive.cloud/alive` | HTTP 200 |
| Mattermost | `https://mattermost.enclaive.cloud/api/v4/system/ping` | status=OK |
| console | `https://console.enclaive.cloud/health` | TBD |
| vhsm.enclaive.cloud | `https://vhsm.enclaive.cloud/v1/sys/health` | initialized=true, sealed=false |

### Alert rules

| Condition | Alert |
|---|---|
| 3 consecutive failures | Service down alert |
| Response time > 2s | Latency alert |
| TLS cert expiry < 30 days | Certificate expiry alert |
| Vault `sealed=true` | Vault sealed alert |
| Nextcloud `maintenance=true` | Maintenance mode alert |

### Alert destinations

- Email: `alerts@enclaive.io`
- Mattermost: channel TBD (webhook URL needed)

### Health checker API design

```
GET /check/vhsm/<instance-id>
GET /check/nextcloud
GET /check/vaultwarden
GET /check/mattermost
GET /check/all
```

Response format:
```json
{
  "timestamp": "2026-06-11T12:00:00Z",
  "checks": [
    { "service": "vhsm-shareddev", "status": "healthy", "latency_ms": 85 },
    { "service": "nextcloud",      "status": "healthy", "latency_ms": 102 }
  ]
}
```

### Python tech stack

- `httpx` — async HTTP requests
- `asyncio` — parallel checks
- `apscheduler` — run checks every N minutes
- `smtplib` — email alerts (built-in)

---

## PART 7 — TROUBLESHOOTING

| Problem | Command |
|---|---|
| Server won't start | `vhsm operator diagnose` |
| Check sealed/unsealed state | `vhsm status` |
| Unseal after restart | `vhsm operator unseal` (run 3x) |
| Check logs live | `vhsm monitor` |
| Debug server | `vhsm debug` |
| PKI health | `vhsm pki health-check` |
| Version info | `vhsm version` |
| List version history | `vhsm version-history` |

---

## PART 8 — DOCUMENTATION LINKS

| Topic | URL |
|---|---|
| vHSM overview | https://docs.enclaive.cloud/virtual-hsm |
| What is vHSM | https://docs.enclaive.cloud/virtual-hsm/documentation/what-is-virtual-hsm |
| Why vHSM | https://docs.enclaive.cloud/virtual-hsm/documentation/why-a-vhsm |
| How it works | https://docs.enclaive.cloud/virtual-hsm/documentation/how-does-it-work |
| Use case | https://docs.enclaive.cloud/virtual-hsm/documentation/use-case |
| Start server | https://docs.enclaive.cloud/virtual-hsm/documentation/getting-started/start-the-server |
| CLI reference | https://docs.enclaive.cloud/virtual-hsm/cli |
| vhsm operator | https://docs.enclaive.cloud/virtual-hsm/cli/configuration-and-management/vhsm-operator |
| vhsm policy | https://docs.enclaive.cloud/virtual-hsm/cli/authentication-and-authorization/vhsm-policy |
| vhsm status | https://docs.enclaive.cloud/virtual-hsm/cli/server-and-infrastructure-management/vhsm-status |
| vhsm login | https://docs.enclaive.cloud/virtual-hsm/cli/authentication-and-authorization/vhsm-login |
| Nitride overview | https://docs.enclaive.cloud/nitride |
| Vault Agent | https://docs.enclaive.cloud/vault/cli/agent |
| vHSM sitemap | https://docs.enclaive.cloud/virtual-hsm/sitemap.md |

---

*Generated from official Enclaive documentation — June 11, 2026*