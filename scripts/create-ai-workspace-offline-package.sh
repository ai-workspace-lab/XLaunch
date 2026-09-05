#!/usr/bin/env bash
set -euo pipefail

DISTRO_ID="${DISTRO_ID:?DISTRO_ID is required, e.g. debian or ubuntu}"
DISTRO_VERSION="${DISTRO_VERSION:?DISTRO_VERSION is required, e.g. 13 or 24.04}"
ARCH="${ARCH:-amd64}"
PACKAGE_VERSION="${PACKAGE_VERSION:-$(date -u +%Y%m%d%H%M%S)}"

PLAYBOOKS_REPO="${PLAYBOOKS_REPO:-https://github.com/ai-workspace-infra/playbooks.git}"
PLAYBOOKS_REF="${PLAYBOOKS_REF:-main}"
CONSOLE_REPO="${CONSOLE_REPO:-https://github.com/ai-workspace-lab/XLaunch.git}"
CONSOLE_REF="${CONSOLE_REF:-main}"
CORE_SKILLS_REPO="${CORE_SKILLS_REPO:-https://github.com/ai-workspace-lab/xworkspace-core-skills.git}"
CORE_SKILLS_REF="${CORE_SKILLS_REF:-main}"
CONSOLE_RUNTIME_RELEASE_REPO="${CONSOLE_RUNTIME_RELEASE_REPO:-ai-workspace-lab/XLaunch}"
CONSOLE_RUNTIME_RELEASE_TAG="${CONSOLE_RUNTIME_RELEASE_TAG:-latest-runtime}"
BRIDGE_RUNTIME_RELEASE_REPO="${BRIDGE_RUNTIME_RELEASE_REPO:-ai-workspace-lab/xworkmate-bridge}"
BRIDGE_RUNTIME_RELEASE_TAG="${BRIDGE_RUNTIME_RELEASE_TAG:-latest-runtime}"
QMD_RUNTIME_RELEASE_REPO="${QMD_RUNTIME_RELEASE_REPO:-ai-workspace-services/qmd}"
QMD_RUNTIME_RELEASE_TAG="${QMD_RUNTIME_RELEASE_TAG:-latest-runtime}"
LITELLM_RUNTIME_RELEASE_REPO="${LITELLM_RUNTIME_RELEASE_REPO:-ai-workspace-services/litellm}"
LITELLM_RUNTIME_RELEASE_TAG="${LITELLM_RUNTIME_RELEASE_TAG:-latest-runtime}"

NODEJS_MAJOR_VERSIONS="${NODEJS_MAJOR_VERSIONS:-22 24}"
NODEJS_22_VERSION="${NODEJS_22_VERSION:-22.22.3}"
NODEJS_24_VERSION="${NODEJS_24_VERSION:-24.16.0}"
VAULT_VERSION="${VAULT_VERSION:-1.21.4}"
TTYD_VERSION="${TTYD_VERSION:-latest}"
POSTGRES_IMAGE="${POSTGRES_IMAGE:-postgres:17.7}"
OPENCLAW_VERSION="${OPENCLAW_VERSION:-2026.6.6}"
PLAYWRIGHT_VERSION="${PLAYWRIGHT_VERSION:-1.60.0}"
GOOGLE_CHROME_VERSION="${GOOGLE_CHROME_VERSION:-149.0.7827.114-1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

case "${ARCH}" in
  x86_64|amd64) ARCH=amd64 ;;
  aarch64|arm64) ARCH=arm64 ;;
  *) echo "Unsupported ARCH: ${ARCH}" >&2; exit 1 ;;
esac

case "${DISTRO_ID}:${DISTRO_VERSION}" in
  debian:11|debian:12|debian:13|ubuntu:22.04|ubuntu:24.04|ubuntu:26.04) ;;
  *)
    echo "Unsupported target: ${DISTRO_ID}:${DISTRO_VERSION}" >&2
    echo "Supported: debian 11/12/13 and ubuntu 22.04/24.04/26.04" >&2
    exit 1
    ;;
