[🇺🇸 English](../../README.md) | [🇨🇳 中文](../../README.zh.md)

## 2. Deploy Execution Model (Remote exec / GitHub pull)

- `scripts/setup-ai-workspace-all-in-one.sh` runs **on the remote host**, purely in remote exec mode.
- **Do not use rsync**; the required repositories are `pull`ed directly from GitHub by the remote host:
  - Playbooks: `https://github.com/ai-workspace-infra/playbooks.git`
  - Core Skills: `https://github.com/ai-workspace-lab/xworkspace-core-skills.git`
  - Console (where the script itself resides): `https://github.com/ai-workspace-lab/XLaunch.git`
  - QMD: `https://github.com/ai-workspace-services/qmd.git`
  - LiteLLM: `https://github.com/ai-workspace-services/litellm.git`
- Implication: **Local commits must be pushed to the above GitHub repositories before remote deployment can fetch the changes**.

> ⚠️ Note the repository address inconsistency: the local `origin` of playbooks is currently `git@github.com:x-evor/playbooks.git`, but the authoritative source for deployment is `ai-workspace-infra/playbooks`. During the implementation phase, align the pull source in the script to `ai-workspace-infra/playbooks` and push commits to that repository.

### 2.1 Environment Variable Interface Contract (Authoritative)

The bootstrap entry is fixed to the original script in the console repository. All exposure/security/optional desktop behaviors are controlled via environment variables prior to `bash -`.

**Standard Install** (default secure local workspace, requires only one unified token):

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -
```

**All Parameters (Defaults and Recommended Usage):**

| Variable | Default | Recommended Use |
|---|---|---|
| `TOKEN` | generated or reused | Set a **unified** auth token for Bridge / Portal / LiteLLM / OpenClaw / Vault |
| `AI_WORKSPACE_SECURITY_LEVEL` | `standard` | Use `strict` for public/semi-public hosts |
| `XWORKMATE_BRIDGE_PUBLIC_ACCESS` | `true` | Bridge is the default sole public service; explicitly set `false` to disable external access |
| `XWORKMATE_BRIDGE_DOMAIN` | host-specific | Set the public Bridge domain, e.g., `acp-bridge.onwalk.net` |
| `XWORKSPACE_CONSOLE_PUBLIC_ACCESS` | `false` | Enable only when Portal must be public; local-first is safer |
| `XWORKSPACE_CONSOLE_ENABLE_XRDP` | `false` | Enable only when remote desktop access is required |
| `GATEWAY_OPENCLAW_PUBLIC_ACCESS` | `false` | Keep false unless OpenClaw must be exposed directly |
| `VAULT_PUBLIC_ACCESS` | `false` | Keep false for normal deployments |
| `LITELLM_API_CADDY_STRICT_WHITELIST` | `false` | Enable in strict mode when LiteLLM is exposed via Caddy |

**Advanced Install Example:**

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | \
  AI_WORKSPACE_SECURITY_LEVEL=strict \
  XWORKSPACE_CONSOLE_ENABLE_XRDP=true \
  XWORKSPACE_CONSOLE_PUBLIC_ACCESS=true \
  XWORKMATE_BRIDGE_PUBLIC_ACCESS=true \
  GATEWAY_OPENCLAW_PUBLIC_ACCESS=false \
  VAULT_PUBLIC_ACCESS=false \
  LITELLM_API_CADDY_STRICT_WHITELIST=true \
  TOKEN="your-unified-auth-token" \
  bash -
```

**Target Host (ACP Bridge) Example:**

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | \
  XWORKMATE_BRIDGE_DOMAIN=acp-bridge.onwalk.net \
  XWORKMATE_BRIDGE_PUBLIC_ACCESS=true \
  AI_WORKSPACE_SECURITY_LEVEL=strict \
  bash -
```

> Key Alignment: `XWORKMATE_BRIDGE_PUBLIC_ACCESS` defaults to **`true`**——Bridge is the **default and only public** service (with its domain passed customized via `XWORKMATE_BRIDGE_DOMAIN`); other services (Console/OpenClaw/Vault/QMD/Hermes/PG/LiteLLM) default to `false` and remain listening on `127.0.0.1` locally. If you need to disable external access to the Bridge, explicitly set `XWORKMATE_BRIDGE_PUBLIC_ACCESS=false`. The `TOKEN` output must be kept private——do not copy it into frontend source code or commit it to Git.

### 2.2 Expected Final Output (Deployment Summary)

Upon successful deployment, the script will print the deployment domain and token **exactly once**, followed by the running status of each service:

- AI Workspace domain and token (displayed once only)
- OpenClaw
- QMD
- PostgreSQL
- Vault
- Workspace Portal / Console
- LiteLLM
- Hermes
- Agent CLI: opencode, gemini, codex, claude

### 2.3 Local macOS Validation Mode

On macOS, the script defaults to **local validation mode** and starts the Portal at `http://127.0.0.1:17000`. If validation fails due to port conflict, stop the existing local service or retry in a clean session.

