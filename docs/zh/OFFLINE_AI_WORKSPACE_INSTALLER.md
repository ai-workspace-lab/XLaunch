[🇺🇸 English](../../README.md) | [🇨🇳 中文](../../README.zh.md)

# 离线 AI 工作区安装程序

`offline-package-ai-workspace-installer.yaml` 为 `setup-ai-workspace-all-in-one.sh` 构建了用于 tarball 资源包的离线打包程序。

## 支持的目标系统

- Debian: 13, 12, 11
- Ubuntu LTS: 26.04, 24.04, 22.04
- 架构: amd64, arm64

Ubuntu 20.04 不在默认支持矩阵中，因为标准支持已移至 Ubuntu Pro/ESM。

## 包内容

- `repos/playbooks`
- `repos/xworkspace-console`
- `repos/xworkspace-core-skills`
- `repos/xworkmate-bridge`
- `repos/qmd`
- `repos/litellm`
- `packages/apt`
- `packages/npm`
- `packages/npm-cache`
- `packages/pip`
- `packages/bin`
- `packages/images`
- `scripts/ai-workspace-offline-install.sh`
- `metadata/manifest.json`
- `metadata/*.commit`

## 运行时用法

在线引导脚本优先使用 `ai-workspace-lab/xworkspace-console` GitHub 版本发布中对应的离线包（当其可用时）：

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -
```

将 `AI_WORKSPACE_OFFLINE_MODE=off` 设置为强制使用传统的纯在线路径，或者将 `AI_WORKSPACE_OFFLINE_MODE=force` 设置为在无法准备匹配的离线包时失败。

默认包的获取源是：

```text
https://github.com/ai-workspace-lab/XLaunch/releases/download/<tag>/ai-workspace-all-in-one-offline-<distro>-<version>-<arch>.tar.gz
```

当 `AI_WORKSPACE_OFFLINE_RELEASE_TAG=latest` 时，引导脚本会向 GitHub 请求最新且实际包含匹配 tarball 资产的非草稿发布版本，因此如果 `releases/latest` 目标缺少该文件，它将跳过该发布版本。固定的发布版本标签仍可像以前一样工作。

对于私有镜像或固定发布，请使用：

```bash
AI_WORKSPACE_OFFLINE_PACKAGE_BASE_URL=https://mirror.example/offline-package/ai-workspace/offline-ai-workspace-<run_number> \
  bash scripts/setup-ai-workspace-all-in-one.sh

AI_WORKSPACE_OFFLINE_RELEASE_TAG=offline-ai-workspace-<run_number> \
  bash scripts/setup-ai-workspace-all-in-one.sh
```

要使用来自本地文件系统的特定、预先下载的离线部署包：

```bash
AI_WORKSPACE_OFFLINE_PACKAGE=/path/to/offline-package.tar.gz \
  bash scripts/setup-ai-workspace-all-in-one.sh
```

你也可以在主机上提取目标包并运行：

```bash
sudo ./scripts/ai-workspace-offline-install.sh
```

需要时，通过 `sudo env` 明确传递部署设置：

```bash
sudo env \
  XWORKMATE_BRIDGE_DOMAIN=acp-bridge.onwalk.net \
  AI_WORKSPACE_SECURITY_LEVEL=strict \
  ./scripts/ai-workspace-offline-install.sh
```

该脚本配置了一个本地 APT 存储库，安装了捆绑的二进制文件，在 Docker 可用时加载了打包的容器镜像，并运行了带有本地源目录的打包的 all-in-one 引导脚本。

## 部署时间记录

在 `acp-bridge.onwalk.net` 上的远程 `setup-ai-workspace-all-in-one.sh` 运行中，显示了以下可见的时间耗费点：

- OpenClaw npm 包/插件安装和依赖修复：约 68 秒
- Codex ACP Go 编译：约 37 秒
- Codex/OpenCode/Gemini/Hermes 的 ACP 虚拟主机配置：约 95 秒
- 控制台运行时 apt/package 设置和 ttyd：约 47 秒
- 智能体技能同步和质量检查：约 48 秒

被采样日志的前几分钟包括了 Node、apt 以及 AI 运行时的环境配置（在上述被捕获的时间窗口之前）。这些阶段被视为极其耗费资源的准备阶段，所以它们通过 APT 缓存、npm tarballs、pip wheels、本地 git 源码库、二进制文件和容器镜像 tarballs 被包含在了离线包中。
