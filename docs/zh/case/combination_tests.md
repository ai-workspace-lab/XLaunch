[🇺🇸 English](../../../README.md) | [🇨🇳 中文](../../../README.zh.md)

# 组合测试用例

本文档定义了 `setup-ai-workspace-all-in-one.sh` 的端到端组合测试矩阵。

## 测试前置条件

| 条件 | 说明 |
|------|------|
| 支持平台 | macOS (Darwin) / Debian / Ubuntu |
| 必备工具 | `curl`、`bash`（macOS 额外需要 `brew`） |
| 网络要求 | 可访问 GitHub / npm registry |

---

## 测试矩阵

### COMBO-001: 全新安装（无 API Key）

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -
```

**预期结果**: 安装完成，LiteLLM 等服务以空配置启动，控制台可访问。

---

### COMBO-002: 全新安装 + API Key 注入

```bash
export DEEPSEEK_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export NVIDIA_API_KEY="nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export OLLAMA_API_KEY="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.xxxxxxxxxxxxxxxx"

curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -
```

**预期结果**: 安装完成，API Key 自动注入 LiteLLM 配置，AI 模型网关可正常代理请求。

---

### COMBO-003: 卸载（保留数据）

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -s -- uninstall
```

**预期结果**: 停止所有服务，移除运行时文件，保留用户数据和配置。

---

### COMBO-004: 彻底卸载（清除所有数据）

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -s -- uninstall --purge
```

**预期结果**: 停止所有服务，移除运行时文件，清除所有用户数据、配置和本地数据库。

---

### COMBO-005: 卸载后重装（完整生命周期）

```bash
# Step 1: 彻底卸载
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -s -- uninstall --purge

# Step 2: 带 Key 重装
export DEEPSEEK_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export NVIDIA_API_KEY="nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export OLLAMA_API_KEY="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.xxxxxxxxxxxxxxxx"

curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -
```

**预期结果**: 卸载干净无残留，重装后一切正常运行，API Key 正确注入。

---

### COMBO-006: 幂等性测试（重复安装）

```bash
# 连续执行两次安装
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -
```

**预期结果**: 第二次运行应以幂等方式完成，不产生错误，`changed` 计数应接近 0。

---

## 平台覆盖矩阵

| 测试编号 | macOS (Darwin) | Debian | Ubuntu |
|----------|:--------------:|:------:|:------:|
| COMBO-001 | ✅ | ✅ | ✅ |
| COMBO-002 | ✅ | ✅ | ✅ |
| COMBO-003 | ✅ | ✅ | ✅ |
| COMBO-004 | ✅ | ✅ | ✅ |
| COMBO-005 | ✅ | ✅ | ✅ |
| COMBO-006 | ✅ | ✅ | ✅ |

> **注意**: 目前仅 macOS / Debian / Ubuntu 经过实际测试验证，其他 Linux 发行版未测试。