esac

WORKDIR="${WORKDIR:-${REPO_ROOT}/ai-workspace-all-in-one-offline-${DISTRO_ID}-${DISTRO_VERSION}-${ARCH}}"
OUT="${OUT:-${REPO_ROOT}/ai-workspace-all-in-one-offline-${DISTRO_ID}-${DISTRO_VERSION}-${ARCH}.tar.gz}"

image_for_target() {
  case "${DISTRO_ID}" in
    debian) echo "debian:${DISTRO_VERSION}" ;;
    ubuntu) echo "ubuntu:${DISTRO_VERSION}" ;;
  esac
}

safe_name() {
  tr '/:@+' '----' <<<"$1"
}

clone_repo() {
  local url=$1
  local ref=$2
  local dest=$3

  git clone --depth 1 --branch "${ref}" "${url}" "${dest}" 2>/dev/null || {
    git clone --depth 1 "${url}" "${dest}"
    git -C "${dest}" fetch --depth 1 origin "${ref}"
    git -C "${dest}" checkout FETCH_HEAD
  }
  git -C "${dest}" rev-parse HEAD
}

github_api() {
  local path=$1
  local headers=(-H "Accept: application/vnd.github+json")
  if [ -n "${GH_TOKEN:-${GITHUB_TOKEN:-}}" ]; then
    headers+=(-H "Authorization: Bearer ${GH_TOKEN:-${GITHUB_TOKEN}}")
  fi
  curl -fsSL --retry 5 --retry-all-errors "${headers[@]}" "https://api.github.com${path}"
}

resolve_runtime_tag() {
  local repo=$1
  local requested=$2
  local attempt tag=""
  if [ "${requested}" != "latest-runtime" ]; then
    printf '%s\n' "${requested}"
    return
  fi
  for attempt in $(seq 1 40); do
    tag="$(
      github_api "/repos/${repo}/releases?per_page=100" |
        jq -r '[.[] | select(.draft == false and (.tag_name | startswith("runtime-")))] | first | .tag_name // empty'
    )"
    if [ -n "${tag}" ]; then
      printf '%s\n' "${tag}"
      return
    fi
    echo "Waiting for the first runtime release from ${repo} (${attempt}/40)..." >&2
    sleep 30
  done
}

download_release_asset() {
  local repo=$1 requested_tag=$2 asset=$3 destination=$4 metadata_name=$5
  local tag release_json asset_url checksums_url expected actual
  tag="$(resolve_runtime_tag "${repo}" "${requested_tag}")"
  [ -n "${tag}" ] || { echo "No runtime release found for ${repo}" >&2; exit 1; }
  release_json="$(github_api "/repos/${repo}/releases/tags/${tag}")"
  asset_url="$(jq -r --arg name "${asset}" '.assets[] | select(.name == $name) | .browser_download_url' <<<"${release_json}")"
  checksums_url="$(jq -r '.assets[] | select(.name == "SHA256SUMS") | .browser_download_url' <<<"${release_json}")"
  [ -n "${asset_url}" ] && [ "${asset_url}" != "null" ] ||
    { echo "Release asset ${asset} is missing from ${repo}@${tag}" >&2; exit 1; }
  [ -n "${checksums_url}" ] && [ "${checksums_url}" != "null" ] ||
    { echo "SHA256SUMS is missing from ${repo}@${tag}" >&2; exit 1; }

  mkdir -p "$(dirname "${destination}")" "${WORKDIR}/metadata/components"
  curl -fsSL --retry 5 --retry-all-errors "${asset_url}" -o "${destination}"
  curl -fsSL --retry 5 --retry-all-errors "${checksums_url}" \
    -o "${WORKDIR}/metadata/components/${metadata_name}.SHA256SUMS"
  expected="$(awk -v file="${asset}" '$2 == file || $2 == "*" file { print $1; exit }' \
    "${WORKDIR}/metadata/components/${metadata_name}.SHA256SUMS")"
  actual="$(sha256sum "${destination}" | awk '{print $1}')"
  [ -n "${expected}" ] && [ "${expected}" = "${actual}" ] ||
    { echo "Checksum mismatch or missing checksum for ${repo}@${tag}/${asset}" >&2; exit 1; }
  printf '%s\n' "${tag}" > "${WORKDIR}/metadata/components/${metadata_name}.tag"
  printf '%s\n' "${actual}" > "${WORKDIR}/metadata/components/${metadata_name}.sha256"
}

