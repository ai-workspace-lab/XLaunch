#!/usr/bin/env bash
set -euo pipefail

cmdb_path=${CMDB_PATH:-cmdb/cmdb.json}
host=${MATRIX_HOST:?MATRIX_HOST is required}
ssh_key=${SSH_KEY_PATH:-"$HOME/.ssh/id_deploy"}
ssh_key="${ssh_key/#\~/$HOME}"
run_id=${GITHUB_RUN_ID:-manual}
run_attempt=${GITHUB_RUN_ATTEMPT:-1}

ip="$(jq -r --arg host "$host" '.[$host].ip' "$cmdb_path")"
user="$(jq -r --arg host "$host" '.[$host].ansible_user // "root"' "$cmdb_path")"
domain="${XWORKMATE_BRIDGE_DOMAIN:-}"
if [ -z "$domain" ]; then
  domain="$(jq -r --arg host "$host" '(.[$host].host_vars.service_domains // "") | if type == "array" then .[0] else split(",")[0] end' "$cmdb_path" | tr -d ' ')"
fi

if [ -z "$ip" ] || [ "$ip" = "null" ]; then
  echo "::error::No IP found in ${cmdb_path} for ${host}" >&2
  exit 1
fi

ssh_opts=(
  -i "$ssh_key"
  -o StrictHostKeyChecking=accept-new
  -o ServerAliveInterval=30
  -o ServerAliveCountMax=60
  -o ConnectTimeout=20
  -o BatchMode=yes
)

remote_dir="/tmp/xworkspace-bootstrap-${run_id}-${run_attempt}-${host//[^A-Za-z0-9_.-]/_}"
remote_env="${remote_dir}/env"
remote_log="${remote_dir}/bootstrap.log"
remote_rc="${remote_dir}/bootstrap.rc"
remote_runner="${remote_dir}/run.sh"

echo "Bootstrapping ${host} (${user}@${ip}) on-host, domain=${domain:-<none>} ..."

remote_payload="$(mktemp)"
trap 'rm -f "$remote_payload"' EXIT

# 离线包是按 release 快照打包的；当其落后于 playbooks main（如 Chrome 版本钉点、
# postgres PGDATA 属主等已在 main 修复但未重新发包）时，默认 offline=auto 会用到
# 过期 playbook 导致部署失败。默认 off，让 on-host 引导在线 git clone 最新 main；
# 待离线包重新发布后可改回 auto 以恢复离线加速。
{
  printf 'AI_WORKSPACE_OFFLINE_MODE=%q\n' "${AI_WORKSPACE_OFFLINE_MODE:-off}"
  printf 'XWORKMATE_BRIDGE_DOMAIN=%q\n' "$domain"
  # 空则不写，让 on-host installer 的 resolve_unified_auth_token 走"复用持久化/自动生成"分支。
  printf 'AI_WORKSPACE_AUTH_TOKEN=%q\n' "${AI_WORKSPACE_AUTH_TOKEN:-}"
  printf 'DEEPSEEK_API_KEY=%q\n' "${DEEPSEEK_API_KEY:-}"
  printf 'NVIDIA_API_KEY=%q\n' "${NVIDIA_API_KEY:-}"
  printf 'OLLAMA_API_KEY=%q\n' "${OLLAMA_API_KEY:-}"
  printf 'AI_WORKSPACE_BRANCH=%q\n' "${GITHUB_REF_NAME:-main}"
  # BRANCH controls which branch of ai-workspace-infra/playbooks is cloned on-host.
  printf 'BRANCH=%q\n' "${PLAYBOOKS_BRANCH:-main}"
} > "$remote_payload"

ssh "${ssh_opts[@]}" "${user}@${ip}" "mkdir -p '$remote_dir' && chmod 700 '$remote_dir'"
scp "${ssh_opts[@]}" "$remote_payload" "${user}@${ip}:${remote_env}" >/dev/null
ssh "${ssh_opts[@]}" "${user}@${ip}" "chmod 600 '$remote_env'"

ssh "${ssh_opts[@]}" "${user}@${ip}" "cat > '$remote_runner' && chmod 700 '$remote_runner'" <<'REMOTE_SCRIPT'
#!/usr/bin/env bash
set -euo pipefail
remote_env=$1
remote_log=$2
remote_rc=$3
if [ -f "$remote_rc" ]; then
  exit 0
fi
(
  set +e
  source "$remote_env"
  export AI_WORKSPACE_OFFLINE_MODE XWORKMATE_BRIDGE_DOMAIN AI_WORKSPACE_AUTH_TOKEN DEEPSEEK_API_KEY NVIDIA_API_KEY OLLAMA_API_KEY AI_WORKSPACE_BRANCH BRANCH
  bash -lc "curl -sfL https://raw.githubusercontent.com/ai-workspace-lab/XLaunch/${AI_WORKSPACE_BRANCH}/scripts/setup-ai-workspace-all-in-one.sh | bash -"
  rc=$?
  printf '%s\n' "$rc" > "$remote_rc"
  exit "$rc"
) > "$remote_log" 2>&1 &
REMOTE_SCRIPT

ssh "${ssh_opts[@]}" "${user}@${ip}" "nohup '$remote_runner' '$remote_env' '$remote_log' '$remote_rc' >/dev/null 2>&1 &"

last_lines=0
while true; do
  poll_output="$(ssh "${ssh_opts[@]}" "${user}@${ip}" "if [ -f '$remote_log' ]; then wc -l < '$remote_log'; else echo 0; fi; if [ -f '$remote_rc' ]; then cat '$remote_rc'; else echo RUNNING; fi" 2>/dev/null || true)"
  line_count="$(printf '%s\n' "$poll_output" | sed -n '1p')"
  rc_value="$(printf '%s\n' "$poll_output" | sed -n '2p')"
  case "$line_count" in
    ''|*[!0-9]*) line_count=0 ;;
  esac

  if [ "$line_count" -gt "$last_lines" ]; then
    start=$((last_lines + 1))
    ssh "${ssh_opts[@]}" "${user}@${ip}" "sed -n '${start},${line_count}p' '$remote_log'" || true
    last_lines="$line_count"
  else
    echo "[INFO] Bootstrap still running on ${host}; no new log lines."
  fi

  if [ "$rc_value" != "RUNNING" ] && [ -n "$rc_value" ]; then
    if [ "$rc_value" = "0" ]; then
      echo "[SUCCESS] Bootstrap completed on ${host}."
      exit 0
    fi
    echo "::error::Bootstrap failed on ${host} with exit code ${rc_value}."
    exit "$rc_value"
  fi

  sleep 20
done
