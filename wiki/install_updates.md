# Using Ansible Modules to Manage Incremental macOS Updates

This guide describes how to use two Ansible modules, `softwareupdate_list_updates` and `softwareupdate_install`, to manage incremental (patch) macOS updates. Unlike the modules that fetch and install the full macOS installer, these modules allow you to query and apply incremental updates—such as system patches and security updates—directly from Apple’s servers using the `softwareupdate` command-line tool.

## Overview

1. **`softwareupdate_list_updates` Module**:
   - Lists available incremental updates (e.g., minor OS patches, security fixes, Safari updates).
   - Can filter updates by product type (e.g., macOS, Safari, security, etc.).
   - Can filter updates by a version pattern (regex) to focus on specific versions (e.g., only macOS 14.x updates).
   - Returns a structured list of available updates including details such as label, title, version, and recommended status.

2. **`softwareupdate_install` Module**:
   - Installs one of the listed incremental updates by specifying its `label`.
   - Runs in the background so the installation can proceed without blocking Ansible.
   - Requires credentials (username and password) if the update requires agreement or admin privileges.
   - Works only on macOS and is compatible with major macOS versions 13, 14, and 15 (Ventura, Sonoma, Sequoia).

## Why Use These Modules Together?

- **`softwareupdate_list_updates`** helps you discover which incremental updates are available before you proceed. For example, you might first check what macOS updates are available for version 14.x.
- Once you know which updates you want to apply, **`softwareupdate_install`** takes the `label` of a specific update and initiates the installation process.
- Running them together in a playbook enables a controlled, step-by-step update process—useful for CI/CD pipelines, large-scale fleet management, or any scenario where you need predictable, automated macOS patching.

## Prerequisites

- Ansible and SSH access to the macOS host.
- The host must be running a supported macOS version (13, 14, or 15).
- `become: true` is required because applying updates typically requires administrator privileges.
- Ensure that automatic updates are disabled if you want full manual control (see `softwareupdate_auto_settings`).

## Example Playbook

The following example demonstrates how to:

1. Disable automatic updates using a helper module (`softwareupdate_auto_settings`).
2. List available macOS incremental updates using `softwareupdate_list_updates`, filtering by product type (`macos`) and version pattern (`'^14\.'`), focusing on macOS 14.x updates.
3. Install a specific incremental update using `softwareupdate_install`.

```yaml
macmachines:
  hosts:
    macos-vm1:
      ansible_host: 192.168.0.60
      ansible_user: admin

  vars:
    ansible_python_interpreter: /opt/homebrew/bin/python3
---
- hosts: macmachines
  gather_facts: false
  become: true

  tasks:
    # 1. Disable automatic updates so we have manual control over the update process
    - name: Disable all automatic updates
      macos.softwareupdate.softwareupdate_auto_settings:
        automatic_check_enabled: false
        automatic_download: false
        automatically_install_macos_updates: false
        config_data_install: false
        critical_update_install: false
        app_auto_update: false

    # 2. List available incremental macOS updates (major version 14.x)
    - name: List available updates filtered by product (macOS)
      macos.softwareupdate.softwareupdate_list_updates:
        product: macos
        version_pattern: '^14\.'
      register: updates_result

    - debug:
        var: updates_result

    # 3. Install a specific macOS update by label
    - name: Install a specific macOS update by label
      macos.softwareupdate.softwareupdate_install:
        label: "{{ updates_result.updates[0].label }}"
        username: "admin"
        password: "admin"
      register: install_result
      when: updates_result.updates is defined and updates_result.updates | length > 0

    - debug:
        var: install_result
      when: updates_result.updates is defined and updates_result.updates | length > 0
```
## What Happens in This Playbook?
- Disable all automatic updates: Ensures the system doesn't self-update, giving Ansible complete authority.
- List available updates: Shows which incremental updates are available for macOS 14.x. You'll see labels and titles of each update.
- Install chosen update: Installs the first listed update (or any you select by label) in the background. The machine might require a restart if the update demands it.