download_component_releases() {
  local component_dir="${WORKDIR}/packages/components"
  local bridge_tmp="${WORKDIR}/.bridge-runtime"
  local litellm_tmp="${WORKDIR}/.litellm-runtime"
  local console_asset="xworkspace-console-runtime-linux-${ARCH}.tar.gz"
  local bridge_asset="xworkmate-bridge-linux-${ARCH}.tar.gz"
  local qmd_asset="qmd-runtime-linux-${ARCH}.tar.gz"
  local litellm_asset="litellm-runtime-${DISTRO_ID}-${DISTRO_VERSION}-${ARCH}.tar.gz"

  mkdir -p "${component_dir}" "${bridge_tmp}" "${litellm_tmp}" "${WORKDIR}/packages/bin"
  download_release_asset "${CONSOLE_RUNTIME_RELEASE_REPO}" "${CONSOLE_RUNTIME_RELEASE_TAG}" \
    "${console_asset}" "${component_dir}/${console_asset}" xworkspace-console
  download_release_asset "${BRIDGE_RUNTIME_RELEASE_REPO}" "${BRIDGE_RUNTIME_RELEASE_TAG}" \
    "${bridge_asset}" "${component_dir}/${bridge_asset}" xworkmate-bridge
  download_release_asset "${QMD_RUNTIME_RELEASE_REPO}" "${QMD_RUNTIME_RELEASE_TAG}" \
    "${qmd_asset}" "${component_dir}/${qmd_asset}" qmd
  download_release_asset "${LITELLM_RUNTIME_RELEASE_REPO}" "${LITELLM_RUNTIME_RELEASE_TAG}" \
    "${litellm_asset}" "${component_dir}/${litellm_asset}" litellm

  tar -xzf "${component_dir}/${bridge_asset}" -C "${bridge_tmp}"
  install -m 0755 "${bridge_tmp}/xworkmate-bridge/bin/xworkmate-go-core" \
    "${WORKDIR}/packages/bin/xworkmate-go-core.${ARCH}"
  tar -xzf "${component_dir}/${litellm_asset}" -C "${litellm_tmp}"
  cp -a "${litellm_tmp}/litellm-runtime/packages/pip" "${WORKDIR}/packages/"
  if [ -d "${litellm_tmp}/litellm-runtime/packages/python" ]; then
    cp -a "${litellm_tmp}/litellm-runtime/packages/python" "${WORKDIR}/packages/"
  fi
  cp "${litellm_tmp}/litellm-runtime/metadata/runtime.env" \
    "${WORKDIR}/metadata/litellm-runtime.env"
}

