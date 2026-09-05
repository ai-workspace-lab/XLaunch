[🇺🇸 English](../../README.md) | [🇨🇳 中文](../../README.zh.md)

# AI Workspace 一站式安装

这是从 `xworkspace-console` 仓库安装 AI Workspace Runtime 的推荐启动程序入口。

启动脚本以本仓库为公开入口点，随后通过 AI Workspace playbooks 和组件仓库准备运行时服务。

## 1. 标准安装

当需要默认安全的本地工作区且仅需要生成或现有的统一 token 时使用此方式。

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -
```

## 2. 进阶安装

在 `bash -` 之前使用环境变量来自定义公开访问、安全级别和可选的桌面功能。

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

> 子命令作为 `bash -` 的位置参数传入：`... | bash -s -- uninstall`。

## 3. 子命令

作为第一个位置参数传入（`... | bash -s -- <子命令>`）。

| 子命令 | 作用 |
| --- | --- |
| `uninstall` | 停止并移除所有 AI Workspace 应用/服务（macOS launchd；Linux systemd 单元 + docker 容器）。`$HOME` 下的配置、token、数据**保留**。 |
| `uninstall --purge` | 同上，并**删除**配置/状态/token/缓存目录（`~/.config/xworkspace`、`~/.local/state/xworkspace`、`~/.openclaw`、`~/.ai_workspace_auth_token`、`/tmp/ai-workspace-deploy`；Linux 有 root 时再加 `/opt/ai-workspace`、`/etc/ai-workspace`）。执行前打印清单，逐项报告 已删/不存在。 |

## 4. 可选参数（环境变量）

在 `bash -` 之前以环境变量传入。下表为脚本支持的完整可选项，按用途分类。

### 4.1 公网暴露与安全

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `AI_WORKSPACE_SECURITY_LEVEL` | `standard` | 公网/半公网主机用 `strict`（收紧公开 Web API）。 |
| `XWORKMATE_BRIDGE_PUBLIC_ACCESS` | `false` | Bridge 经 Caddy 对外（公网 IP 主机的典型唯一对外服务）。 |
| `XWORKSPACE_CONSOLE_PUBLIC_ACCESS` | `false` | Portal/Console 对外。默认本地only（`127.0.0.1:17000`）更安全。 |
| `GATEWAY_OPENCLAW_PUBLIC_ACCESS` | `false` | OpenClaw 网关对外。 |
| `VAULT_PUBLIC_ACCESS` | `false` | Vault 对外。常规部署保持 false。 |
| `LITELLM_API_CADDY_STRICT_WHITELIST` | `false` | strict 且 LiteLLM 经 Caddy 暴露时，限制公开网关路径白名单。 |
| `LITELLM_CADDY_CONFIG_ENABLED` | 视部署 | 是否为 LiteLLM 下发 Caddy 站点配置。 |
| `XWORKSPACE_CONSOLE_ENABLE_XRDP` | `false` | 安装 XRDP 远程桌面（仅需要图形远程时）。 |
| `XWORKMATE_BRIDGE_DOMAIN` | 主机相关 | 对外 Bridge 域名，例如 `acp-bridge.onwalk.net`。 |

### 4.2 统一认证 Token

按以下顺序取第一个非空值作为统一 token（传给 Bridge / LiteLLM / OpenClaw / Vault）：
`AI_WORKSPACE_AUTH_TOKEN` → `XWORKSPACE_CONSOLE_AUTH_TOKEN` → `XWORKMATE_BRIDGE_AUTH_TOKEN` → `BRIDGE_AUTH_TOKEN` → `INTERNAL_SERVICE_TOKEN` → `DEPLOY_TOKEN`。
均未设则**自动生成**并存入 `AI_WORKSPACE_AUTH_TOKEN_FILE`（默认 `~/.ai_workspace_auth_token`）。Vault root token 可用 `VAULT_SERVER_ROOT_ACCESS_TOKEN` 单独指定。

### 4.3 运行时形态

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `AI_WORKSPACE_RUNTIME_MODES` | `docker,systemd` | 运行时形态组合；`docker` 与 `k3s` 互斥。 |
| `POSTGRESQL_DEPLOY_MODE` | `compose` | 部署模式：`compose`（Docker 容器）、`native`（Linux apt/systemd，macOS Homebrew）、`external`（外部已有数据库，跳过本地安装启动）。若 `VAULT_DEPLOY_MODE=external` 或提供了 `POSTGRESQL_DATABASE_URL`，默认自动设为 `external`。 |
| `POSTGRESQL_DATABASE_URL` | 无 | 外部 PostgreSQL 数据库 URL 链接（例：`postgres://account:<masked_token>@127.0.0.1:15432/account?sslmode=disable`），设为此项时会自动解析其中的 Host/Port/User/Password 并注入部署环境。 |
| `POSTGRESQL_ADMIN_USER` | `postgres` | 外部 PostgreSQL 的超级管理员用户名。在 `external` 部署模式下用以执行建库建用户操作。若未显式指定，会自动从 `POSTGRESQL_DATABASE_URL` 中解析，但请注意，若 URL 为普通用户，建议显式声明此管理员账号以确保建库权限。 |
| `POSTGRESQL_ADMIN_PASSWORD` | 无 | 外部 PostgreSQL 超级管理员的密码。若未显式设置，将尝试从 `POSTGRESQL_DATABASE_URL` 解析或读取本地密码影子文件 `/root/.ai_workspace_postgres_password`（Debian/Ubuntu 部署时）。 |

