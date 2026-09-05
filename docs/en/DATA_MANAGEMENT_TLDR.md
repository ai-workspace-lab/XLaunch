[🇺🇸 English](../../README.md) | [🇨🇳 中文](../../README.zh.md)

# AI Workspace Data Management TL;DR

This document provides a quick reference for managing the AI Workspace lifecycle, including backup, restoration, migration, and uninstallation using the one-line bootstrap script.

The `setup-ai-workspace-all-in-one.sh` script acts as a powerful orchestrator. You can pass special sub-commands at the end of the `bash` pipe using `--` or `-s`.

---

## 1. 备份 (Backup)

Create an AES-256 encrypted archive of your entire workspace (Vault keys, LiteLLM Database, QMD memory, Session states, and Plugin configurations).

**Default Backup:**
(Will backup to `~/ai_workspace_backup.tar.gz.enc` by default)
```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -s -- backup
```

**Custom Output Path:**
```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -s -- backup --output /data/my_cold_backup.tar.gz.enc
```

---

## 2. 恢复 (Restore)

Restore the AI Workspace from a cold backup archive. This will seamlessly inject Vault K/V secrets, PostgreSQL database states, and all configuration settings back into a working environment.

**Default Restore:**
(Looks for `~/ai_workspace_backup.tar.gz.enc` by default)
```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -s -- restore
```

**Custom Input Path:**
```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -s -- restore --input /data/my_cold_backup.tar.gz.enc
```

---

## 3. 跨主机迁移 (Migrate)

Seamlessly migrate and merge an AI workspace from a remote node into the local machine using secure SSH pathways (`rsync`) and `qmd sync`. This preserves the remote host non-destructively while bringing states, vector indices, and memory networks to localhost.

**Migrate from a Remote User/Host:**
```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -s -- migrate --source ubuntu@openclaw.svc.plus
```
*(Ensure you have passwordless SSH or an active agent loaded for `ubuntu@openclaw.svc.plus` before running this command).*

---

## 4. 卸载清理 (Uninstall)

Uninstall the AI Workspace components and configuration.

**Standard Uninstall:**
(Stops services and removes binaries but keeps data caches intact)
```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -s -- uninstall
```

**Purge Uninstall:**
(Stops services and destroys all databases, caches, configurations, and user states. Use with extreme caution!)
```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -s -- uninstall --purge
```

---

## Technical Notes
- **Security:** Backup archives are highly sensitive. They contain Vault exported secrets and LiteLLM database dumps. They are encrypted automatically via AES-256-CBC using the deployment symmetric key (`Vault Password` or `AI_WORKSPACE_AUTH_TOKEN`).
- **Dependencies:** The migration, backup, and restore routines automatically ensure dependencies (like PostgreSQL and Vault services) are fully running before executing their specific Ansible payloads.