download_apt_packages() {
  local image=$1
  local platform="linux/${ARCH}"
  local apt_dir="${WORKDIR}/packages/apt"
  local apt_lists="${WORKDIR}/metadata/apt"
  mkdir -p "${apt_dir}" "${apt_lists}"

  docker run --rm --platform "${platform}" \
    -e DISTRO_ID="${DISTRO_ID}" \
    -e DISTRO_VERSION="${DISTRO_VERSION}" \
    -e NODEJS_MAJOR_VERSIONS="${NODEJS_MAJOR_VERSIONS}" \
    -e NODEJS_22_VERSION="${NODEJS_22_VERSION}" \
    -e NODEJS_24_VERSION="${NODEJS_24_VERSION}" \
    -e GOOGLE_CHROME_VERSION="${GOOGLE_CHROME_VERSION}" \
    -v "${apt_dir}:/offline-apt" \
    -v "${apt_lists}:/offline-meta" \
    "${image}" \
    bash -lc "$(cat <<'CONTAINER'
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

retry_command() {
  local attempt
  for attempt in 1 2 3 4 5; do
    if "$@"; then
      return 0
    fi
    if [ "${attempt}" -lt 5 ]; then
      echo "Command failed (attempt ${attempt}/5), retrying: $*" >&2
      sleep $((attempt * 3))
    fi
  done
  return 1
}

cat > /etc/apt/apt.conf.d/80-ai-workspace-retries <<'EOF'
Acquire::Retries "5";
Acquire::http::Timeout "30";
Acquire::https::Timeout "30";
EOF
retry_command apt-get update -y
retry_command apt-get install -y ca-certificates curl gnupg dpkg-dev apt-transport-https

install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key -o /etc/apt/keyrings/nodesource.asc
for major in ${NODEJS_MAJOR_VERSIONS}; do
  echo "deb [signed-by=/etc/apt/keyrings/nodesource.asc] https://deb.nodesource.com/node_${major}.x nodistro main" \
    > "/etc/apt/sources.list.d/nodesource-node${major}.list"
done
curl -fsSL https://dl.cloudsmith.io/public/caddy/stable/gpg.key -o /etc/apt/keyrings/caddy-stable.asc
echo "deb [signed-by=/etc/apt/keyrings/caddy-stable.asc] https://dl.cloudsmith.io/public/caddy/stable/deb/debian any-version main" \
  > /etc/apt/sources.list.d/caddy-stable.list
if [ "$(dpkg --print-architecture)" = "amd64" ]; then
  curl -fsSL https://dl.google.com/linux/linux_signing_key.pub \
    | gpg --dearmor -o /etc/apt/keyrings/google-linux-signing-key.gpg
  echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-linux-signing-key.gpg] https://dl.google.com/linux/chrome/deb/ stable main" \
    > /etc/apt/sources.list.d/google-chrome.list
fi
curl -fsSL https://dl.yarnpkg.com/debian/pubkey.gpg -o /etc/apt/keyrings/yarn.asc
echo "deb [signed-by=/etc/apt/keyrings/yarn.asc] https://dl.yarnpkg.com/debian/ stable main" \
  > /etc/apt/sources.list.d/yarn.list
if curl -fsSL https://download.docker.com/linux/${DISTRO_ID}/gpg -o /etc/apt/keyrings/docker.asc; then
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/${DISTRO_ID} ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
fi

retry_command apt-get update -y

required_packages=(
  ansible git curl ca-certificates gnupg jq rsync unzip wget xdg-utils
  caddy xfce4 python3 python3-pip python3-venv python3-dev python3-setuptools
  build-essential pkg-config libpq-dev python-is-python3 pandoc nodejs yarn golang-go
  texlive-xetex texlive-latex-extra texlive-fonts-recommended
  texlive-lang-chinese latexmk fonts-noto-cjk
  fonts-noto-cjk-extra fonts-wqy-zenhei fonts-wqy-microhei
)

resolve_required_package() {
  local candidate
  for candidate in "$@"; do
    if apt-cache show "${candidate}" 2>/dev/null | awk '
      BEGIN { found = 0 }
      /^Package: / { package = $2 }
      /^Version: / { found = 1 }
      END { exit found ? 0 : 1 }
    '; then
      printf '%s\n' "${candidate}"
      return
    fi
  done
  echo "Required APT package is unavailable for this target: $*" >&2
  exit 1
}

