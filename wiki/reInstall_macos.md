# Ansible Modules for Managing macOS Updates through reistallation

This set of Ansible modules provides automation for controlling macOS updates and installation on remote hosts. They enable you to:

1. **Disable Automatic Updates** (using `softwareupdate_auto_settings`):
   - A helper module (not extensively documented here) that simply enables or disables all automatic updates in macOS. In our use case, we disable them to ensure manual control via Ansible, preventing macOS from self-updating automatically.

2. **Download the Full macOS Installer** (`softwareupdate_download_osapp`):
   - Uses the `softwareupdate --fetch-full-installer` command to download a specific full macOS installer of a desired version.
   - After completion, an installer application directory should appear under `/Applications` (e.g., `Install macOS Sonoma.app`).

3. **Start macOS Installation** (`softwareupdate_osinstall`):
   - Initiates the macOS installation process using the `startosinstall` tool from the previously downloaded installer.
   - Runs the installation in the background, allowing the machine to reboot automatically to complete the installation process.

## Why Use These Modules?

By default, macOS manages updates automatically. However, you may need controlled, predictable updates in an environment with numerous macOS hosts. These modules let you:

- Prevent automatic, unsolicited updates from macOS itself.
- Precisely control which macOS version to download and when.
- Integrate macOS updating and upgrading into your existing Ansible workflows, CI/CD pipelines, or IT orchestration tools.

## Prerequisites

- Ansible and SSH access to the target macOS machines.
- `become: true` (root privileges) to run the tasks.
- Supported macOS major versions: 13 (Ventura), 14 (Sonoma), and 15 (Sequoia). This is due to differences in the `softwareupdate` behavior and installation commands.
- Ensure `softwareupdate` and `startosinstall` are available on the target macOS machine.

## Example Playbook

The following playbook demonstrates:

1. Disabling all automatic updates (`softwareupdate_auto_settings`).
2. Listing available macOS installer versions (using `softwareupdate_list_installers`—assumed to be available).
3. Downloading a specific full installer (`softwareupdate_download_osapp`).
4. Starting the macOS installation process (`softwareupdate_osinstall`).

```yaml
macmachines:
  hosts:
    macos-vm1:
      ansible_host: 192.168.0.61
      ansible_user: admin

  vars:
    ansible_python_interpreter: /opt/homebrew/bin/python3
---
- hosts: macmachines
  gather_facts: false
  become: true

  tasks:
    # 1. Disable all automatic updates
    - name: Disable all automatic updates
      softwareupdate_auto_settings:
        automatic_check_enabled: false
        automatic_download: false
        automatically_install_macos_updates: false
        config_data_install: false
        critical_update_install: false
        app_auto_update: false

    # 2. List available macOS installers
    - name: List macOS installers
      softwareupdate_list_installers:
        latest_only: true
        version_pattern: '^14\.'
      register: installers_result

    - debug:
        var: installers_result.installers

    # 3. Download a specific macOS installer (e.g., 14.x version)
    - name: Download a specific macOS installer by version
      softwareupdate_download_osapp:
        macos_version: "{{ installers_result.installers[0].version }}"
      register: download_result

    - debug:
        var: download_result

    # 4. Start the macOS installation from the full installer
    - name: Install macOS from full installer
      softwareupdate_osinstall:
        version: 14
        username: "admin"
        password: "admin"
```

## What Happens Here?
- Disable all automatic updates: Ensures that macOS won't update itself, leaving Ansible in full control.
- List macOS installers: Gets a list of available macOS installers that can be fetched.
- Download a specific macOS installer: Fetches the chosen full installer (e.g., Sonoma 14.7.2). Once complete, you should see /Applications/Install macOS Sonoma.app.
- Install macOS from full installer: Initiates the OS upgrade process. The machine will reboot and proceed with the installation.