### 4.4 离线包（加速 / 气隙）

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `AI_WORKSPACE_OFFLINE_MODE` | `auto` | `auto`（尝试离线、失败回退在线）/ `force`（强制离线）/ `off`。 |
| `AI_WORKSPACE_OFFLINE_PACKAGE` | 无 | 本地离线包文件/目录或 URL。 |
| `AI_WORKSPACE_OFFLINE_PACKAGE_URL` | 无 | 直链 tar URL。 |
| `AI_WORKSPACE_OFFLINE_PACKAGE_BASE_URL` | 无 | 镜像目录（其下含目标 tar）；为空则跳过镜像。 |
| `AI_WORKSPACE_OFFLINE_RELEASE_TAG` | `latest` | GitHub Release tag 或 `latest`。 |
| `AI_WORKSPACE_OFFLINE_REPO` | `ai-workspace-lab/xworkspace-console` | 离线包所在仓库。 |
| `AI_WORKSPACE_OFFLINE_AUTO_DOWNLOAD` | `true` | auto 模式下从 GitHub Release 自动取匹配包（含分片重组）。 |
| `AI_WORKSPACE_OFFLINE_WORK_DIR` | `/tmp/ai-workspace-offline` | 离线包解压工作目录。 |

> 取数优先级：`OFFLINE_PACKAGE` → `OFFLINE_PACKAGE_URL` → `OFFLINE_PACKAGE_BASE_URL/<file>` → 否则 `AUTO_DOWNLOAD` 走 GitHub Release。失败则按系统回退在线（apt/yum 或 macOS homebrew + git clone + 在线拉 runtime）。

### 4.5 性能 / 并发 / 锁

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `AI_WORKSPACE_PREFETCH_ENABLED` | `true` | 预取仓库/组件。 |
| `AI_WORKSPACE_PREFETCH_DIR` | `/var/tmp/ai-workspace-prefetch` | 预取目录。 |
| `AI_WORKSPACE_MAX_PARALLEL_JOBS` | `auto` | 并发上限（不超过 2× 在线 CPU 核数）。 |
| `AI_WORKSPACE_SPLIT_PHASES` | `true` | 分阶段执行。 |
| `AI_WORKSPACE_RUNTIME_PREBUILD_ENABLED` | `false` | 预构建 runtime。 |
| `AI_WORKSPACE_DEPLOYMENT_LOCK_TIMEOUT` | `1800` | 部署互斥锁等待秒数。 |
| `AI_WORKSPACE_APT_LOCK_TIMEOUT` | `900` | 等待 dpkg/apt 锁秒数（避开 cloud-init/unattended-upgrades 抢锁）。 |

### 4.6 源/版本覆盖（开发与离线定制）

| 变量 | 说明 |
| --- | --- |
| `PLAYBOOK_DIR` | 本地 playbooks 检出目录（macOS 验证常用）。 |
| `XWORKSPACE_CONSOLE_DIR` | 本地 xworkspace-console 检出（macOS）。 |
| `XWORKSPACE_CONSOLE_SOURCE_REPO` / `XWORKSPACE_CONSOLE_SOURCE_VERSION` | Linux console playbook 的 Git 源/版本。 |
| `XWORKSPACE_CONSOLE_RUNTIME_ARCHIVE` / `QMD_RUNTIME_ARCHIVE` | 预编译 runtime tar 路径（离线）。 |
| `LITELLM_PACKAGE_SPEC` / `AI_WORKSPACE_PREBUILT_COMPONENTS_REQUIRED` | LiteLLM 包规格 / 强制要求预编译组件。 |
| `OPENCLAW_MULTI_SESSION_PLUGIN_PACKAGE_SPEC` / `OPENCLAW_MULTI_SESSION_PLUGIN_DIR` | OpenClaw 多会话插件源 / 本地检出（macOS link 安装）。 |
| `BRANCH` | 部署使用的 playbooks 仓库的 Git 分支、Tag 或 commit hash。在线安装时支持通过在部署链接路径后缀中指定（例：`curl -sfL https://install.svc.plus/ai-workspace/v1.1.5 | bash`），或显式指定本变量。 |

## 5. 目标主机示例

对于当前 ACP Bridge 主机：

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | \
  XWORKMATE_BRIDGE_DOMAIN=acp-bridge.onwalk.net \
  XWORKMATE_BRIDGE_PUBLIC_ACCESS=true \
  AI_WORKSPACE_SECURITY_LEVEL=strict \
  bash -
```

## 6. 预期最终输出

部署成功后，脚本会一次性打印部署的域名与 token，然后报告以下服务状态：

- AI Workspace 域名与 token
- OpenClaw
- QMD
- PostgreSQL
- Vault
- Workspace Portal / Console
- LiteLLM
- Agent CLI：`opencode`、`gemini`、`codex`、`claude`

请妥善保管 token。它不应该被复制到前端源代码或提交到 Git 中。

## 7. 本地 macOS 验证

在 macOS 上，脚本默认进入本地验证模式并在以下地址启动 Portal：

```text
http://127.0.0.1:17000
```

如果因为端口已被占用导致验证失败，请先停止现有的本地服务或在干净的会话中重试。
