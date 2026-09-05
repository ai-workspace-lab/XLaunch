[🇺🇸 English](../../README.md) | [🇨🇳 中文](../../README.zh.md)

# Offline AI Workspace Installer

`offline-package-ai-workspace-installer.yaml` builds tarball resource packs for
`setup-ai-workspace-all-in-one.sh`.

## Supported Targets

- Debian: 13, 12, 11
- Ubuntu LTS: 26.04, 24.04, 22.04
- Architectures: amd64, arm64

Ubuntu 20.04 is not in the default matrix because standard support has moved to
Ubuntu Pro/ESM.

## Package Contents

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

## Runtime Usage

The online bootstrap prefers the matching offline package from the
`ai-workspace-lab/xworkspace-console` GitHub releases when it is available:

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -
```

Set `AI_WORKSPACE_OFFLINE_MODE=off` to force the legacy online-only path, or
`AI_WORKSPACE_OFFLINE_MODE=force` to fail when no matching offline package can be
prepared.

The default package source is:

```text
https://github.com/ai-workspace-lab/XLaunch/releases/download/<tag>/ai-workspace-all-in-one-offline-<distro>-<version>-<arch>.tar.gz
```

When `AI_WORKSPACE_OFFLINE_RELEASE_TAG=latest`, the bootstrap asks GitHub for
the newest non-draft release that actually contains the matching tarball asset,
so it will skip a `releases/latest` target if that release is missing the file.
Pinned release tags still work as before.

For private mirrors or pinned releases, use:

```bash
AI_WORKSPACE_OFFLINE_PACKAGE_BASE_URL=https://mirror.example/offline-package/ai-workspace/offline-ai-workspace-<run_number> \
  bash scripts/setup-ai-workspace-all-in-one.sh

AI_WORKSPACE_OFFLINE_RELEASE_TAG=offline-ai-workspace-<run_number> \
  bash scripts/setup-ai-workspace-all-in-one.sh
```

To use a specific, pre-downloaded offline deployment package from the local file system:

```bash
AI_WORKSPACE_OFFLINE_PACKAGE=/path/to/offline-package.tar.gz \
  bash scripts/setup-ai-workspace-all-in-one.sh
```

You can also extract the target package on the host and run:

```bash
sudo ./scripts/ai-workspace-offline-install.sh
```

Pass deployment settings explicitly through `sudo env` when needed:

```bash
sudo env \
  XWORKMATE_BRIDGE_DOMAIN=acp-bridge.onwalk.net \
  AI_WORKSPACE_SECURITY_LEVEL=strict \
  ./scripts/ai-workspace-offline-install.sh
```

The script configures a local APT repository, installs bundled binaries, loads
packaged container images when Docker is available, and runs the packaged
all-in-one bootstrap with local source directories.

## Deployment Timing Notes

A remote `setup-ai-workspace-all-in-one.sh` run on `acp-bridge.onwalk.net`
showed these visible timing hotspots:

- OpenClaw npm package/plugin install and dependency repair: about 68 seconds
- Codex ACP Go build: about 37 seconds
- ACP vhosts for Codex/OpenCode/Gemini/Hermes: about 95 seconds
- Console runtime apt/package setup and ttyd: about 47 seconds
- Agent skill sync and quality checks: about 48 seconds

The first several minutes of the sampled log included Node, apt, and AI runtime
setup before the captured timing window. Those are treated as resource-heavy
setup phases and are included in the offline package through APT caches, npm
tarballs, pip wheels, local git sources, binaries, and container image tarballs.
