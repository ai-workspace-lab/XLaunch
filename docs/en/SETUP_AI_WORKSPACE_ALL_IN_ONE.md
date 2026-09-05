[🇺🇸 English](../../README.md) | [🇨🇳 中文](../../README.zh.md)

# AI Workspace All-in-One Setup

This is the recommended bootstrap entry for installing AI Workspace Runtime from the `xworkspace-console` repository.

The bootstrap script uses this repository as the public entrypoint, then prepares the runtime services through the AI Workspace playbooks and component repositories.

## 1. Standard Install

Use this when you want the default secure local workspace and only need a generated or existing unified token.

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -
```

## 2. Advanced Install

Use environment variables before `bash -` to customize exposure, security, and optional desktop features.

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | \
  AI_WORKSPACE_SECURITY_LEVEL=strict \
  XWORKSPACE_CONSOLE_ENABLE_XRDP=true \
  XWORKSPACE_CONSOLE_PUBLIC_ACCESS=true \
  XWORKMATE_BRIDGE_PUBLIC_ACCESS=true \
  GATEWAY_OPENCLAW_PUBLIC_ACCESS=false \
  VAULT_PUBLIC_ACCESS=false \
  LITELLM_API_CADDY_STRICT_WHITELIST=true \
  AI_WORKSPACE_AUTH_TOKEN="your-unified-auth-token" \
  bash -
```

> Subcommands are passed as positional args to `bash -`: `... | bash -s -- uninstall`.

## 3. Subcommands

Passed as the first positional arg (`... | bash -s -- <subcommand>`).

| Subcommand | Effect |
| --- | --- |
| `uninstall` | Stop & remove all AI Workspace apps/services (macOS launchd; Linux systemd units + docker containers). Config, tokens and data under `$HOME` are **kept**. |
| `uninstall --purge` | Same teardown, then **delete** config/state/token/cache dirs (`~/.config/xworkspace`, `~/.local/state/xworkspace`, `~/.openclaw`, `~/.ai_workspace_auth_token`, `/tmp/ai-workspace-deploy`; plus `/opt/ai-workspace` & `/etc/ai-workspace` on Linux as root). Prints a plan first, reports each path removed/absent. |

## 4. Optional Parameters (Environment Variables)

Pass before `bash -`. Full set of supported options, grouped by purpose.

### 4.1 Public Exposure & Security

| Variable | Default | Notes |
| --- | --- | --- |
| `AI_WORKSPACE_SECURITY_LEVEL` | `standard` | `strict` for public/semi-public hosts (locks down public web APIs). |
| `XWORKMATE_BRIDGE_PUBLIC_ACCESS` | `false` | Expose Bridge via Caddy (typically the only public service on a public-IP host). |
| `XWORKSPACE_CONSOLE_PUBLIC_ACCESS` | `false` | Expose Portal/Console. Local-only (`127.0.0.1:17000`) by default is safer. |
| `GATEWAY_OPENCLAW_PUBLIC_ACCESS` | `false` | Expose the OpenClaw gateway. |
| `VAULT_PUBLIC_ACCESS` | `false` | Keep false for normal deployments. |
| `LITELLM_API_CADDY_STRICT_WHITELIST` | `false` | With strict + LiteLLM behind Caddy, restrict the public gateway path whitelist. |
| `LITELLM_CADDY_CONFIG_ENABLED` | deployment-dependent | Whether to render a Caddy site for LiteLLM. |
| `XWORKSPACE_CONSOLE_ENABLE_XRDP` | `false` | Install XRDP remote desktop (only if graphical remote needed). |
| `XWORKMATE_BRIDGE_DOMAIN` | host-specific | Public Bridge domain, e.g. `acp-bridge.onwalk.net`. |

### 4.2 Unified Auth Token

First non-empty of: `AI_WORKSPACE_AUTH_TOKEN` → `XWORKSPACE_CONSOLE_AUTH_TOKEN` → `XWORKMATE_BRIDGE_AUTH_TOKEN` → `BRIDGE_AUTH_TOKEN` → `INTERNAL_SERVICE_TOKEN` → `DEPLOY_TOKEN` is used as the unified token (Bridge / LiteLLM / OpenClaw / Vault). If all unset it is **auto-generated** into `AI_WORKSPACE_AUTH_TOKEN_FILE` (default `~/.ai_workspace_auth_token`). The Vault root token can be set separately via `VAULT_SERVER_ROOT_ACCESS_TOKEN`.

### 4.3 Runtime Modes

| Variable | Default | Notes |
| --- | --- | --- |
| `AI_WORKSPACE_RUNTIME_MODES` | `docker,systemd` | Runtime modes; `docker` and `k3s` are mutually exclusive. |
| `POSTGRESQL_DEPLOY_MODE` | `compose` | Deployment mode: `compose` (Docker container), `native` (Linux apt/systemd, macOS Homebrew), or `external` (existing external database, skips local install/start). Defaults to `external` if `VAULT_DEPLOY_MODE=external` or if `POSTGRESQL_DATABASE_URL` is set. |
| `POSTGRESQL_DATABASE_URL` | none | External PostgreSQL database URL (e.g. `postgres://account:<masked_token>@127.0.0.1:15432/account?sslmode=disable`). Specifying this will automatically parse the host/port/user/password components and inject them into the deployment environment. |
| `POSTGRESQL_ADMIN_USER` | `postgres` | Superuser username for external PostgreSQL. Used in `external` mode to provision databases and users. If unset, parsed from `POSTGRESQL_DATABASE_URL` (but note that if the URL uses a non-admin user, you should explicitly set this to ensure creation privileges). |
| `POSTGRESQL_ADMIN_PASSWORD` | none | Superuser password for external PostgreSQL. If unset, parsed from `POSTGRESQL_DATABASE_URL` or read from target shadow file `/root/.ai_workspace_postgres_password` (for Debian/Ubuntu targets). |