---

## 7. Deployment and Validation

### 7.1 Deployment Command (Execute on the target host or in an environment with network/SSH access to it)

```bash
# Remote exec: The script pulls the repos from GitHub onto the host and runs ansible to localhost
# Adopts §2.1 authoritative env var contract (Target Host Example)
ssh root@acp-bridge.onwalk.net \
  'curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | \
   XWORKMATE_BRIDGE_DOMAIN=acp-bridge.onwalk.net \
   XWORKMATE_BRIDGE_PUBLIC_ACCESS=true \
   AI_WORKSPACE_SECURITY_LEVEL=strict \
   bash -'
```

### 7.2 Validation Checklist

- [ ] The script finishes by outputting a unified summary, and the Bridge displays `https://acp-bridge.onwalk.net`.
- [ ] `curl -I https://acp-bridge.onwalk.net` is reachable; other service ports are listening only on `127.0.0.1`.
- [ ] `systemctl --user is-active` shows each service is `active`.
- [ ] `opencode/gemini/codex/claude --version` are all executable.
- [ ] Credentials appear only once in the summary.

---

## Appendix A. AI Workspace All-in-One Setup (Bootstrap User Guide)

> Official installation guide intended for end users, integrated into this plan as the single authoritative source.
> This appendix has two alignments compared to the upstream README: ① `XWORKMATE_BRIDGE_PUBLIC_ACCESS` defaults to **`true`** (Bridge is the default sole public service); ② `acp-bridge.onwalk.net` is a **host-specific custom parameter** passed via `XWORKMATE_BRIDGE_DOMAIN`.

This is the recommended bootstrap entry point to install the AI Workspace Runtime from the `xworkspace-console` repository. The script uses this repository as the public entry point, then prepares runtime services through AI Workspace playbooks and component repositories.

### A.1 Standard Install

Suitable for default secure local workspaces where only a generated or existing unified token is needed:

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -
```

### A.2 Advanced Install

Use environment variables before `bash -` to customize the exposure surface, security level, and optional desktop features:

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | \
  AI_WORKSPACE_SECURITY_LEVEL=strict \
  XWORKSPACE_CONSOLE_ENABLE_XRDP=true \
  XWORKSPACE_CONSOLE_PUBLIC_ACCESS=true \
  XWORKMATE_BRIDGE_PUBLIC_ACCESS=true \
  GATEWAY_OPENCLAW_PUBLIC_ACCESS=false \
  VAULT_PUBLIC_ACCESS=false \
  LITELLM_API_CADDY_STRICT_WHITELIST=true \
  TOKEN="your-unified-auth-token" \
  bash -
```

### A.3 Recommended Parameters

| Variable | Default | Recommended Use |
|---|---|---|
| `TOKEN` | generated or reused | Set one unified auth token for Bridge, Portal, LiteLLM, OpenClaw, and Vault |
| `AI_WORKSPACE_SECURITY_LEVEL` | `standard` | Use `strict` for public/semi-public hosts |
| `XWORKMATE_BRIDGE_PUBLIC_ACCESS` | `true` | Bridge is the default sole public service; explicitly set `false` to disable external access |
| `XWORKMATE_BRIDGE_DOMAIN` | host-specific (custom) | Public Bridge domain, e.g., `acp-bridge.onwalk.net` |
| `XWORKSPACE_CONSOLE_PUBLIC_ACCESS` | `false` | Enable only when Portal must be public; local-first is safer |
| `GATEWAY_OPENCLAW_PUBLIC_ACCESS` | `false` | Keep false unless OpenClaw must be exposed directly |
| `VAULT_PUBLIC_ACCESS` | `false` | Keep false for normal deployments |
| `LITELLM_API_CADDY_STRICT_WHITELIST` | `false` | Enable for strict deployments when LiteLLM is exposed via Caddy |
| `XWORKSPACE_CONSOLE_ENABLE_XRDP` | `false` | Enable only when remote desktop access is required |

### A.4 Target Host Example (Current ACP Bridge Host)

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | \
  XWORKMATE_BRIDGE_DOMAIN=acp-bridge.onwalk.net \
  XWORKMATE_BRIDGE_PUBLIC_ACCESS=true \
  AI_WORKSPACE_SECURITY_LEVEL=strict \
  bash -
```

### A.5 Expected Final Output

Upon successful deployment, the script prints the deployment domain and token **exactly once**, and then reports the status of the following services:

- AI Workspace domain and token
- OpenClaw
- QMD
- PostgreSQL
- Vault
- Workspace Portal / Console
- LiteLLM
- Agent CLI: opencode, gemini, codex, claude

> The Token output must be kept private, and not copied into frontend source code or committed to Git.

### A.6 Local macOS Validation

On macOS, the script defaults to local validation mode and starts the Portal at `http://127.0.0.1:17000`. If validation fails due to port conflicts, stop any existing local service or retry in a clean session.
