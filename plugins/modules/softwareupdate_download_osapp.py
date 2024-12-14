#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ansible.module_utils.basic import AnsibleModule
import os
import platform
import subprocess

DOCUMENTATION = r'''
---
module: softwareupdate_download_osapp
short_description: Download full macOS installer using `softwareupdate`
description:
  - This module uses the `softwareupdate` command to fetch a full macOS installer.
  - After downloading, it verifies that the expected installer application directory 
    appears in `/Applications`.
options:
  version:
    description:
      - The full macOS version string to fetch (e.g., "14.7.2").
    required: true
    type: str
author:
  - kostakoff
requirements:
  - macOS with appropriate `softwareupdate` tool available.
'''

EXAMPLES = r'''
- name: Download full macOS installer for version 14.7.2
  softwareupdate_download_osapp:
    macos_version: "14.7.2"
'''

RETURN = r'''
macos_version:
  description: The major version of the current macOS.
  returned: always
  type: int
  sample: 14
msg:
  description: A message describing the result of the module's operation.
  returned: always
  type: str
  sample: "Successfully fetched full installer '14.7.2', located at '/Applications/Install macOS Sonoma.app'."
changed:
  description: Indicates if any changes were made (i.e., if the installer was successfully fetched).
  returned: always
  type: bool
'''

INSTALLERS = {
    13: "Install macOS Ventura.app",
    14: "Install macOS Sonoma.app",
    15: "Install macOS 15.app"
}

def get_macos_major_version():
    """
    Retrieves the major version of macOS (the currently running OS).
    Returns an integer if determined, otherwise None.
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
        version=dict(type='str', required=True),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False
    )

    # Проверяем, что мы на macOS
    if platform.system() != "Darwin":
        module.fail_json(msg="This module can only run on macOS (Darwin). Current OS: {}".format(platform.system()))

    # Текущая версия macOS хоста (выполняющего playbook)
    host_major_version = get_macos_major_version()
    if host_major_version is None:
        module.fail_json(msg="Failed to determine the macOS version of the host.")

    # Проверяем что текущая мажорная версия поддерживается
    if host_major_version not in INSTALLERS.keys():
        module.fail_json(msg="This module supports only macOS major versions {}. Current version: {}".format(
            list(INSTALLERS.keys()), host_major_version))

    desired_version = module.params['version']
    # Получим мажорную версию из желаемой версии (например, "14.7.2" -> 14)
    try:
        desired_major_version = int(desired_version.split('.')[0])
    except ValueError:
        module.fail_json(msg="Invalid macos version format '{}'. Could not extract major version.".format(desired_version))

    # Проверим, есть ли нужный нам инсталлер в словаре
    if desired_major_version not in INSTALLERS:
        module.fail_json(msg="No installer mapping found for desired macOS major version {}".format(desired_major_version))

    expected_app = INSTALLERS[desired_major_version]
    expected_path = os.path.join("/Applications", expected_app)

    cmd = ["softwareupdate", "--fetch-full-installer", "--full-installer-version", desired_version]

    try:
        # Запускаем команду загрузки установщика
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        module.fail_json(
            msg="Failed to fetch full installer for version '{}'. Error: {}".format(desired_version, str(e)), 
            macos_version=host_major_version
        )

    # Проверяем, что каталог с установщиком появился
    if not os.path.isdir(expected_path):
        module.fail_json(
            msg="The installer directory '{}' was not found after fetching full installer.".format(expected_path),
            macos_version=host_major_version
        )

    # Если мы здесь, значит установщик скачан и каталог существует
    module.exit_json(
        changed=True,
        macos_version=host_major_version,
        msg="Successfully fetched full installer '{}', located at '{}'.".format(desired_version, expected_path)
    )

if __name__ == '__main__':
    main()
