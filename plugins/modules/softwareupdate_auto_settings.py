#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ansible.module_utils.basic import AnsibleModule
import os
import platform
import subprocess

DOCUMENTATION = r'''
---
module: softwareupdate_auto_settings
short_description: Manage automatic macOS update settings.
description:
  - This module manages automatic macOS update settings using the `defaults` command.
    It allows enabling or disabling various automatic update options such as checking for updates, downloading, installing, etc.
version_added: "1.0.0"
author:
  - kostakoff
options:
  automatic_check_enabled:
    description:
      - Enable or disable automatic checking for updates.
    type: bool
    required: false
  automatic_download:
    description:
      - Enable or disable automatic downloading of updates.
    type: bool
    required: false
  automatically_install_macos_updates:
    description:
      - Enable or disable automatic installation of macOS updates.
    type: bool
    required: false
  config_data_install:
    description:
      - Enable or disable automatic installation of configuration data.
    type: bool
    required: false
  critical_update_install:
    description:
      - Enable or disable automatic installation of critical updates.
    type: bool
    required: false
  app_auto_update:
    description:
      - Enable or disable automatic app updates.
    type: bool
    required: false
'''

EXAMPLES = r'''
# Включить автоматическую проверку и загрузку обновлений
- name: Enable automatic check and download of updates
  softwareupdate_auto_settings:
    automatic_check_enabled: true
    automatic_download: true

# Отключить автоматическую установку обновлений macOS
- name: Disable automatic installation of macOS updates
  softwareupdate_auto_settings:
    automatically_install_macos_updates: false

# Включить автоматическое обновление приложений
- name: Enable automatic app updates
  softwareupdate_auto_settings:
    app_auto_update: true

# Пример использования в playbook
- name: Manage automatic macOS update settings
  hosts: localhost
  become: yes
  gather_facts: no
  tasks:
    - name: Enable automatic check and download of updates
      softwareupdate_auto_settings:
        automatic_check_enabled: true
        automatic_download: true
      register: check_download_result

    - name: Display the result of enabling check and download
      debug:
        var: check_download_result

    - name: Disable automatic installation of macOS updates
      softwareupdate_auto_settings:
        automatically_install_macos_updates: false
      register: disable_install_result

    - name: Display the result of disabling installation
      debug:
        var: disable_install_result

    - name: Enable automatic app updates
      softwareupdate_auto_settings:
        app_auto_update: true
      register: app_update_result

    - name: Display the result of enabling app updates
      debug:
        var: app_update_result
'''

RETURN = r'''
changed:
  description: Indicates if any changes were made by the module.
  type: bool
  returned: always
msg:
  description: A message indicating the result of the module execution.
  type: str
  returned: always
softwareupdate_plist:
  description: Output of the `plutil -p` command for the SoftwareUpdate preferences plist.
  type: str
  returned: always
macos_version:
  description: The major version of macOS on which the module was executed.
  type: int
  returned: always
'''

def get_macos_major_version():
    """
    Retrieves the major version of macOS.
    Returns an integer if the version is determined, otherwise None.
    """
    version_str = platform.mac_ver()[0]
    if version_str:
        try:
            return int(version_str.split('.')[0])
        except ValueError:
            return None
    return None

def read_default(domain, key):
    """Читает значение ключа из defaults, возвращает True/False или None, если ключ отсутствует."""
    try:
        output = subprocess.check_output(
            ["defaults", "read", domain, key],
            stderr=subprocess.STDOUT,
            universal_newlines=True
        ).strip()
        if output == '1':
            return True
        elif output == '0':
            return False
        return None
    except subprocess.CalledProcessError:
        return None

def write_default(domain, key, value_bool, check_mode=False):
    """
    Записывает значение ключа в defaults, если check_mode=False.
    Возвращает True, если значение действительно было бы изменено, иначе False.
    """
    current_value = read_default(domain, key)
    if current_value == value_bool:
        return False  # уже в нужном состоянии
    if not check_mode:
        bool_str = "true" if value_bool else "false"
        subprocess.check_call(
            ["defaults", "write", domain, key, "-bool", bool_str],
            stderr=subprocess.STDOUT
        )
    return True

def plutil_print(path):
    """
    Возвращает вывод plutil -p <path> или None, если файл не существует или ошибка.
    """
    if not os.path.exists(path):
        return None
    try:
        output = subprocess.check_output(
            ["plutil", "-p", path],
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        return output.strip()
    except subprocess.CalledProcessError as e:
        return f"Error reading {path}: {str(e)}"

def main():
    module_args = dict(
        automatic_check_enabled=dict(type='bool', required=False),
        automatic_download=dict(type='bool', required=False),
        automatically_install_macos_updates=dict(type='bool', required=False),
        config_data_install=dict(type='bool', required=False),
        critical_update_install=dict(type='bool', required=False),
        app_auto_update=dict(type='bool', required=False)
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    # Проверяем ОС
    if platform.system() != "Darwin":
        module.fail_json(msg="This module can only run on macOS (Darwin). Current OS: {}".format(platform.system()))

    # Проверяем root
    if os.geteuid() != 0:
        module.fail_json(msg="This module must be run as root (become: true). Current UID: {}".format(os.geteuid()))

    # Get the major version of macOS
    major_version = get_macos_major_version()
    if major_version is None:
        module.fail_json(msg="Failed to determine the macOS version.")
    
    # Verify that the major version is supported
    if major_version not in [13, 14, 15]:
        module.fail_json(msg="This module supports only macOS major versions 13, 14, or 15. Current version: {}".format(major_version))

    check_mode = module.check_mode
    changed = False

    SWU_DOMAIN = "/Library/Preferences/com.apple.SoftwareUpdate"
    COMMERCE_DOMAIN = "/Library/Preferences/com.apple.commerce"

    changes = []

    if module.params['automatic_check_enabled'] is not None:
        changes.append((SWU_DOMAIN, "AutomaticCheckEnabled", module.params['automatic_check_enabled']))
    if module.params['automatic_download'] is not None:
        changes.append((SWU_DOMAIN, "AutomaticDownload", module.params['automatic_download']))
    if module.params['automatically_install_macos_updates'] is not None:
        changes.append((SWU_DOMAIN, "AutomaticallyInstallMacOSUpdates", module.params['automatically_install_macos_updates']))
    if module.params['config_data_install'] is not None:
        changes.append((SWU_DOMAIN, "ConfigDataInstall", module.params['config_data_install']))
    if module.params['critical_update_install'] is not None:
        changes.append((SWU_DOMAIN, "CriticalUpdateInstall", module.params['critical_update_install']))

    if module.params['app_auto_update'] is not None:
        changes.append((COMMERCE_DOMAIN, "AutoUpdate", module.params['app_auto_update']))

    for domain, key, value in changes:
        try:
            if write_default(domain, key, value, check_mode=check_mode):
                changed = True
        except subprocess.CalledProcessError as e:
            module.fail_json(msg="Failed to set {} in {}: {}".format(key, domain, str(e)))

    # Читаем итоговое состояние plist-файлов
    swu_plist = plutil_print("/Library/Preferences/com.apple.SoftwareUpdate.plist")

    module.exit_json(
        changed=changed, 
        msg="Automatic update settings have been managed successfully.",
        softwareupdate_plist=swu_plist,
        macos_version=major_version
    )

if __name__ == '__main__':
    main()