case "$(dpkg --print-architecture)" in
  amd64)
    if apt-cache madison google-chrome-stable | awk '{print $3}' | grep -Fxq "${GOOGLE_CHROME_VERSION}"; then
      chrome_package="google-chrome-stable=${GOOGLE_CHROME_VERSION}"
    elif apt-cache show google-chrome-stable >/dev/null 2>&1; then
      echo "Required Google Chrome version is unavailable: ${GOOGLE_CHROME_VERSION}; using the repository candidate instead." >&2
      chrome_package="google-chrome-stable"
    else
      echo "Required Google Chrome package is unavailable for this target." >&2
      exit 1
    fi
    ;;
  arm64)
    browser_dependency_groups=(
      "libasound2 libasound2t64"
      "libatk-bridge2.0-0 libatk-bridge2.0-0t64"
      "libatk1.0-0 libatk1.0-0t64"
      "libatspi2.0-0 libatspi2.0-0t64"
      "libcairo2"
      "libcups2 libcups2t64"
      "libdbus-1-3"
      "libdrm2"
      "libgbm1"
      "libglib2.0-0 libglib2.0-0t64"
      "libnspr4"
      "libnss3"
      "libpango-1.0-0"
      "libx11-6"
      "libxcb1"
      "libxcomposite1"
      "libxdamage1"
      "libxext6"
      "libxfixes3"
      "libxkbcommon0"
      "libxrandr2"
    )
    : > /offline-meta/browser-deb-packages.txt
    for dependency_group in "${browser_dependency_groups[@]}"; do
      read -r -a dependency_candidates <<<"${dependency_group}"
      resolved_dependency="$(resolve_required_package "${dependency_candidates[@]}")"
      required_packages+=("${resolved_dependency}")
      printf '%s\n' "${resolved_dependency}" >> /offline-meta/browser-deb-packages.txt
    done
    ;;
esac
packages=()

for package in "${required_packages[@]}"; do
  if ! apt-cache show "${package}" >/dev/null 2>&1; then
    echo "Required APT package is unavailable for this target: ${package}" >&2
    exit 1
  fi
  packages+=("${package}")
done

if [ "$(dpkg --print-architecture)" = "amd64" ]; then
  packages+=("${chrome_package}")
fi

if apt-cache show docker-ce >/dev/null 2>&1; then
  packages+=(docker-ce docker-ce-cli containerd.io)
  for package in docker-buildx-plugin docker-compose-plugin; do
    if apt-cache show "${package}" >/dev/null 2>&1; then
      packages+=("${package}")
    fi
  done
elif apt-cache show docker.io >/dev/null 2>&1; then
  packages+=(docker.io)
  if apt-cache show docker-compose-plugin >/dev/null 2>&1; then
    packages+=(docker-compose-plugin)
  fi
fi

retry_command apt-get install --download-only -y --no-install-recommends "${packages[@]}"
retry_command apt-get download "nodejs=${NODEJS_22_VERSION}-1nodesource1"
retry_command apt-get download "nodejs=${NODEJS_24_VERSION}-1nodesource1"
cp -n ./*.deb /offline-apt/ 2>/dev/null || true
find /var/cache/apt/archives -name '*.deb' -exec cp -n {} /offline-apt/ \;
cd /offline-apt
dpkg-scanpackages --multiversion . /dev/null | gzip -9c > Packages.gz
find . -maxdepth 1 -name '*.deb' -printf '%f\n' | sort > /offline-meta/deb-files.txt

CONTAINER
)"
}

warm_npm_dependency_cache() {
  local npm_cache_dir="${WORKDIR}/packages/npm-cache"
  mkdir -p "${npm_cache_dir}"
  docker run --rm --platform "linux/${ARCH}" \
    -e OPENCLAW_VERSION="${OPENCLAW_VERSION}" \
    -e PLAYWRIGHT_VERSION="${PLAYWRIGHT_VERSION}" \
    -v "${npm_cache_dir}:/offline-cache" \
    node:24-bookworm \
    bash -lc "$(cat <<'CONTAINER'
set -euo pipefail
export npm_config_cache=/offline-cache
export npm_config_audit=false
export npm_config_fund=false

npm install --ignore-scripts --no-audit --no-fund --prefix /tmp/global \
  opencode-ai \
  @google/gemini-cli \
  @openai/codex \
  @anthropic-ai/claude-code \
  "openclaw@${OPENCLAW_VERSION}" \
  "@openclaw/codex@${OPENCLAW_VERSION}" \
  "playwright@${PLAYWRIGHT_VERSION}"
CONTAINER
)"
}

download_playwright_browser() {
  if [ "${ARCH}" != "arm64" ]; then
    return
  fi

  local browser_dir="${WORKDIR}/packages/playwright-browsers"
  mkdir -p "${browser_dir}"
  docker run --rm --platform "linux/${ARCH}" \
    -e PLAYWRIGHT_VERSION="${PLAYWRIGHT_VERSION}" \
    -e PLAYWRIGHT_BROWSERS_PATH=/offline-browsers \
    -v "${browser_dir}:/offline-browsers" \
    node:24-bookworm \
    bash -lc 'npx --yes "playwright@${PLAYWRIGHT_VERSION}" install chromium'

  if ! find "${browser_dir}" -type f \
      \( -path '*/chrome-linux/chrome' -o -path '*/chrome-linux64/chrome' \) \
      -print -quit | grep -q .; then
    echo "Bundled Playwright Chromium executable was not found for ${ARCH}" >&2
    exit 1
  fi
}

