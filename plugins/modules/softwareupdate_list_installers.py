#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ansible.module_utils.basic import AnsibleModule
import subprocess
import re
import platform

DOCUMENTATION = r'''
---
module: softwareupdate_list_installers
short_description: Retrieve a list of available macOS installers.
description:
  - This module retrieves a list of available macOS installers using the `softwareupdate` command.
    It supports filtering to return only the latest versions for each major macOS version.
version_added: "1.0.0"
author:
  - kostakoff
options:
  latest_only:
    description:
      - When set to true, the module returns only the latest installer for each major macOS version.
      - If false, it returns the full list of available installers.
    type: bool
    required: false
    default: false
  version_pattern:
    description:
      - A regex pattern to filter updates by their version.
      - Only updates matching this pattern will be returned.
    type: str
    required: false
    default: null
'''

EXAMPLES = r'''
# Получить полный список доступных установщиков macOS
- name: Retrieve full list of macOS installers
  softwareupdate_list_installers:

# Получить только последние версии установщиков для каждой мажорной версии macOS
- name: Retrieve only the latest installers for each macOS major version
  softwareupdate_list_installers:
    latest_only: true

# Пример использования в задачах Ansible
- name: Get the latest macOS installers
  hosts: localhost
  gather_facts: no
  tasks:
    - name: Retrieve latest installers
      softwareupdate_list_installers:
        latest_only: true
      register: result

    - name: Display the latest installers
      debug:
        var: result
'''

RETURN = r'''
changed:
  description: Indicates if any changes were made by the module.
  type: bool
  returned: always
installers:
  description: A list of available macOS installers.
  type: list
  returned: always
  elements: dict
  contains:
    title:
      description: The name of the macOS installer.
      type: str
    version:
      description: The version number of the macOS installer.
      type: str
    size_kib:
      description: The size of the installer in KiB.
      type: int
    build:
      description: The build identifier of the macOS installer.
      type: str
    deferred:
      description: Indicates if the installer download is deferred.
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

def parse_version(version_str):
    """
    Преобразует строку версии в кортеж чисел для корректной сортировки.
    Пример: "15.1.1" -> (15, 1, 1)
    """
    return tuple(int(part) for part in version_str.split('.') if part.isdigit())

def main():
    module_args = dict(
        latest_only=dict(type='bool', required=False, default=False),
        version_pattern=dict(type='str', required=False, default=None)
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    # Проверяем, что ОС — macOS (Darwin)
    if platform.system() != "Darwin":
        module.fail_json(msg="This module can only run on macOS (Darwin). Current OS: {}".format(platform.system()))

    # Получаем мажорную версию macOS
    major_version = get_macos_major_version()
    if major_version is None:
        module.fail_json(msg="Failed to determine the macOS version.")

    # Проверяем, что мажорная версия входит в допустимые значения
    if major_version not in [13, 14, 15]:
        module.fail_json(msg="This module supports only macOS major versions 13, 14, or 15. Current version: {}".format(major_version), macos_version=major_version)

    # Получаем значение параметра 'latest_only'
    latest_only = module.params.get('latest_only')
    version_pattern = module.params['version_pattern']
    version_regex = None

    if version_pattern:
        try:
            version_regex = re.compile(version_pattern)
        except re.error as e:
            module.fail_json(msg="Invalid version_pattern regex: {}".format(str(e)))
    
    if module.check_mode:
        # В check_mode не делаем изменений
        module.exit_json(changed=False, msg="Check mode: no changes.", macos_version=major_version)

    # Запускаем команду softwareupdate
    try:
        cmd_output = subprocess.check_output(
            ["softwareupdate", "--list-full-installers"],
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
    except subprocess.CalledProcessError as e:
        module.fail_json(msg="Failed to run softwareupdate: {}".format(e.output), macos_version=major_version)

    # Паттерн для парсинга списка установщиков
    pattern = re.compile(
        r"^\* Title:\s+(.*?), Version:\s+(.*?), Size:\s+(.*?), Build:\s+(\S+), Deferred:\s+(.*)$"
    )

    installers = []
    for line in cmd_output.splitlines():
        line = line.strip()
        if line.startswith("* Title:"):
            match = pattern.match(line)
            if match:
                title = match.group(1).strip()
                version = match.group(2).strip()
                size_str = match.group(3).strip()
                build = match.group(4).strip()
                deferred = match.group(5).strip()

                # Применяем фильтр по версии, если указан
                if version_regex and not version_regex.match(version):
                    continue

                installers.append({
                    "title": title,
                    "version": version,
                    "size": size_str,
                    "build": build,
                    "deferred": deferred
                })

    if latest_only:
        # Группируем установщики по мажорной версии и выбираем последнюю версию для каждой группы
        latest_installers = {}
        for installer in installers:
            # Извлекаем мажорную версию из полной версии
            major_ver = installer['version'].split('.')[0]
            try:
                major_ver_int = int(major_ver)
            except ValueError:
                continue  # Пропускаем, если мажорная версия не число

            # Если мажорная версия уже в словаре, сравниваем версии
            if major_ver_int in latest_installers:
                current_latest = latest_installers[major_ver_int]
                if parse_version(installer['version']) > parse_version(current_latest['version']):
                    latest_installers[major_ver_int] = installer
            else:
                latest_installers[major_ver_int] = installer

        # Преобразуем словарь в список и сортируем по мажорной версии в порядке убывания
        installers = sorted(
            latest_installers.values(),
            key=lambda x: int(x['version'].split('.')[0]),
            reverse=True
        )

    else:
        # Сортируем полный список установщиков по версии в порядке убывания
        installers = sorted(
            installers,
            key=lambda x: parse_version(x['version']),
            reverse=True
        )

    module.exit_json(
        changed=False,
        installers=installers,
        macos_version=major_version,
        msg="Installers listed successfully."
    )


if __name__ == '__main__':
    main()
