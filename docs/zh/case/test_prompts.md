[🇺🇸 English](../../../README.md) | [🇨🇳 中文](../../../README.zh.md)

# 测试提示词模板

本文档提供了用于测试 `setup-ai-workspace-all-in-one.sh` 的标准化提示词模板，可直接复制粘贴到终端执行。

---

## 1. 快速安装（一键部署）

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -
```

## 2. 带 API Key 安装

```bash
export DEEPSEEK_API_KEY="<your-deepseek-api-key>"
export NVIDIA_API_KEY="<your-nvidia-api-key>"
export OLLAMA_API_KEY="<your-ollama-api-key>"

curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -
```

## 3. 卸载（保留数据）

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -s -- uninstall
```

## 4. 彻底卸载（清除所有数据）

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -s -- uninstall --purge
```

## 5. 完整生命周期测试（卸载 → 重装）

```bash
# Step 1: 彻底卸载
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -s -- uninstall --purge

# Step 2: 设置 API Keys
export DEEPSEEK_API_KEY="<your-deepseek-api-key>"
export NVIDIA_API_KEY="<your-nvidia-api-key>"
export OLLAMA_API_KEY="<your-ollama-api-key>"

# Step 3: 重新安装
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -
```

## 6. 使用本地 Playbook 开发调试

```bash
export PLAYBOOK_DIR="/path/to/local/playbooks"
export DEEPSEEK_API_KEY="<your-deepseek-api-key>"
export NVIDIA_API_KEY="<your-nvidia-api-key>"
export OLLAMA_API_KEY="<your-ollama-api-key>"

bash /path/to/setup-ai-workspace-all-in-one.sh
```

> 设置 `PLAYBOOK_DIR` 后脚本会使用本地 Playbook 目录，而非从 Git 远端拉取，适合开发调试场景。

---

## 环境变量参考

| 变量名 | 用途 | 必填 |
|--------|------|:----:|
| `DEEPSEEK_API_KEY` | DeepSeek 模型 API 密钥 | 可选 |
| `NVIDIA_API_KEY` | NVIDIA NIM API 密钥 | 可选 |
| `OLLAMA_API_KEY` | Ollama 服务 API 密钥 | 可选 |
| `PLAYBOOK_DIR` | 本地 Playbook 目录路径（开发调试用） | 可选 |

---

## 支持平台

| 平台 | 状态 |
|------|:----:|
| macOS (Apple Silicon / Intel) | ✅ 已测试 |
| Debian 11/12 | ✅ 已测试 |
| Ubuntu 22.04/24.04 | ✅ 已测试 |
| 其他 Linux 发行版 | ⚠️ 未测试 |