download_binaries() {
  local bin_dir="${WORKDIR}/packages/bin"
  local vault_arch="${ARCH}"
  local ttyd_arch
  mkdir -p "${bin_dir}"

  case "${ARCH}" in
    amd64) ttyd_arch=x86_64 ;;
    arm64) ttyd_arch=aarch64 ;;
  esac

  curl -fsSL \
    "https://releases.hashicorp.com/vault/${VAULT_VERSION}/vault_${VAULT_VERSION}_linux_${vault_arch}.zip" \
    -o "${bin_dir}/vault_${VAULT_VERSION}_linux_${vault_arch}.zip"

  if [ "${TTYD_VERSION}" = "latest" ]; then
    curl -fsSL "https://github.com/tsl0922/ttyd/releases/latest/download/ttyd.${ttyd_arch}" \
      -o "${bin_dir}/ttyd.${ttyd_arch}"
  else
    curl -fsSL "https://github.com/tsl0922/ttyd/releases/download/${TTYD_VERSION}/ttyd.${ttyd_arch}" \
      -o "${bin_dir}/ttyd.${ttyd_arch}"
  fi
  chmod +x "${bin_dir}/ttyd.${ttyd_arch}"
}

export_container_images() {
  local images_dir="${WORKDIR}/packages/images"
  mkdir -p "${images_dir}"
  docker pull --platform "linux/${ARCH}" "${POSTGRES_IMAGE}"
  docker save "${POSTGRES_IMAGE}" -o "${images_dir}/$(safe_name "${POSTGRES_IMAGE}").tar"
}

