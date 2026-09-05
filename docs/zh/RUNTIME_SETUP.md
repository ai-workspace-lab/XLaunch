[🇺🇸 English](../../README.md) | [🇨🇳 中文](../../README.zh.md)

## 2. 部署执行模型（远程 exec / GitHub pull）

- `scripts/setup-ai-workspace-all-in-one.sh` 运行**在远程主机上**，全程 remote exec 模式。
- **不使用 rsync**；所需仓库由远程主机直接从 GitHub `pull`：
  - Playbooks：`https://github.com/ai-workspace-infra/playbooks.git`
  - Core Skills：`https://github.com/ai-workspace-lab/xworkspace-core-skills.git`
  - Console（脚本自身所在仓库）：`https://github.com/ai-workspace-lab/XLaunch.git`
  - QMD：`https://github.com/ai-workspace-services/qmd.git`
  - LiteLLM：`https://github.com/ai-workspace-services/litellm.git`
- 含义：**本地提交必须推送到上述 GitHub 仓库后，远程部署才能拉到改动**。

> ⚠️ 注意仓库地址不一致：playbooks 本地 `origin` 当前为 `git@github.com:x-evor/playbooks.git`，而部署权威源是 `ai-workspace-infra/playbooks`。实现阶段需将脚本中的 pull 源对齐到 `ai-workspace-infra/playbooks`，并把提交推送到该仓库。

### 2.1 环境变量接口契约（权威）

bootstrap 入口固定为 console 仓库的原始脚本，所有暴露/安全/可选桌面行为均通过 `bash -` 前的环境变量控制。

**标准安装**（默认安全本地工作区，仅需一个统一 token）：

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -
```

**全部参数（默认值与推荐用法）：**

| 变量 | 默认 | 推荐用法 |
|---|---|---|
| `TOKEN` | 生成或复用 | 为 Bridge / Portal / LiteLLM / OpenClaw / Vault 设置**统一**认证 token |
| `AI_WORKSPACE_SECURITY_LEVEL` | `standard` | 公网/半公网主机使用 `strict` |
| `XWORKMATE_BRIDGE_PUBLIC_ACCESS` | `true` | Bridge 为默认唯一公开服务；如需关闭对外访问可显式设 `false` |
| `XWORKMATE_BRIDGE_DOMAIN` | host-specific | 设置 Bridge 公网域名，例如 `acp-bridge.onwalk.net` |
| `XWORKSPACE_CONSOLE_PUBLIC_ACCESS` | `false` | 仅当 Portal 必须公开时开启；本地优先更安全 |
| `XWORKSPACE_CONSOLE_ENABLE_XRDP` | `false` | 仅当需要远程桌面访问时开启 |
| `GATEWAY_OPENCLAW_PUBLIC_ACCESS` | `false` | 除非 OpenClaw 必须直接暴露，保持 false |
| `VAULT_PUBLIC_ACCESS` | `false` | 常规部署保持 false |
| `LITELLM_API_CADDY_STRICT_WHITELIST` | `false` | strict 且 LiteLLM 经 Caddy 暴露时开启 |

**进阶安装示例：**

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

**目标主机（ACP Bridge）示例：**

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | \
  XWORKMATE_BRIDGE_DOMAIN=acp-bridge.onwalk.net \
  XWORKMATE_BRIDGE_PUBLIC_ACCESS=true \
  AI_WORKSPACE_SECURITY_LEVEL=strict \
  bash -
```

> 关键校准：`XWORKMATE_BRIDGE_PUBLIC_ACCESS` 默认 **`true`**——Bridge 是**默认唯一公开**的服务（域名经 `XWORKMATE_BRIDGE_DOMAIN` 自定义传入）；其余服务（Console/OpenClaw/Vault/QMD/Hermes/PG/LiteLLM）默认 `false`，保持 `127.0.0.1` 本地监听。如需关闭 Bridge 对外访问，显式设 `XWORKMATE_BRIDGE_PUBLIC_ACCESS=false`。`TOKEN` 输出务必私密保存——不得拷入前端源码或提交到 Git。

### 2.2 预期最终输出（部署摘要）

部署成功后，脚本将**一次性**打印部署域名与 token，随后报告各服务运行状态：

- AI Workspace 域名与 token（仅显示一次）
- OpenClaw
- QMD
- PostgreSQL
- Vault
- Workspace Portal / Console
- LiteLLM
- Hermes
- Agent CLI：opencode、gemini、codex、claude

### 2.3 本地 macOS 校验模式