### 4.4 Offline Package (acceleration / air-gap)

| Variable | Default | Notes |
| --- | --- | --- |
| `AI_WORKSPACE_OFFLINE_MODE` | `auto` | `auto` (try offline, fall back online) / `force` / `off`. |
| `AI_WORKSPACE_OFFLINE_PACKAGE` | none | Local package file/dir or URL. |
| `AI_WORKSPACE_OFFLINE_PACKAGE_URL` | none | Direct tarball URL. |
| `AI_WORKSPACE_OFFLINE_PACKAGE_BASE_URL` | none | Mirror dir containing the target tarball; empty skips the mirror. |
| `AI_WORKSPACE_OFFLINE_RELEASE_TAG` | `latest` | GitHub Release tag or `latest`. |
| `AI_WORKSPACE_OFFLINE_REPO` | `ai-workspace-lab/xworkspace-console` | Repo hosting offline packages. |
| `AI_WORKSPACE_OFFLINE_AUTO_DOWNLOAD` | `true` | In auto mode, fetch the matching package from GitHub Releases (reassembles split parts). |
| `AI_WORKSPACE_OFFLINE_WORK_DIR` | `/tmp/ai-workspace-offline` | Extraction work dir. |

> Source priority: `OFFLINE_PACKAGE` → `OFFLINE_PACKAGE_URL` → `OFFLINE_PACKAGE_BASE_URL/<file>` → else `AUTO_DOWNLOAD` via GitHub Releases. On failure falls back online per-OS (apt/yum or macOS homebrew + git clone + online runtime fetch).

### 4.5 Performance / Concurrency / Locks

| Variable | Default | Notes |
| --- | --- | --- |
| `AI_WORKSPACE_PREFETCH_ENABLED` | `true` | Prefetch repos/components. |
| `AI_WORKSPACE_PREFETCH_DIR` | `/var/tmp/ai-workspace-prefetch` | Prefetch dir. |
| `AI_WORKSPACE_MAX_PARALLEL_JOBS` | `auto` | Concurrency cap (never exceeds 2× online CPU cores). |
| `AI_WORKSPACE_SPLIT_PHASES` | `true` | Phased execution. |
| `AI_WORKSPACE_RUNTIME_PREBUILD_ENABLED` | `false` | Prebuild runtime. |
| `AI_WORKSPACE_DEPLOYMENT_LOCK_TIMEOUT` | `1800` | Deployment mutex wait (s). |
| `AI_WORKSPACE_APT_LOCK_TIMEOUT` | `900` | Wait for dpkg/apt lock (s) (avoids racing cloud-init/unattended-upgrades). |

### 4.6 Source/Version Overrides (dev & offline customization)

| Variable | Notes |
| --- | --- |
| `PLAYBOOK_DIR` | Local playbooks checkout (handy for macOS validation). |
| `XWORKSPACE_CONSOLE_DIR` | Local xworkspace-console checkout (macOS). |
| `XWORKSPACE_CONSOLE_SOURCE_REPO` / `XWORKSPACE_CONSOLE_SOURCE_VERSION` | Git source/version for the Linux console playbook. |
| `XWORKSPACE_CONSOLE_RUNTIME_ARCHIVE` / `QMD_RUNTIME_ARCHIVE` | Prebuilt runtime tar paths (offline). |
| `LITELLM_PACKAGE_SPEC` / `AI_WORKSPACE_PREBUILT_COMPONENTS_REQUIRED` | LiteLLM package spec / require prebuilt components. |
| `OPENCLAW_MULTI_SESSION_PLUGIN_PACKAGE_SPEC` / `OPENCLAW_MULTI_SESSION_PLUGIN_DIR` | OpenClaw plugin source / local checkout (macOS link install). |
| `BRANCH` | Git branch, tag, or commit hash of the playbooks repository to deploy. Supported by suffixing the installer URL path (e.g. `curl -sfL https://install.svc.plus/ai-workspace/v1.1.5 | bash`), or by setting this variable explicitly. |

## 5. Target Host Example

For the current ACP Bridge host:

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | \
  XWORKMATE_BRIDGE_DOMAIN=acp-bridge.onwalk.net \
  XWORKMATE_BRIDGE_PUBLIC_ACCESS=true \
  AI_WORKSPACE_SECURITY_LEVEL=strict \
  bash -
```

## 6. Expected Final Output

After a successful deployment, the script prints the deployed domain and token once, then reports service status for:

- AI Workspace domain and token
- OpenClaw
- QMD
- PostgreSQL
- Vault
- Workspace Portal / Console
- LiteLLM
- Agent CLI: `opencode`, `gemini`, `codex`, `claude`

Keep the token output private. It should not be copied into frontend source code or committed to Git.

## 7. Local macOS Validation

On macOS, the script defaults to local validation mode and starts the Portal at:

```text
http://127.0.0.1:17000
```

If validation fails because a port is already in use, stop the existing local service or run in a clean session before retrying.