write_manifest() {
  local manifest="${WORKDIR}/metadata/manifest.json"
  mkdir -p "$(dirname "${manifest}")"
  cat > "${WORKDIR}/metadata/target.env" <<EOF
DISTRO_ID=${DISTRO_ID}
DISTRO_VERSION=${DISTRO_VERSION}
ARCH=${ARCH}
EOF
  cat > "${manifest}" <<JSON
{
  "name": "ai-workspace-all-in-one-offline",
  "packageVersion": "${PACKAGE_VERSION}",
  "target": {
    "distro": "${DISTRO_ID}",
    "version": "${DISTRO_VERSION}",
    "arch": "${ARCH}"
  },
  "sources": {
    "playbooks": {"repo": "${PLAYBOOKS_REPO}", "ref": "${PLAYBOOKS_REF}"},
    "xworkspaceConsole": {"repo": "${CONSOLE_REPO}", "ref": "${CONSOLE_REF}"},
    "xworkspaceCoreSkills": {"repo": "${CORE_SKILLS_REPO}", "ref": "${CORE_SKILLS_REF}"}
  },
  "componentReleases": {
    "xworkspaceConsole": {"repo": "${CONSOLE_RUNTIME_RELEASE_REPO}", "tag": "$(cat "${WORKDIR}/metadata/components/xworkspace-console.tag")"},
    "xworkmateBridge": {"repo": "${BRIDGE_RUNTIME_RELEASE_REPO}", "tag": "$(cat "${WORKDIR}/metadata/components/xworkmate-bridge.tag")"},
    "qmd": {"repo": "${QMD_RUNTIME_RELEASE_REPO}", "tag": "$(cat "${WORKDIR}/metadata/components/qmd.tag")"},
    "litellm": {"repo": "${LITELLM_RUNTIME_RELEASE_REPO}", "tag": "$(cat "${WORKDIR}/metadata/components/litellm.tag")"}
  },
  "versions": {
    "vault": "${VAULT_VERSION}",
    "openclaw": "${OPENCLAW_VERSION}",
    "playwright": "${PLAYWRIGHT_VERSION}",
    "googleChrome": "${GOOGLE_CHROME_VERSION}",
    "postgresImage": "${POSTGRES_IMAGE}"
  }
}
JSON
}

main() {
  rm -rf "${WORKDIR}" "${OUT}"
  mkdir -p "${WORKDIR}/repos" "${WORKDIR}/scripts" "${WORKDIR}/metadata"

  local image
  image="$(image_for_target)"

  echo "Building AI Workspace offline package for ${DISTRO_ID} ${DISTRO_VERSION} ${ARCH}"
  echo "Using package workspace: ${WORKDIR}"

  clone_repo "${PLAYBOOKS_REPO}" "${PLAYBOOKS_REF}" "${WORKDIR}/repos/playbooks" > "${WORKDIR}/metadata/playbooks.commit"
  clone_repo "${CONSOLE_REPO}" "${CONSOLE_REF}" "${WORKDIR}/repos/xworkspace-console" > "${WORKDIR}/metadata/xworkspace-console.commit"
  clone_repo "${CORE_SKILLS_REPO}" "${CORE_SKILLS_REF}" "${WORKDIR}/repos/xworkspace-core-skills" > "${WORKDIR}/metadata/xworkspace-core-skills.commit"
  download_apt_packages "${image}"
  download_component_releases
  warm_npm_dependency_cache
  download_playwright_browser
  download_binaries
  export_container_images

  cp "${SCRIPT_DIR}/ai-workspace-offline-install.sh" "${WORKDIR}/scripts/"
  chmod +x "${WORKDIR}/scripts/ai-workspace-offline-install.sh"
  write_manifest

  cat > "${WORKDIR}/README.md" <<'README'
# AI Workspace All-in-One Offline Package

The standard online bootstrap can use matching packages published from
`https://github.com/ai-workspace-lab/XLaunch/releases` automatically:

```bash
curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/main/scripts/setup-ai-workspace-all-in-one.sh | bash -
```

Extract this archive on the target host, then run:

```bash
sudo ./scripts/ai-workspace-offline-install.sh
```

The installer configures a local APT repository from `packages/apt`, loads bundled
container images when Docker is available, and runs the packaged
`xworkspace-console/scripts/setup-ai-workspace-all-in-one.sh` with local source
directories for playbooks, console, core skills, and bridge code.

Set the same environment variables supported by the online installer before
running the script, for example:

```bash
sudo env \
  XWORKMATE_BRIDGE_DOMAIN=acp-bridge.onwalk.net \
  AI_WORKSPACE_SECURITY_LEVEL=strict \
  ./scripts/ai-workspace-offline-install.sh
```
README

  tar -czf "${OUT}" -C "$(dirname "${WORKDIR}")" "$(basename "${WORKDIR}")"
  ls -lh "${OUT}"
}

main "$@"
