#!/usr/bin/env python3
"""
This script is invoked by setup-ai-workspace-all-in-one.sh to patch playbooks for macOS.
"""

import os
from pathlib import Path

def main():
    def patch_0():
        
        path = Path("setup-xworkspace-console.yaml")
        text = path.read_text()
        
        commands = {
            'su - {{ xworkspace_console_user }} -c "systemctl --user daemon-reload"': 'systemctl --user daemon-reload',
            'su - {{ xworkspace_console_user }} -c "systemctl --user restart xworkspace-console.service"': 'systemctl --user restart xworkspace-console.service',
            'su - {{ xworkspace_console_user }} -c "systemctl --user restart xworkspace-ttyd.service"': 'systemctl --user restart xworkspace-ttyd.service',
        }
        
        def wrapped(systemctl_command: str) -> str:
            lines = [
                'uid="$(id -u {{ xworkspace_console_user }})"',
                'loginctl enable-linger {{ xworkspace_console_user }} || true',
                'systemctl start "user@${uid}.service" || true',
                f'runuser -u {{{{ xworkspace_console_user }}}} -- env XDG_RUNTIME_DIR="/run/user/${{uid}}" DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/${{uid}}/bus" {systemctl_command}',
            ]
            return "\n        ".join(lines)
        
        updated = text
        for old, command in commands.items():
            updated = updated.replace(old, wrapped(command))
        
        if updated != text:
            path.write_text(updated)

    patch_0()

    def patch_1():
        
        vars_path = Path("roles/vhosts/vault/vars/main.yml")
        tasks_path = Path("roles/vhosts/vault/tasks/main.yml")
        macos_path = Path("roles/vhosts/vault/tasks/macos.yml")
        
        # 1) Make vault dirs and binary path OS-conditional (Linux unchanged).
        vars_text = vars_path.read_text()
        vars_subs = {
            "vault_binary_path: /usr/local/bin/vault":
                "vault_binary_path: \"{{ '/opt/homebrew/bin/vault' if ansible_os_family == 'Darwin' else '/usr/local/bin/vault' }}\"",
            "vault_config_dir: /etc/vault.d":
                "vault_config_dir: \"{{ (ansible_env.HOME ~ '/Library/Application Support/vault') if ansible_os_family == 'Darwin' else '/etc/vault.d' }}\"",
            "vault_data_dir: /opt/vault/data":
                "vault_data_dir: \"{{ (ansible_env.HOME ~ '/Library/Application Support/vault/data') if ansible_os_family == 'Darwin' else '/opt/vault/data' }}\"",
        }
        for old, new in vars_subs.items():
            if old in vars_text:
                vars_text = vars_text.replace(old, new)
        vars_path.write_text(vars_text)
        
        # 2) Skip the root-owned directory creation task on macOS.
        tasks_text = tasks_path.read_text()
        dir_when_old = (
            '  loop:\n'
            '    - "{{ vault_config_dir }}"\n'
            '    - "{{ vault_data_dir }}"\n'
            '  when:\n'
            '    - vault_deploy_mode == "standalone"\n'
        )
        dir_when_new = dir_when_old + "    - ansible_os_family != 'Darwin'\n"
        if dir_when_old in tasks_text and "    - ansible_os_family != 'Darwin'\n\n- name: Deploy standalone Vault systemd" not in tasks_text:
            tasks_text = tasks_text.replace(dir_when_old, dir_when_new, 1)
        
        # 2b) The admin bootstrap runs files/init_vault_admin.sh, which require_cmd's
        # vault/jq/curl/base64. On macOS those live under Homebrew, which is not on the
        # minimal PATH ansible.builtin.script uses; prepend the Homebrew bin dirs so the
        # helper can find them.
        boot_old = (
            '    --ui-url {{ vault_admin_ui_url | quote }}\n'
            '  no_log: true\n'
        )
        boot_new = (
            '    --ui-url {{ vault_admin_ui_url | quote }}\n'
            '  environment:\n'
            '    PATH: "/opt/homebrew/bin:/usr/local/bin:{{ ansible_env.PATH }}"\n'
            '  no_log: true\n'
        )
        if boot_old in tasks_text and boot_new not in tasks_text:
            tasks_text = tasks_text.replace(boot_old, boot_new, 1)

        kv_old = (
            '- name: Bootstrap Vault admin userpass auth\n'
            '  ansible.builtin.script: >-\n'
        )
        kv_new = (
            '- name: Ensure Vault KV v2 secrets engine is enabled\n'
            '  ansible.builtin.command: >-\n'
            "    bash -lc '\n"
            "    if ! vault secrets list -format=json | jq -e \"has(\\\"kv/\\\")\" >/dev/null; then\n"
            "      vault secrets enable -version=2 kv >/dev/null\n"
            "    fi'\n"
            '  environment:\n'
            '    PATH: "/opt/homebrew/bin:/usr/local/bin:{{ ansible_env.PATH }}"\n'
            '    VAULT_ADDR: "{{ vault_admin_addr }}"\n'
            '    VAULT_TOKEN: "{{ vault_server_root_access_token }}"\n'
            '  changed_when: false\n'
            '  when:\n'
            '    - vault_deploy_mode in ["standalone", "external"]\n\n'
            '- name: Bootstrap Vault admin userpass auth\n'
            '  ansible.builtin.script: >-\n'
        )
        if kv_old in tasks_text and "Ensure Vault KV v2 secrets engine is enabled" not in tasks_text:
            tasks_text = tasks_text.replace(kv_old, kv_new, 1)
        
        tasks_path.write_text(tasks_text)
        
        # 2d) init_vault_admin.sh resolves the admin entity_id by logging in as the
        # user. Once the login MFA enforcement it creates exists, that login is
        # MFA-gated and returns no entity_id, so re-runs fail with "missing entityID".
        # Resolve the entity via its userpass entity-alias instead (idempotent).
        init_path = Path("roles/vhosts/vault/files/init_vault_admin.sh")
        if init_path.exists():
            init_text = init_path.read_text()
            login_old = (
                'bootstrap_json="$(vault write -format=json "auth/userpass/login/${USERNAME}" password="$PASSWORD")"\n'
                'entity_id="$(printf \'%s\' "$bootstrap_json" | jq -r \'.auth.entity_id\')"\n'
                'bootstrap_token="$(printf \'%s\' "$bootstrap_json" | jq -r \'.auth.client_token\')"\n'
            )
            login_new = (
                'entity_id=""\n'
                '# bootstrap_token kept defined (empty) so any later "vault token revoke\n'
                '# $bootstrap_token" line stays valid under set -u; we no longer log in.\n'
                'bootstrap_token=""\n'
                'for alias_id in $(vault list -format=json identity/entity-alias/id 2>/dev/null | jq -r \'.[]?\'); do\n'
                '  alias_json="$(vault read -format=json "identity/entity-alias/id/${alias_id}" 2>/dev/null || true)"\n'
                '  alias_name="$(printf \'%s\' "$alias_json" | jq -r \'.data.name // empty\')"\n'
                '  alias_mount="$(printf \'%s\' "$alias_json" | jq -r \'.data.mount_accessor // empty\')"\n'
                '  if [[ "$alias_name" == "$USERNAME" && "$alias_mount" == "$userpass_accessor" ]]; then\n'
                '    entity_id="$(printf \'%s\' "$alias_json" | jq -r \'.data.canonical_id // empty\')"\n'
                '    break\n'
                '  fi\n'
                'done\n'
                '\n'
                'if [[ -z "$entity_id" ]]; then\n'
                '  entity_id="$(vault write -format=json identity/entity name="$USERNAME" policies="$POLICY_NAME" | jq -r \'.data.id\')"\n'
                '  vault write identity/entity-alias name="$USERNAME" canonical_id="$entity_id" mount_accessor="$userpass_accessor" >/dev/null\n'
                'fi\n'
            )
            if login_old in init_text:
                init_text = init_text.replace(login_old, login_new, 1)
                # Note: we intentionally do NOT delete the later "vault token revoke
                # $bootstrap_token" line — on some revisions it is wrapped in an if/fi,
                # and removing it would leave an empty then-block (syntax error). With
                # bootstrap_token="" set above, the revoke is a harmless no-op.
                init_path.write_text(init_text)
        
        # 3) Create the macOS vault dirs (user-owned) before the launchd plist is laid down.
        macos_text = macos_path.read_text()
        dir_task = (
            "- name: Ensure macOS Vault directories exist\n"
            "  ansible.builtin.file:\n"
            "    path: \"{{ item }}\"\n"
            "    state: directory\n"
            "    mode: \"0755\"\n"
            "  loop:\n"
            "    - \"{{ vault_config_dir }}\"\n"
            "    - \"{{ vault_data_dir }}\"\n"
            "    - \"{{ ansible_env.HOME }}/.local/state/xworkspace\"\n\n"
        )
        anchor = "- name: Install HashiCorp Tap\n"
        if "Ensure macOS Vault directories exist" not in macos_text and anchor in macos_text:
            macos_text = macos_text.replace(anchor, dir_task + anchor, 1)
        
        # jq is not preinstalled on macOS and the Linux apt task that installs it is
        # Darwin-skipped, yet init_vault_admin.sh requires it. Install it via Homebrew.
        vault_brew_old = (
            "- name: Install Vault via Homebrew\n"
            "  ansible.builtin.command: brew install hashicorp/tap/vault\n"
            "  args:\n"
            "    creates: /opt/homebrew/bin/vault\n"
            "  changed_when: true\n"
        )
        jq_task = (
            "\n- name: Install jq via Homebrew (required by Vault admin bootstrap)\n"
            "  ansible.builtin.command: brew install jq\n"
            "  args:\n"
            "    creates: /opt/homebrew/bin/jq\n"
            "  changed_when: true\n"
        )
        if vault_brew_old in macos_text and "Install jq via Homebrew" not in macos_text:
            macos_text = macos_text.replace(vault_brew_old, vault_brew_old + jq_task, 1)
        macos_path.write_text(macos_text)

    patch_1()

    def patch_vault_database_write():
        # Keep database writes safe when an older Vault data directory is reused.
        path = Path("write_passwords_to_vault.yml")
        if not path.exists():
            return
        text = path.read_text()
        marker = "    - name: Securely write database passwords to Vault KV\n"
        debug_start = "    - name: Debug vault token length and prefix\n"
        prepare_start = "    - name: Prepare Vault payload\n"
        if debug_start in text and prepare_start in text:
            start = text.index(debug_start)
            end = text.index(prepare_start, start)
            text = text[:start] + text[end:]
        if marker not in text or "Inspect Vault mounts before database writes" in text:
            path.write_text(text)
            return
        task = (
            "    - name: Inspect Vault mounts before database writes\n"
            "      ansible.builtin.uri:\n"
            "        url: \"{{ vault_addr }}/v1/sys/mounts\"\n"
            "        method: GET\n"
            "        headers:\n"
            "          X-Vault-Token: \"{{ vault_token }}\"\n"
            "        status_code: 200\n"
            "        return_content: true\n"
            "      register: vault_mounts_before_database_write\n"
            "      retries: 12\n"
            "      delay: 5\n"
            "      until: vault_mounts_before_database_write.status | default(0) == 200\n"
            "      changed_when: false\n"
            "      when:\n"
            "        - resolved_db_configs is defined\n"
            "        - vault_token | length > 0\n"
            "      run_once: true\n"
            "      delegate_to: localhost\n"
            "      no_log: \"{{ not (lookup('env', 'AI_WORKSPACE_DEBUG') | default('false', true) | bool) }}\"\n\n"
            "    - name: Enable Vault KV v2 mount before database writes\n"
            "      ansible.builtin.uri:\n"
            "        url: \"{{ vault_addr }}/v1/sys/mounts/kv\"\n"
            "        method: POST\n"
            "        headers:\n"
            "          X-Vault-Token: \"{{ vault_token }}\"\n"
            "        body_format: json\n"
            "        body:\n"
            "          type: kv\n"
            "          options:\n"
            "            version: \"2\"\n"
            "        status_code:\n"
            "          - 200\n"
            "          - 204\n"
            "      when:\n"
            "        - resolved_db_configs is defined\n"
            "        - vault_token | length > 0\n"
            "        - \"'kv/' not in (vault_mounts_before_database_write.json.data | default({}))\"\n"
            "      run_once: true\n"
            "      delegate_to: localhost\n"
            "      no_log: \"{{ not (lookup('env', 'AI_WORKSPACE_DEBUG') | default('false', true) | bool) }}\"\n\n"
        )
        old_start = "    - name: Ensure Vault KV v2 mount exists before database writes\n"
        if old_start in text:
            start = text.index(old_start)
            end = text.index(marker, start)
            text = text[:start] + text[end:]
        path.write_text(text.replace(marker, task + marker, 1))

    patch_vault_database_write()

    def patch_2():
        
        path = Path("roles/vhosts/common/tasks/main.yml")
        text = path.read_text()
        guard = "  when: ansible_os_family != 'Darwin'\n"
        
        # Tasks that end with a trailing attribute and have no `when:` yet -> append guard.
        append_blocks = [
            ('- name: Base | set timezone\n'
             '  ansible.builtin.command: "timedatectl set-timezone Asia/Shanghai"\n'
             '  changed_when: false\n'
             '  become: true\n'),
            ('- name: Base | render /etc/hostname\n'
             '  ansible.builtin.template:\n'
             '    src: templates/hostname.j2\n'
             '    dest: /etc/hostname\n'
             '    owner: root\n'
             '    group: root\n'
             '    mode: "0644"\n'
             '  become: true\n'),
            ('- name: Base | set hostname\n'
             '  ansible.builtin.hostname:\n'
             '    name: "{{ inventory_hostname }}"\n'
             '  become: true\n'),
            ('- name: Base | update /etc/hosts\n'
             '  ansible.builtin.template:\n'
             '    src: templates/hosts\n'
             '    dest: /etc/hosts\n'
             '    owner: root\n'
             '    group: root\n'
             '    mode: "0644"\n'
             '  become: true\n'),
            ('- name: Base | harden ssh\n'
             '  ansible.builtin.script: files/secure_ssh.sh\n'
             '  become: true\n'),
            ('- name: Base | harden ssh config\n'
             '  ansible.builtin.import_tasks: harden_ssh.yml\n'
             '  tags: [ssh, security]\n'),
            ('- name: Base | configure fail2ban\n'
             '  ansible.builtin.import_tasks: fail2ban.yml\n'
             '  tags: [fail2ban, security]\n'),
        ]
        for block in append_blocks:
            if block in text and (block + guard) not in text:
                text = text.replace(block, block + guard, 1)
        
        # Tasks that already have a `when:` list -> add the Darwin condition to it.
        when_blocks = [
            ('  when:\n'
             '    - common_security_limits.enabled | default(true) | bool\n'),
            ('  when:\n'
             '    - common_firewall.enabled | default(true) | bool\n'),
        ]
        extra = "    - ansible_os_family != 'Darwin'\n"
        for block in when_blocks:
            if block in text and (block + extra) not in text:
                text = text.replace(block, block + extra, 1)
        
        path.write_text(text)

    patch_2()

    def patch_3():
        
        path = Path("roles/vhosts/postgres/tasks/macos.yml")
        text = path.read_text()
        old = (
            "- name: Ensure PostgreSQL 16 is installed via Homebrew\n"
            "  community.general.homebrew:\n"
            "    name: postgresql@16\n"
            "    state: present\n"
        )
        new = (
            "- name: Ensure PostgreSQL 16 is installed via Homebrew\n"
            "  ansible.builtin.command: brew install postgresql@16\n"
            "  environment:\n"
            "    PATH: \"/opt/homebrew/bin:/usr/local/bin:{{ ansible_env.PATH }}\"\n"
            "    HOMEBREW_NO_AUTO_UPDATE: \"1\"\n"
            "  register: postgresql_brew_install\n"
            "  changed_when: >-\n"
            "    'already installed' not in (postgresql_brew_install.stderr | default(''))\n"
            "    and 'already installed' not in (postgresql_brew_install.stdout | default(''))\n"
            "  failed_when: postgresql_brew_install.rc != 0\n"
        )
        if old in text:
            text = text.replace(old, new, 1)
            path.write_text(text)

    patch_3()

    def patch_4():
        
        path = Path("roles/vhosts/litellm/tasks/main.yml")
        text = path.read_text()
        old = (
            "- name: Install LiteLLM prerequisites (macOS)\n"
            "  community.general.homebrew:\n"
            "    name: python@3.13\n"
            "    state: present\n"
            "  when: ansible_os_family == 'Darwin'\n"
        )
        new = (
            "- name: Install LiteLLM prerequisites (macOS)\n"
            "  ansible.builtin.command: brew install python@3.13\n"
            "  environment:\n"
            "    PATH: \"/opt/homebrew/bin:/usr/local/bin:{{ ansible_env.PATH }}\"\n"
            "    HOMEBREW_NO_AUTO_UPDATE: \"1\"\n"
            "  register: litellm_brew_python\n"
            "  changed_when: >-\n"
            "    'already installed' not in (litellm_brew_python.stderr | default(''))\n"
            "    and 'already installed' not in (litellm_brew_python.stdout | default(''))\n"
            "  failed_when: litellm_brew_python.rc != 0\n"
            "  when: ansible_os_family == 'Darwin'\n"
        )
        if old in text:
            text = text.replace(old, new, 1)
        
        # The config dir and env-file tasks hardcode owner/group root, which cannot be
        # chowned under become=false on macOS. Make ownership OS-conditional (service
        # user/group on Darwin, root on Linux). The config dir path itself is relocated
        # to a user-writable location via the litellm_config_dir extra-var.
        owner_subs = [
            (
                '    path: "{{ litellm_config_dir }}"\n'
                '    state: directory\n'
                '    owner: root\n'
                '    group: root\n'
                '    mode: "0755"\n',
                '    path: "{{ litellm_config_dir }}"\n'
                '    state: directory\n'
                '    owner: "{{ litellm_service_user if ansible_os_family == \'Darwin\' else \'root\' }}"\n'
                '    group: "{{ litellm_service_group if ansible_os_family == \'Darwin\' else \'root\' }}"\n'
                '    mode: "0755"\n',
            ),
            (
                '    dest: "{{ litellm_env_file }}"\n'
                '    owner: root\n'
                '    group: root\n'
                '    mode: "0600"\n',
                '    dest: "{{ litellm_env_file }}"\n'
                '    owner: "{{ litellm_service_user if ansible_os_family == \'Darwin\' else \'root\' }}"\n'
                '    group: "{{ litellm_service_group if ansible_os_family == \'Darwin\' else \'root\' }}"\n'
                '    mode: "0600"\n',
            ),
        ]
        for o, n in owner_subs:
            if o in text:
                text = text.replace(o, n, 1)

        # litellm[proxy] pulls large wheels (polars-runtime ~46MB, etc.) that
        # frequently break mid-stream over slow/mirrored links with
        # IncompleteRead, failing the whole deploy. Make the online install
        # resilient: --retries reconnects and --resume-retries (pip >= 25.1,
        # which the macOS python@3.13 venv already ships) continues a partial
        # download instead of restarting it. Until the playbooks repo carries
        # this in the role itself, the curl|bash clone path needs it injected.
        pip_old = (
            '    executable: "{{ litellm_pip_executable }}"\n'
            '    state: present\n'
            '  environment:\n'
            '    PIP_CACHE_DIR: "{{ litellm_pip_cache_dir }}"\n'
            '    PIP_DEFAULT_TIMEOUT: "120"\n'
        )
        pip_new = (
            '    executable: "{{ litellm_pip_executable }}"\n'
            '    state: present\n'
            '    extra_args: "--retries 5 --resume-retries 5"\n'
            '  environment:\n'
            '    PIP_CACHE_DIR: "{{ litellm_pip_cache_dir }}"\n'
            '    PIP_DEFAULT_TIMEOUT: "180"\n'
        )
        if pip_old in text and pip_new not in text:
            text = text.replace(pip_old, pip_new, 1)

        # `default('{}')` does NOT replace an empty string (only an undefined
        # value), so when the "Inspect installed LiteLLM dependency versions"
        # task returns empty stdout (common on a re-run / partial venv),
        # from_json('') raises and the set_fact fails with a confusing
        # "args could not be converted to dict" error. Use default(..., true)
        # so empty/falsy stdout falls back to '{}'.
        text = text.replace(
            "default('{}') | from_json",
            "default('{}', true) | from_json",
        )

        path.write_text(text)
        
        # provision-database.yml runs psql with become_user postgres, which has no
        # equivalent on macOS Homebrew (no postgres system user, no passwordless sudo,
        # psql off-PATH). On Darwin run without escalation as the current user (the brew
        # DB superuser) and put the postgresql@16 bin on PATH. Linux unchanged.
        prov_path = Path("roles/vhosts/litellm/tasks/provision-database.yml")
        if prov_path.exists():
            prov = prov_path.read_text()
            prov_old = (
                "  args:\n"
                "    executable: /bin/bash\n"
                "  become: true\n"
                "  become_user: \"{{ 'root' if litellm_database_provisioner == 'docker' else 'postgres' }}\"\n"
            )
            prov_new = (
                "  args:\n"
                "    executable: /bin/bash\n"
                "  environment:\n"
                "    PATH: \"/opt/homebrew/opt/postgresql@16/bin:/usr/local/opt/postgresql@16/bin:{{ ansible_env.PATH }}\"\n"
                "  become: \"{{ ansible_os_family != 'Darwin' }}\"\n"
                "  become_user: \"{{ 'root' if litellm_database_provisioner == 'docker' else 'postgres' }}\"\n"
            )
            if prov_old in prov:
                prov = prov.replace(prov_old, prov_new)
                prov_path.write_text(prov)

    patch_4()

    def patch_5():
        
        path = Path("setup-xworkspace-console.yaml")
        if path.exists():
            text = path.read_text()
        
            # 1. Skip release archive download/validate/install tasks on macOS.
            download_old = (
                "    - name: Download XWorkspace Console runtime release\n"
                "      ansible.builtin.get_url:\n"
                "        url: \"https://github.com/ai-workspace-lab/xworkspace-console/releases/latest/download/xworkspace-console-runtime-{{ ansible_system | lower }}-{{ 'amd64' if ansible_architecture in ['x86_64', 'amd64'] else 'arm64' }}.tar.gz\"\n"
                "        dest: \"/tmp/xworkspace-console-runtime.tar.gz\"\n"
                "        mode: \"0644\"\n"
                "        force: true\n"
                "      when: xworkspace_console_runtime_archive | length == 0"
            )
            download_new = (
                "    - name: Download XWorkspace Console runtime release\n"
                "      ansible.builtin.get_url:\n"
                "        url: \"https://github.com/ai-workspace-lab/XLaunch/releases/latest/download/xworkspace-console-runtime-{{ ansible_system | lower }}-{{ 'amd64' if ansible_architecture in ['x86_64', 'amd64'] else 'arm64' }}.tar.gz\"\n"
                "        dest: \"/tmp/xworkspace-console-runtime.tar.gz\"\n"
                "        mode: \"0644\"\n"
                "        force: true\n"
                "      when:\n"
                "        - xworkspace_console_runtime_archive | length == 0\n"
                "        - ansible_os_family != 'Darwin'"
            )
            if download_old in text:
                text = text.replace(download_old, download_new, 1)
        
            validate_old = (
                "    - name: Validate packaged XWorkspace Console runtime\n"
                "      ansible.builtin.stat:\n"
                "        path: \"{{ xworkspace_console_runtime_archive_resolved }}\"\n"
                "      register: xworkspace_console_runtime_archive_stat"
            )
            validate_new = (
                "    - name: Validate packaged XWorkspace Console runtime\n"
                "      ansible.builtin.stat:\n"
                "        path: \"{{ xworkspace_console_runtime_archive_resolved }}\"\n"
                "      register: xworkspace_console_runtime_archive_stat\n"
                "      when: ansible_os_family != 'Darwin'"
            )
            if validate_old in text and (validate_old + "\n      when:") not in text:
                text = text.replace(validate_old, validate_new, 1)
        
            require_old = (
                "    - name: Require packaged XWorkspace Console runtime\n"
                "      ansible.builtin.assert:\n"
                "        that:\n"
                "          - xworkspace_console_runtime_archive_stat.stat.exists | default(false)\n"
                "        fail_msg: \"A valid XWORKSPACE_CONSOLE_RUNTIME_ARCHIVE is required or download failed.\""
            )
            require_new = (
                "    - name: Require packaged XWorkspace Console runtime\n"
                "      ansible.builtin.assert:\n"
                "        that:\n"
                "          - xworkspace_console_runtime_archive_stat.stat.exists | default(false)\n"
                "        fail_msg: \"A valid XWORKSPACE_CONSOLE_RUNTIME_ARCHIVE is required or download failed.\"\n"
                "      when: ansible_os_family != 'Darwin'"
            )
            if require_old in text and (require_old + "\n      when:") not in text:
                text = text.replace(require_old, require_new, 1)
        
            marker_old = (
                "    - name: Inspect installed XWorkspace Console runtime marker\n"
                "      ansible.builtin.slurp:\n"
                "        path: \"{{ xworkspace_console_runtime_marker }}\"\n"
                "      register: xworkspace_console_runtime_marker_content\n"
                "      failed_when: false"
            )
            marker_new = (
                "    - name: Inspect installed XWorkspace Console runtime marker\n"
                "      ansible.builtin.slurp:\n"
                "        path: \"{{ xworkspace_console_runtime_marker }}\"\n"
                "      register: xworkspace_console_runtime_marker_content\n"
                "      failed_when: false\n"
                "      when: ansible_os_family != 'Darwin'"
            )
            if marker_old in text and (marker_old + "\n      when:") not in text:
                text = text.replace(marker_old, marker_new, 1)
        
            install_old = (
                "    - name: Install packaged XWorkspace Console runtime\n"
                "      ansible.builtin.unarchive:\n"
                "        src: \"{{ xworkspace_console_runtime_archive_resolved }}\"\n"
                "        dest: \"{{ xworkspace_console_repo_dir | dirname }}\"\n"
                "        remote_src: true\n"
                "        owner: \"{{ xworkspace_console_user }}\"\n"
                "        group: \"{{ 'staff' if ansible_os_family == 'Darwin' else xworkspace_console_user }}\"\n"
                "      when:\n"
                "        - xworkspace_console_runtime_archive_stat.stat.exists | default(false)\n"
                "        - >-\n"
                "          (xworkspace_console_runtime_marker_content.content | default('') | b64decode | trim)\n"
                "          != (xworkspace_console_runtime_archive_stat.stat.checksum | default(''))\n"
                "          or not (xworkspace_console_api_binary is file)\n"
                "          or not ((xworkspace_console_dashboard_dir ~ '/dist/index.html') is file)"
            )
            install_new = (
                "    - name: Install packaged XWorkspace Console runtime\n"
                "      ansible.builtin.unarchive:\n"
                "        src: \"{{ xworkspace_console_runtime_archive_resolved }}\"\n"
                "        dest: \"{{ xworkspace_console_repo_dir | dirname }}\"\n"
                "        remote_src: true\n"
                "        owner: \"{{ xworkspace_console_user }}\"\n"
                "        group: \"{{ 'staff' if ansible_os_family == 'Darwin' else xworkspace_console_user }}\"\n"
                "      when:\n"
                "        - ansible_os_family != 'Darwin'\n"
                "        - xworkspace_console_runtime_archive_stat.stat.exists | default(false)\n"
                "        - >-\n"
                "          (xworkspace_console_runtime_marker_content.content | default('') | b64decode | trim)\n"
                "          != (xworkspace_console_runtime_archive_stat.stat.checksum | default(''))\n"
                "          or not (xworkspace_console_api_binary is file)\n"
                "          or not ((xworkspace_console_dashboard_dir ~ '/dist/index.html') is file)"
            )
            if install_old in text:
                text = text.replace(install_old, install_new, 1)
        
            record_old = (
                "    - name: Record installed XWorkspace Console runtime checksum\n"
                "      ansible.builtin.copy:\n"
                "        dest: \"{{ xworkspace_console_runtime_marker }}\"\n"
                "        owner: \"{{ xworkspace_console_user }}\"\n"
                "        group: \"{{ 'staff' if ansible_os_family == 'Darwin' else xworkspace_console_user }}\"\n"
                "        mode: \"0644\"\n"
                "        content: \"{{ xworkspace_console_runtime_archive_stat.stat.checksum }}\\n\"\n"
                "      when:\n"
                "        - xworkspace_console_runtime_archive_stat.stat.exists | default(false)"
            )
            record_new = (
                "    - name: Record installed XWorkspace Console runtime checksum\n"
                "      ansible.builtin.copy:\n"
                "        dest: \"{{ xworkspace_console_runtime_marker }}\"\n"
                "        owner: \"{{ xworkspace_console_user }}\"\n"
                "        group: \"{{ 'staff' if ansible_os_family == 'Darwin' else xworkspace_console_user }}\"\n"
                "        mode: \"0644\"\n"
                "        content: \"{{ xworkspace_console_runtime_archive_stat.stat.checksum }}\\n\"\n"
                "      when:\n"
                "        - ansible_os_family != 'Darwin'\n"
                "        - xworkspace_console_runtime_archive_stat.stat.exists | default(false)"
            )
            if record_old in text:
                text = text.replace(record_old, record_new, 1)
        
            # 2. Inject Clone and Build tasks on macOS (Darwin).
            anchor = "    - name: Deploy AI Workspace portal service configuration"
            injected_tasks = (
                "    - name: Check if xworkspace-console repo already exists (macOS)\n"
                "      ansible.builtin.stat:\n"
                "        path: \"{{ xworkspace_console_repo_dir }}/.git\"\n"
                "      register: xworkspace_console_git_stat_macos\n"
                "      when: ansible_os_family == 'Darwin'\n"
                "\n"
                "    - name: Clone xworkspace-console repository (macOS)\n"
                "      ansible.builtin.git:\n"
                "        repo: \"{{ xworkspace_console_source_repo }}\"\n"
                "        dest: \"{{ xworkspace_console_repo_dir }}\"\n"
                "        version: \"{{ xworkspace_console_source_version }}\"\n"
                "        depth: 1\n"
                "      become_user: \"{{ xworkspace_console_user }}\"\n"
                "      when:\n"
                "        - ansible_os_family == 'Darwin'\n"
                "        - not (xworkspace_console_git_stat_macos.stat.exists | default(false))\n"
                "\n"
                "    - name: Build dashboard assets on target (macOS)\n"
                "      ansible.builtin.shell: |\n"
                "        set -euo pipefail\n"
                "        cd \"{{ xworkspace_console_dashboard_dir }}\"\n"
                "        source_commit=\"$(git -C \"{{ xworkspace_console_repo_dir }}\" rev-parse HEAD)\"\n"
                "        marker=\".ai-workspace-build-commit\"\n"
                "        if [ -f \"dist/index.html\" ] && [ \"$(cat \"$marker\" 2>/dev/null || true)\" = \"$source_commit\" ]; then\n"
                "          echo \"build=unchanged\"\n"
                "          exit 0\n"
                "        fi\n"
                "        npm install && npm run build\n"
                "        printf '%s\\n' \"$source_commit\" > \"$marker\"\n"
                "        echo \"build=changed\"\n"
              "      args:\n"
                "        executable: /bin/bash\n"
                "      become_user: \"{{ xworkspace_console_user }}\"\n"
                "      register: xworkspace_console_dashboard_build_macos\n"
                "      changed_when: \"'build=changed' in (xworkspace_console_dashboard_build_macos.stdout | default(''))\"\n"
                "      when: ansible_os_family == 'Darwin'\n"
                "\n"
            )
            if anchor in text and "Clone xworkspace-console repository (macOS)" not in text:
                text = text.replace(anchor, injected_tasks + anchor, 1)
        
            path.write_text(text)
        
        # Patch xworkspace_console_macos.yml to ensure LaunchAgents directory exists
        macos_path = Path("xworkspace_console_macos.yml")
        if macos_path.exists():
            macos_text = macos_path.read_text()
            launchagents_task = (
                "- name: Ensure macOS LaunchAgents directory exists\n"
                "  ansible.builtin.file:\n"
                "    path: \"{{ ansible_env.HOME }}/Library/LaunchAgents\"\n"
                "    state: directory\n"
                "    mode: \"0755\"\n\n"
            )
            if "Ensure macOS LaunchAgents directory exists" not in macos_text:
                if macos_text.startswith("---\n"):
                    macos_text = "---\n" + launchagents_task + macos_text[4:]
                else:
                    macos_text = launchagents_task + macos_text
                macos_path.write_text(macos_text)

    patch_5()

    def patch_6():
        
        path = Path("roles/vhosts/gateway_openclaw/tasks/main.yml")
        if path.exists():
            text = path.read_text()
            
            download_old = (
                "- name: Download OpenClaw Multi-Session Plugins offline archive\n"
                "  ansible.builtin.get_url:\n"
                "    url: \"{{ gateway_openclaw_multi_session_plugin_archive_url }}\"\n"
                "    dest: \"/tmp/openclaw-multi-session-plugins.tar.gz\"\n"
                "    mode: \"0644\""
            )
            download_new = (
                "- name: Download OpenClaw Multi-Session Plugins offline archive\n"
                "  ansible.builtin.get_url:\n"
                "    url: \"{{ gateway_openclaw_multi_session_plugin_archive_url }}\"\n"
                "    dest: \"/tmp/openclaw-multi-session-plugins.tar.gz\"\n"
                "    mode: \"0644\"\n"
                "  when: ansible_os_family != 'Darwin'"
            )
            # Idempotency: download_new contains download_old as a prefix, so a
            # second pass over an already-patched tree would otherwise append a
            # second `when:` line (duplicate mapping key -> invalid YAML). Only
            # apply when the patched form is not already present.
            if download_old in text and download_new not in text:
                text = text.replace(download_old, download_new, 1)

            # NOTE: this block must match the upstream Extract task verbatim,
            # including the `creates:` line and the multi-item `notify:` list
            # (`Run OpenClaw doctor` + `Restart openclaw`). If it drifts from
            # upstream the substitution silently no-ops and the Darwin guard is
            # never added, so the task tries to unarchive a tarball that is never
            # downloaded on macOS and the OpenClaw step fails.
            extract_old = (
                "- name: Extract OpenClaw Multi-Session Plugins\n"
                "  ansible.builtin.unarchive:\n"
                "    src: \"/tmp/openclaw-multi-session-plugins.tar.gz\"\n"
                "    dest: \"{{ gateway_openclaw_home }}/.openclaw/extensions\"\n"
                "    remote_src: true\n"
                "    owner: \"{{ gateway_openclaw_service_user }}\"\n"
                "    group: \"{{ gateway_openclaw_service_group }}\"\n"
                "    mode: \"0755\"\n"
                "    creates: \"{{ gateway_openclaw_home }}/.openclaw/extensions/openclaw-multi-session-plugins\"\n"
                "  become: \"{{ ansible_os_family != 'Darwin' }}\"\n"
                "  notify:\n"
                "    - Run OpenClaw doctor\n"
                "    - Restart openclaw"
            )
            extract_new = extract_old + "\n  when: ansible_os_family != 'Darwin'"
            # Same idempotency guard as the download task above.
            if extract_old in text and extract_new not in text:
                text = text.replace(extract_old, extract_new, 1)
        
            anchor = "- name: Ensure OpenClaw global plugin npm directory exists"
            injected = (
                "- name: Check if openclaw-multi-session-plugins repo exists (macOS)\n"
                "  ansible.builtin.stat:\n"
                "    path: \"{{ gateway_openclaw_multi_session_plugin_dir | default('/tmp/openclaw-multi-session-plugins') }}/.git\"\n"
                "  register: openclaw_plugin_git_stat_macos\n"
                "  when: ansible_os_family == 'Darwin'\n"
                "\n"
                "- name: Clone openclaw-multi-session-plugins repository (macOS)\n"
                "  ansible.builtin.git:\n"
                "    repo: \"https://github.com/ai-workspace-lab/openclaw-multi-session-plugins.git\"\n"
                "    dest: \"{{ gateway_openclaw_multi_session_plugin_dir | default('/tmp/openclaw-multi-session-plugins') }}\"\n"
                "    version: main\n"
                "    depth: 1\n"
                "  become_user: \"{{ gateway_openclaw_service_user }}\"\n"
                "  when:\n"
                "    - ansible_os_family == 'Darwin'\n"
                "    - not (openclaw_plugin_git_stat_macos.stat.exists | default(false))\n"
                "\n"
                "- name: Build openclaw-multi-session-plugins (macOS)\n"
                "  ansible.builtin.shell: |\n"
                "    set -euo pipefail\n"
                "    cd \"{{ gateway_openclaw_multi_session_plugin_dir | default('/tmp/openclaw-multi-session-plugins') }}\"\n"
                "    npm install && npm run build\n"
                "  args:\n"
                "    executable: /bin/bash\n"
                "  become_user: \"{{ gateway_openclaw_service_user }}\"\n"
                "  when: ansible_os_family == 'Darwin'\n"
                "\n"
                "- name: Inspect installed openclaw-multi-session-plugins path (macOS)\n"
                "  ansible.builtin.stat:\n"
                "    path: \"{{ gateway_openclaw_home }}/.openclaw/extensions/openclaw-multi-session-plugins\"\n"
                "    follow: false\n"
                "  register: openclaw_plugin_extension_stat_macos\n"
                "  when: ansible_os_family == 'Darwin'\n"
                "\n"
                "- name: Remove legacy temporary plugin symlink (macOS)\n"
                "  ansible.builtin.file:\n"
                "    path: \"{{ gateway_openclaw_home }}/.openclaw/extensions/openclaw-multi-session-plugins\"\n"
                "    state: absent\n"
                "  when:\n"
                "    - ansible_os_family == 'Darwin'\n"
                "    - openclaw_plugin_extension_stat_macos.stat.islnk | default(false)\n"
                "  notify: Restart openclaw\n"
                "\n"
                "- name: Ensure stable openclaw-multi-session-plugins directory (macOS)\n"
                "  ansible.builtin.file:\n"
                "    path: \"{{ gateway_openclaw_home }}/.openclaw/extensions/openclaw-multi-session-plugins\"\n"
                "    state: directory\n"
                "    owner: \"{{ gateway_openclaw_service_user }}\"\n"
                "    group: \"{{ gateway_openclaw_service_group }}\"\n"
                "    mode: \"0755\"\n"
                "  when: ansible_os_family == 'Darwin'\n"
                "  notify: Restart openclaw\n"
                "\n"
                "- name: Copy built openclaw-multi-session-plugins into stable directory (macOS)\n"
                "  ansible.builtin.copy:\n"
                "    src: \"{{ gateway_openclaw_multi_session_plugin_dir | default('/tmp/openclaw-multi-session-plugins') }}/{{ item }}\"\n"
                "    dest: \"{{ gateway_openclaw_home }}/.openclaw/extensions/openclaw-multi-session-plugins/\"\n"
                "    remote_src: true\n"
                "    owner: \"{{ gateway_openclaw_service_user }}\"\n"
                "    group: \"{{ gateway_openclaw_service_group }}\"\n"
                "    mode: preserve\n"
                "  loop:\n"
                "    - dist\n"
                "    - openclaw.plugin.json\n"
                "    - package.json\n"
                "  become_user: \"{{ gateway_openclaw_service_user }}\"\n"
                "  when: ansible_os_family == 'Darwin'\n"
                "  notify: Restart openclaw\n"
                "\n"
                "- name: Record stable openclaw-multi-session-plugins install (macOS)\n"
                "  ansible.builtin.command:\n"
                "    cmd: >-\n"
                "      {{ gateway_openclaw_binary_path }} plugins install\n"
                "      {{ (gateway_openclaw_home ~ '/.openclaw/extensions/openclaw-multi-session-plugins') | quote }} --force\n"
                "  environment:\n"
                "    HOME: \"{{ gateway_openclaw_home }}\"\n"
                "    PATH: \"{{ gateway_openclaw_service_path }}\"\n"
                "    OPENCLAW_NO_RESPAWN: \"1\"\n"
                "  become_user: \"{{ gateway_openclaw_service_user }}\"\n"
                "  changed_when: false\n"
                "  when: ansible_os_family == 'Darwin'\n"
                "\n"
            )
            if anchor in text and "Clone openclaw-multi-session-plugins repository (macOS)" not in text:
                text = text.replace(anchor, injected + anchor, 1)
        
            path.write_text(text)

    patch_6()

    def patch_7():
        
        postgres_tasks = Path("roles/vhosts/postgres/tasks/main.yml")
        if postgres_tasks.exists():
            text = postgres_tasks.read_text()
            if "postgresql_deploy_mode_effective" not in text:
                text = text.replace(
                    "- name: Validate PostgreSQL deploy mode\n"
                    "  ansible.builtin.assert:\n"
                    "    that:\n"
                    "      - postgresql_deploy_mode in ['compose', 'native', 'external']\n"
                    "    fail_msg: \"postgresql_deploy_mode must be 'compose', 'native', or 'external'.\"\n",
                    "- name: Normalize PostgreSQL deploy mode\n"
                    "  ansible.builtin.set_fact:\n"
                    "    postgresql_deploy_mode_effective: >-\n"
                    "      {{ 'native' if (postgresql_deploy_mode | default('native')) == 'standalone' else (postgresql_deploy_mode | default('native')) }}\n\n"
                    "- name: Validate PostgreSQL deploy mode\n"
                    "  ansible.builtin.assert:\n"
                    "    that:\n"
                    "      - postgresql_deploy_mode_effective in ['compose', 'native', 'external']\n"
                    "    fail_msg: \"postgresql_deploy_mode must be 'compose', 'native', or 'external'.\"\n",
                    1,
                )
                text = text.replace(
                    "  when: postgresql_deploy_mode == 'external'\n",
                    "  when: postgresql_deploy_mode_effective == 'external'\n",
                )
                text = text.replace(
                    "  when: postgresql_deploy_mode == 'compose'\n",
                    "  when: postgresql_deploy_mode_effective == 'compose'\n",
                )
                text = text.replace(
                    "    - postgresql_deploy_mode == 'native'\n",
                    "    - postgresql_deploy_mode_effective == 'native'\n",
                )
                postgres_tasks.write_text(text)

        db_users = Path("create_databases_and_users.yml")
        if db_users.exists():
            text = db_users.read_text()
            if "postgresql_deploy_mode_effective" not in text:
                text = text.replace(
                    "    postgresql_deploy_mode: \"{{ lookup('env', 'POSTGRESQL_DEPLOY_MODE') | default('native', true) }}\"\n",
                    "    postgresql_deploy_mode: \"{{ lookup('env', 'POSTGRESQL_DEPLOY_MODE') | default('native', true) }}\"\n"
                    "    postgresql_deploy_mode_effective: >-\n"
                    "      {{ 'native' if (lookup('env', 'POSTGRESQL_DEPLOY_MODE') | default('native', true)) == 'standalone'\n"
                    "         else (lookup('env', 'POSTGRESQL_DEPLOY_MODE') | default('native', true)) }}\n",
                    1,
                )
                for old, new in [
                    ("      when: postgresql_deploy_mode == 'compose'\n", "      when: postgresql_deploy_mode_effective == 'compose'\n"),
                    ("      when: postgresql_deploy_mode != 'compose'\n", "      when: postgresql_deploy_mode_effective != 'compose'\n"),
                    ("      when: postgresql_deploy_mode == \"compose\" or (psql_check.rc | default(-1)) == 0\n", "      when: postgresql_deploy_mode_effective == \"compose\" or (psql_check.rc | default(-1)) == 0\n"),
                    ("          - postgresql_deploy_mode == 'compose'\n", "          - postgresql_deploy_mode_effective == 'compose'\n"),
                    ("          - postgresql_deploy_mode != 'compose'\n", "          - postgresql_deploy_mode_effective != 'compose'\n"),
                ]:
                    text = text.replace(old, new)
                db_users.write_text(text)

    patch_7()

    def patch_8():

        postgres_defaults = Path("roles/vhosts/postgres/defaults/main.yml")
        if postgres_defaults.exists():
            text = postgres_defaults.read_text()
            replacements = [
                (
                    "postgresql_compose_project_dir: /opt/ai-workspace/postgres\n",
                    "postgresql_compose_project_dir: >-\n"
                    "  {{ (ansible_env.HOME ~ '/.local/state/ai-workspace/postgres')\n"
                    "     if ansible_os_family == 'Darwin'\n"
                    "     else '/opt/ai-workspace/postgres' }}\n",
                ),
                (
                    "postgresql_admin_password_file: /root/.ai_workspace_postgres_password\n",
                    "postgresql_admin_password_file: >-\n"
                    "  {{ (ansible_env.HOME ~ '/.ai_workspace_postgres_password')\n"
                    "     if ansible_os_family == 'Darwin'\n"
                    "     else '/root/.ai_workspace_postgres_password' }}\n",
                ),
            ]
            updated = text
            for old, new in replacements:
                updated = updated.replace(old, new)
            if updated != text:
                postgres_defaults.write_text(updated)

        postgres_compose = Path("roles/vhosts/postgres/tasks/compose.yml")
        if postgres_compose.exists():
            text = postgres_compose.read_text()
            docker_runtime_old = (
                "- name: Ensure Docker runtime is installed for PostgreSQL compose mode\n"
                "  ansible.builtin.include_role:\n"
                "    name: roles/vhosts/docker\n"
                "  when: postgresql_docker_version.rc != 0\n"
            )
            docker_runtime_new = (
                "- name: Ensure Docker runtime is installed for PostgreSQL compose mode\n"
                "  ansible.builtin.include_role:\n"
                "    name: roles/vhosts/docker\n"
                "  when: postgresql_docker_version.rc != 0\n"
                "\n"
                "- name: Inspect Docker daemon for PostgreSQL compose mode\n"
                "  ansible.builtin.command: docker info\n"
                "  register: postgresql_docker_info\n"
                "  changed_when: false\n"
                "  failed_when: false\n"
                "\n"
                "- name: Start Colima Docker daemon for PostgreSQL compose mode (macOS)\n"
                "  ansible.builtin.command: colima start\n"
                "  register: postgresql_colima_start\n"
                "  changed_when: >-\n"
                "    'already running' not in (postgresql_colima_start.stdout | default(''))\n"
                "    and 'already running' not in (postgresql_colima_start.stderr | default(''))\n"
                "  when:\n"
                "    - ansible_os_family == 'Darwin'\n"
                "    - postgresql_docker_info.rc != 0\n"
                "\n"
                "- name: Wait for Docker daemon after Colima start (macOS)\n"
                "  ansible.builtin.command: docker info\n"
                "  register: postgresql_docker_info_after_colima\n"
                "  changed_when: false\n"
                "  retries: 12\n"
                "  delay: 5\n"
                "  until: postgresql_docker_info_after_colima.rc == 0\n"
                "  when:\n"
                "    - ansible_os_family == 'Darwin'\n"
                "    - postgresql_docker_info.rc != 0\n"
            )
            if "Start Colima Docker daemon for PostgreSQL compose mode" not in text and docker_runtime_old in text:
                text = text.replace(docker_runtime_old, docker_runtime_new, 1)
                postgres_compose.write_text(text)

            old = (
                "  ansible.builtin.file:\n"
                "    path: \"{{ postgresql_compose_project_dir }}\"\n"
                "    state: directory\n"
                "    owner: root\n"
                "    group: root\n"
                "    mode: \"0755\"\n"
            )
            new = (
                "  ansible.builtin.file:\n"
                "    path: \"{{ postgresql_compose_project_dir }}\"\n"
                "    state: directory\n"
                "    owner: \"{{ ansible_user_id if ansible_os_family == 'Darwin' else 'root' }}\"\n"
                "    group: \"{{ 'staff' if ansible_os_family == 'Darwin' else 'root' }}\"\n"
                "    mode: \"0755\"\n"
            )
            if old in text and new not in text:
                text = text.replace(old, new, 1)
                postgres_compose.write_text(text)

            data_old = (
                "  ansible.builtin.file:\n"
                "    path: \"{{ postgresql_data_dir }}\"\n"
                "    state: directory\n"
                "    owner: \"{{ postgresql_container_uid }}\"\n"
                "    group: \"{{ postgresql_container_gid }}\"\n"
                "    mode: \"0700\"\n"
            )
            data_new = (
                "  ansible.builtin.file:\n"
                "    path: \"{{ postgresql_data_dir }}\"\n"
                "    state: directory\n"
                "    owner: \"{{ ansible_user_id if ansible_os_family == 'Darwin' else postgresql_container_uid }}\"\n"
                "    group: \"{{ 'staff' if ansible_os_family == 'Darwin' else postgresql_container_gid }}\"\n"
                "    mode: \"{{ '0755' if ansible_os_family == 'Darwin' else '0700' }}\"\n"
            )
            if data_old in text and data_new not in text:
                text = text.replace(data_old, data_new, 1)
                postgres_compose.write_text(text)

            render_owner_replacements = [
                (
                    "    dest: \"{{ postgresql_compose_env_file }}\"\n"
                    "    owner: root\n"
                    "    group: root\n"
                    "    mode: \"0600\"\n",
                    "    dest: \"{{ postgresql_compose_env_file }}\"\n"
                    "    owner: \"{{ ansible_user_id if ansible_os_family == 'Darwin' else 'root' }}\"\n"
                    "    group: \"{{ 'staff' if ansible_os_family == 'Darwin' else 'root' }}\"\n"
                    "    mode: \"0600\"\n",
                ),
                (
                    "    dest: \"{{ postgresql_compose_file }}\"\n"
                    "    owner: root\n"
                    "    group: root\n"
                    "    mode: \"0644\"\n",
                    "    dest: \"{{ postgresql_compose_file }}\"\n"
                    "    owner: \"{{ ansible_user_id if ansible_os_family == 'Darwin' else 'root' }}\"\n"
                    "    group: \"{{ 'staff' if ansible_os_family == 'Darwin' else 'root' }}\"\n"
                    "    mode: \"0644\"\n",
                ),
            ]
            for render_old, render_new in render_owner_replacements:
                if render_old in text and render_new not in text:
                    text = text.replace(render_old, render_new, 1)
                    postgres_compose.write_text(text)

    patch_8()

if __name__ == '__main__':
    main()
