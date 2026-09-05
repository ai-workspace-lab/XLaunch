[🇺🇸 English](../../../README.md) | [🇨🇳 中文](../../../README.zh.md)

# Test Prompt Templates

This document provides standardized prompt templates used for testing `setup-ai-workspace-all-in-one.sh`, which can be directly copied and pasted into the terminal for execution.

---

## 1. Quick Installation (One-Click Deployment)

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -
```

## 2. Installation with API Keys

```bash
export DEEPSEEK_API_KEY="<your-deepseek-api-key>"
export NVIDIA_API_KEY="<your-nvidia-api-key>"
export OLLAMA_API_KEY="<your-ollama-api-key>"

curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -
```

## 3. Uninstall (Keep Data)

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -s -- uninstall
```

## 4. Complete Uninstall (Purge All Data)

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -s -- uninstall --purge
```

## 5. Full Lifecycle Test (Uninstall → Reinstall)

```bash
# Step 1: Complete Uninstall
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -s -- uninstall --purge

# Step 2: Set API Keys
export DEEPSEEK_API_KEY="<your-deepseek-api-key>"
export NVIDIA_API_KEY="<your-nvidia-api-key>"
export OLLAMA_API_KEY="<your-ollama-api-key>"

# Step 3: Reinstall
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -
```

## 6. Develop and Debug with Local Playbooks

```bash
export PLAYBOOK_DIR="/path/to/local/playbooks"
export DEEPSEEK_API_KEY="<your-deepseek-api-key>"
export NVIDIA_API_KEY="<your-nvidia-api-key>"
export OLLAMA_API_KEY="<your-ollama-api-key>"

bash /path/to/setup-ai-workspace-all-in-one.sh
```

> Setting `PLAYBOOK_DIR` makes the script use the local Playbook directory instead of pulling from the Git remote, which is suitable for development and debugging scenarios.

---

## Environment Variable Reference

| Variable Name | Purpose | Required |
|--------|------|:----:|
| `DEEPSEEK_API_KEY` | DeepSeek model API key | Optional |
| `NVIDIA_API_KEY` | NVIDIA NIM API key | Optional |
| `OLLAMA_API_KEY` | Ollama service API key | Optional |
| `PLAYBOOK_DIR` | Local Playbook directory path (for dev/debugging) | Optional |

---

## Supported Platforms

| Platform | Status |
|------|:----:|
| macOS (Apple Silicon / Intel) | ✅ Tested |
| Debian 11/12 | ✅ Tested |
| Ubuntu 22.04/24.04 | ✅ Tested |
| Other Linux Distributions | ⚠️ Untested |
