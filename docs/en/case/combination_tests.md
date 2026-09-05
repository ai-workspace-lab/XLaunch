[🇺🇸 English](../../../README.md) | [🇨🇳 中文](../../../README.zh.md)

# Combination Test Cases

This document defines the end-to-end combination test matrix for `setup-ai-workspace-all-in-one.sh`.

## Test Prerequisites

| Condition | Description |
|------|------|
| Supported Platforms | macOS (Darwin) / Debian / Ubuntu |
| Required Tools | `curl`, `bash` (`brew` is additionally required on macOS) |
| Network Requirements | Accessible to GitHub / npm registry |

---

## Test Matrix

### COMBO-001: Fresh Installation (No API Key)

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -
```

**Expected Result**: Installation completes, services like LiteLLM start with empty configurations, and the console is accessible.

---

### COMBO-002: Fresh Installation + API Key Injection

```bash
export DEEPSEEK_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export NVIDIA_API_KEY="nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export OLLAMA_API_KEY="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.xxxxxxxxxxxxxxxx"

curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -
```

**Expected Result**: Installation completes, API keys are automatically injected into the LiteLLM configuration, and the AI model gateway can proxy requests normally.

---

### COMBO-003: Uninstall (Keep Data)

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -s -- uninstall
```

**Expected Result**: All services are stopped, runtime files are removed, but user data and configurations are preserved.

---

### COMBO-004: Complete Uninstall (Purge All Data)

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -s -- uninstall --purge
```

**Expected Result**: All services are stopped, runtime files are removed, and all user data, configurations, and local databases are purged.

---

### COMBO-005: Reinstall after Uninstall (Full Lifecycle)

```bash
# Step 1: Complete Uninstall
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -s -- uninstall --purge

# Step 2: Reinstall with Keys
export DEEPSEEK_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export NVIDIA_API_KEY="nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export OLLAMA_API_KEY="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.xxxxxxxxxxxxxxxx"

curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -
```

**Expected Result**: Uninstall leaves no residue, everything runs normally after reinstallation, and API keys are injected correctly.

---

### COMBO-006: Idempotency Test (Repeated Installation)

```bash
# Run installation twice consecutively
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -
```

**Expected Result**: The second run should complete idempotently without errors, and the `changed` count should be close to 0.

---

## Platform Coverage Matrix

| Test ID | macOS (Darwin) | Debian | Ubuntu |
|----------|:--------------:|:------:|:------:|
| COMBO-001 | ✅ | ✅ | ✅ |
| COMBO-002 | ✅ | ✅ | ✅ |
| COMBO-003 | ✅ | ✅ | ✅ |
| COMBO-004 | ✅ | ✅ | ✅ |
| COMBO-005 | ✅ | ✅ | ✅ |
| COMBO-006 | ✅ | ✅ | ✅ |

> **Note**: Currently, only macOS / Debian / Ubuntu have been verified by actual tests; other Linux distributions are untested.