在 macOS 上脚本默认进入**本地校验模式**，在 `http://127.0.0.1:17000` 启动 Portal。若因端口占用校验失败，先停止已有本地服务或在干净会话中重试。

---

## 7. 部署与验证

### 7.1 部署命令（在目标主机或对其有网络/SSH 访问的环境执行）

```bash
# 远程 exec：脚本在主机上自 GitHub pull 仓库并运行 ansible 到 localhost
# 采用 §2.1 权威环境变量契约（目标主机示例）
ssh root@acp-bridge.onwalk.net \
  'curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | \
   XWORKMATE_BRIDGE_DOMAIN=acp-bridge.onwalk.net \
   XWORKMATE_BRIDGE_PUBLIC_ACCESS=true \
   AI_WORKSPACE_SECURITY_LEVEL=strict \
   bash -'
```

### 7.2 验证清单

- [ ] 脚本结束输出统一摘要，且 Bridge 显示 `https://acp-bridge.onwalk.net`。
- [ ] `curl -I https://acp-bridge.onwalk.net` 可达；其余服务端口仅 `127.0.0.1` 监听。
- [ ] `systemctl --user is-active` 各服务为 `active`。
- [ ] `opencode/gemini/codex/claude --version` 均可执行。
- [ ] 凭据仅在摘要中出现一次。

---

## 附录 A. AI Workspace All-in-One Setup（bootstrap 使用指南）

> 面向最终用户的官方安装指南，已合并入本规划作为单一权威来源。
> 本附录相对上游 README 有两处校准：① `XWORKMATE_BRIDGE_PUBLIC_ACCESS` 默认 **`true`**（Bridge 为默认唯一公开服务）；② `acp-bridge.onwalk.net` 为 **host-specific 自定义参数**，经 `XWORKMATE_BRIDGE_DOMAIN` 传入。

这是从 `xworkspace-console` 仓库安装 AI Workspace Runtime 的推荐 bootstrap 入口。脚本以该仓库为公开入口，随后通过 AI Workspace playbooks 与各组件仓库准备运行时服务。

### A.1 标准安装

适用于默认安全的本地工作区，仅需一个生成或既有的统一 token：

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -
```

### A.2 进阶安装

在 `bash -` 前用环境变量自定义暴露面、安全级别与可选桌面功能：

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

### A.3 推荐参数

| 变量 | 默认 | 推荐用法 |
|---|---|---|
| `TOKEN` | 生成或复用 | 为 Bridge、Portal、LiteLLM、OpenClaw、Vault 设置一个统一认证 token |
| `AI_WORKSPACE_SECURITY_LEVEL` | `standard` | 公网/半公网主机使用 `strict` |
| `XWORKMATE_BRIDGE_PUBLIC_ACCESS` | `true` | Bridge 为默认唯一公开服务；需关闭对外访问时显式设 `false` |
| `XWORKMATE_BRIDGE_DOMAIN` | host-specific（自定义） | Bridge 公网域名，例如 `acp-bridge.onwalk.net` |
| `XWORKSPACE_CONSOLE_PUBLIC_ACCESS` | `false` | 仅当 Portal 必须公开时开启；本地优先更安全 |
| `GATEWAY_OPENCLAW_PUBLIC_ACCESS` | `false` | 除非 OpenClaw 必须直接暴露，保持 false |
| `VAULT_PUBLIC_ACCESS` | `false` | 常规部署保持 false |
| `LITELLM_API_CADDY_STRICT_WHITELIST` | `false` | strict 部署且 LiteLLM 经 Caddy 暴露时开启 |
| `XWORKSPACE_CONSOLE_ENABLE_XRDP` | `false` | 仅当需要远程桌面访问时开启 |

### A.4 目标主机示例（当前 ACP Bridge 主机）

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | \
  XWORKMATE_BRIDGE_DOMAIN=acp-bridge.onwalk.net \
  XWORKMATE_BRIDGE_PUBLIC_ACCESS=true \
  AI_WORKSPACE_SECURITY_LEVEL=strict \
  bash -
```

### A.5 预期最终输出

部署成功后，脚本**一次性**打印部署域名与 token，随后报告以下服务状态：

- AI Workspace 域名与 token
- OpenClaw
- QMD
- PostgreSQL
- Vault
- Workspace Portal / Console
- LiteLLM
- Agent CLI：opencode、gemini、codex、claude

> Token 输出务必私密保存，不得拷入前端源码或提交到 Git。

### A.6 本地 macOS 校验

在 macOS 上脚本默认进入本地校验模式，在 `http://127.0.0.1:17000` 启动 Portal。若因端口占用导致校验失败，先停止已有本地服务或在干净会话中重试。
