# macos.softwareupdate ansible module

## Use cases
- In case if we wanna have automation update minor MacOS verison
- In case if we wanna have full controll for MacOS verison without MDM solutions

## How to install
```bash
ansible-galaxy collection install git+git@github.com:kostakoff/macos.softwareupdate.git,main --upgrade
```

## Ansible configuration example

- hosts yaml
```yaml
macmachines:
  hosts:
    macos-vm1:
      ansible_host: 192.168.0.60
      ansible_user: admin

  vars:
    ansible_python_interpreter: /opt/homebrew/bin/python3
```
- playbook yaml
```yaml
- hosts: macmachines
  gather_facts: false
  become: true
  tasks:
    - name: Disable all automatic updates # because we wanna manage it manually
      become: true
      macos.softwareupdate.softwareupdate_auto_settings:
        automatic_check_enabled: false
        automatic_download: false
        automatically_install_macos_updates: false
        config_data_install: false
        critical_update_install: false
        app_auto_update: false

    - name: List macOS installers
      macos.softwareupdate.softwareupdate_list_installers:
      register: list_result

    - debug:
        var: list_result.installers

    - name: List available updates filtered by product (macOS)
      macos.softwareupdate.softwareupdate_list_updates:
        product: macos
        version_pattern: '^14\.' # we wanna keep major version of MacOS 14 with latest updates
      register: updates_result

    - debug:
        var: updates_result

    - name: Install a specific macOS update by label
      become: true
      macos.softwareupdate.softwareupdate_install:
        label: "{{ updates_result.updates[0].label }}" # set specific updates
        username: "admin"
        password: "newlife"
      register: install_result
      when: updates_result.updates is defined and updates_result.updates | length > 0

    - debug:
        var: install_result
      when: updates_result.updates is defined and updates_result.updates | length > 0
    # congratulations MacOS updates been successfully started in background
```
