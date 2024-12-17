#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ansible.module_utils.basic import AnsibleModule
import subprocess
import platform
import re

DOCUMENTATION = r'''
---
module: softwareupdate_list_updates
short_description: Retrieve a list of available macOS updates.
description:
  - This module retrieves a list of available macOS updates using the `softwareupdate` command.
    It supports filtering by product type and version pattern.
version_added: "1.0.1"
author:
  - kostakoff
options:
  product:
    description:
      - Specifies the type of product updates to retrieve.
      - Can be set to `all` to retrieve all updates or to a specific product type.
    type: str
    required: false
    default: all
    choices:
      - all
      - macos
      - xcode
      - command_line_tools
      - safari
      - security
      - firmware
      - printer_drivers
  version_pattern:
    description:
      - A regex pattern to filter updates by their version.
      - Only updates matching this pattern will be returned.
    type: str
    required: false
    default: null
'''

EXAMPLES = r'''
# Получить все доступные обновления
- name: Retrieve all available macOS updates
  softwareupdate_list_updates:

# Получить только обновления для macOS
- name: Retrieve only macOS updates
  softwareupdate_list_updates:
    product: macos

# Получить обновления для macOS с версией 14
- name: Retrieve Xcode updates version 14
  softwareupdate_list_updates:
    product: macos
    version_pattern: '^14\.'

# Пример использования в задачах Ansible
- name: Получить обновления macOS и Xcode с определёнными версиями
  hosts: localhost
  gather_facts: no
  tasks:
    - name: Retrieve macOS updates
      softwareupdate_list_updates:
        product: macos
      register: macos_updates

    - name: Retrieve Xcode updates version 16
      softwareupdate_list_updates:
        product: xcode
        version_pattern: '^16\.'
      register: xcode_updates

    - name: Вывести macOS обновления
      debug:
        var: macos_updates

    - name: Вывести Xcode обновления
      debug:
        var: xcode_updates
'''

RETURN = r'''
changed:
  description: Indicates if any changes were made by the module.
  type: bool
  returned: always
updates:
  description: A list of available macOS updates.
  type: list
  returned: always
  elements: dict
  contains:
    label:
      description: The label identifier of the update.
      type: str
    title:
      description: The title of the update.
      type: str
    version:
      description: The version number of the update.
      type: str
    size_kib:
      description: The size of the update in KiB.
      type: int
    recommended:
      description: Indicates if the update is recommended.
      type: str
    action:
      description: The required action for the update (e.g., restart).
      type: str
macos_version:
  description: The major version of macOS on which the module was executed.
  type: int
  returned: always
msg:
  description: A message indicating the result of the module execution.
  type: str
  returned: always
'''

def get_macos_major_version():
    """
    Получает мажорную версию macOS.
    Возвращает целое число, если версия определена, иначе None.
    """
    version_str = platform.mac_ver()[0]
    if version_str:
        try:
            return int(version_str.split('.')[0])
        except ValueError:
            return None
    return None

def main():
    module_args = dict(
        product=dict(
            type='str', 
            required=False, 
            default='all', 
            choices=[
                'all', 
                'macos', 
                'xcode', 
                'command_line_tools', 
                'safari', 
                'security', 
                'firmware',
                'printer_drivers'
            ]
        ),
        version_pattern=dict(type='str', required=False, default=None)
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    # Проверяем ОС
    if platform.system() != "Darwin":
        module.fail_json(msg="This module can only run on macOS (Darwin). Current OS: {}".format(platform.system()))

    # Получаем мажорную версию macOS
    major_version = get_macos_major_version()
    if major_version is None:
        module.fail_json(msg="Failed to determine the macOS version.")
    
    # Проверяем, что мажорная версия входит в допустимые значения
    if major_version not in [13, 14, 15]:
        module.fail_json(msg="This module supports only macOS major versions 13, 14, or 15. Current version: {}".format(major_version))

    product_filter = module.params['product']
    version_pattern = module.params['version_pattern']
    version_regex = None

    if version_pattern:
        try:
            version_regex = re.compile(version_pattern)
        except re.error as e:
            module.fail_json(msg="Invalid version_pattern regex: {}".format(str(e)))

    if module.check_mode:
        module.exit_json(changed=False, updates=[], msg="Check mode: no changes.")

    # Запускаем команду softwareupdate --list
    try:
        cmd_output = subprocess.check_output(
            ["softwareupdate", "--list"],
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
    except subprocess.CalledProcessError as e:
        module.fail_json(msg="Failed to run softwareupdate: {}".format(e.output), macos_version=major_version)

    # Определяем логику фильтрации по продуктам
    PRODUCT_PATTERNS = {
        'all': lambda t: True,
        'macos': lambda t: t.startswith('macOS'),
        'xcode': lambda t: t.startswith('Xcode ') or t.startswith('Xcode-'),
        'command_line_tools': lambda t: t.startswith('Command Line Tools'),
        'safari': lambda t: t.startswith('Safari'),
        'security': lambda t: t.startswith('Security Update'),
        'firmware': lambda t: 'Firmware Update' in t,
        'printer_drivers': lambda t: 'Printer Drivers' in t,
    }

    lines = cmd_output.splitlines()
    updates = []

    label_pattern = re.compile(r"^\* Label:\s+(.*)$")
    # Пример:
    # Title: macOS Sonoma 14.7.1, Version: 14.7.1, Size: 2387500KiB, Recommended: YES, Action: restart,
    title_pattern = re.compile(
        r"^\s*Title:\s+(.*?),\s*Version:\s+(.*?),\s*Size:\s+(.*?),\s*Recommended:\s+(YES|NO)(?:,\s*Action:\s*(\S+))?,?$"
    )

    current_label = None

    for line in lines:
        line = line.strip()
        if line.startswith("* Label:"):
            m = label_pattern.match(line)
            if m:
                current_label = m.group(1).strip()
        elif line.startswith("Title:") and current_label:
            m = title_pattern.match(line)
            if m:
                title_str = m.group(1).strip()
                version = m.group(2).strip()
                size_str = m.group(3).strip()
                recommended = m.group(4).strip()
                action = m.group(5) if m.group(5) else None

                # Применяем фильтр по продукту
                if not PRODUCT_PATTERNS[product_filter](title_str):
                    current_label = None
                    continue

                # Применяем фильтр по версии, если указан
                if version_regex and not version_regex.match(version):
                    current_label = None
                    continue

                # Если прошли все фильтры, добавляем обновление
                updates.append({
                    "label": current_label,
                    "title": title_str,
                    "version": version,
                    "size": size_str,
                    "recommended": recommended,
                    "action": action
                })

                current_label = None

    module.exit_json(
        changed=False,
        updates=updates,
        macos_version=major_version,
        msg="Updates listed successfully"
    )

if __name__ == '__main__':
    main()
