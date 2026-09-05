[🇺🇸 English](../../README.md) | [🇨🇳 中文](../../README.zh.md)

# AI 工作区数据管理 TL;DR

本文档提供了管理 AI 工作区生命周期的快速参考，包括使用单行引导脚本进行备份、恢复、迁移和卸载。

`setup-ai-workspace-all-in-one.sh` 脚本作为一个强大的编排器。你可以使用 `--` 或 `-s` 在 `bash` 管道的末尾传递特殊的子命令。

---

## 1. 备份 (Backup)

创建整个工作区（金库密钥、LiteLLM 数据库、QMD 记忆、会话状态和插件配置）的 AES-256 加密归档。

**默认备份:**
（默认将备份到 `~/ai_workspace_backup.tar.gz.enc`）
```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -s -- backup
```

**自定义输出路径:**
```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -s -- backup --output /data/my_cold_backup.tar.gz.enc
```

---

## 2. 恢复 (Restore)

从冷备份归档中恢复 AI 工作区。这将会无缝地把金库 K/V 机密、PostgreSQL 数据库状态以及所有配置设置重新注入到一个工作环境中。

**默认恢复:**
（默认查找 `~/ai_workspace_backup.tar.gz.enc`）
```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -s -- restore
```

**自定义输入路径:**
```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -s -- restore --input /data/my_cold_backup.tar.gz.enc
```

---

## 3. 跨主机迁移 (Migrate)

使用安全的 SSH 路径 (`rsync`) 和 `qmd sync`，将 AI 工作区从远程节点无缝迁移并合并到本地机器。这会在保持远程主机非破坏性状态的同时，将状态、向量索引和记忆网络带到本地主机。

**从远程用户/主机迁移:**
```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -s -- migrate --source ubuntu@openclaw.svc.plus
```
*(在运行此命令之前，请确保你拥有免密 SSH，或者已为 `ubuntu@openclaw.svc.plus` 加载了活动的代理)。*

---

## 4. 卸载清理 (Uninstall)

卸载 AI 工作区组件和配置。

**标准卸载:**
（停止服务并移除二进制文件，但保持数据缓存完整）
```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -s -- uninstall
```

**清除卸载:**
（停止服务并销毁所有数据库、缓存、配置和用户状态。请极度谨慎使用！）
```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -s -- uninstall --purge
```

---

## 技术说明
- **安全性:** 备份归档高度敏感。它们包含金库导出的机密和 LiteLLM 数据库转储。它们会通过使用部署的对称密钥（`Vault Password` 或 `AI_WORKSPACE_AUTH_TOKEN`）经 AES-256-CBC 自动加密。
- **依赖关系:** 迁移、备份和恢复例程会在执行其特定的 Ansible 负载之前，自动确保相关依赖（如 PostgreSQL 和 Vault 服务）已完全运行。
