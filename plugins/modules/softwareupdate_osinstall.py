#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ansible.module_utils.basic import AnsibleModule
import os
import platform
import subprocess
import time
import re

DOCUMENTATION = r'''
---
module: softwareupdate_osinstall
short_description: Initiate macOS installation using the startosinstall command.
description:
  - >
    This module initiates the installation of macOS from macOS installer application.
    It requires root privileges and supports only major macOS versions 13, 14, and 15.
    The module runs the installation process in the background, allowing the machine to reboot automatically.
version_added: "1.0.1"
author:
  - kostakoff
options:
  version:
    description:
      - >
        The major version number of macOS to install. Supported versions are 13 (Ventura), 14 (Sonoma), and 15 (Sequoia).
    type: int
    required: true
  username:
    description:
      - >
        The username of the user to accept license greement.
    type: str
    required: true
  password:
    description:
      - >
        The password of the user to accept license greement.
    type: str
    required: true
    no_log: true
'''

EXAMPLES = r'''
# Инициировать установку macOS Ventura (версия 13)
- name: Start macOS Ventura installation
  softwareupdate_osinstall:
    version: 13
    username: admin_user
    password: "secure_password"

# Инициировать установку macOS Sonoma (версия 14)
- name: Start macOS Sonoma installation
  softwareupdate_osinstall:
    version: 14
    username: admin_user
    password: "secure_password"

# Пример использования в playbook
- name: Initiate macOS installation
  hosts: localhost
  become: yes
  gather_facts: no
  tasks:
    - name: Start macOS Ventura installation
      softwareupdate_osinstall:
        version: 13
        username: admin_user
        password: "secure_password"
      register: install_result

    - name: Display installation result
      debug:
        var: install_result

    - name: Start macOS Sonoma installation
      softwareupdate_osinstall:
        version: 14
        username: admin_user
        password: "secure_password"
      register: install_result_sonoma

    - name: Display installation result for Sonoma
      debug:
        var: install_result_sonoma
'''

RETURN = r'''
changed:
  description: Indicates if the module initiated a macOS installation.
  type: bool
  returned: always
msg:
  description: A message indicating the result of the module execution.
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

def check_log_for_progress(log_path, timeout=30, interval=3):
    """Проверяет лог на наличие строки 'Preparing: {x.x}%' в течение указанного времени."""
    start_time = time.time()
    download_pattern = re.compile(r"Preparing: \d+\.\d+%")

    while time.time() - start_time < timeout:
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r') as log_file:
                    log_content = log_file.read()
                    if download_pattern.search(log_content):
                        return True
            except Exception as e:
                # Игнорируем ошибки чтения лог-файла
                pass
        time.sleep(interval)
    return False

def main():
    module_args = dict(
        version=dict(type='int', required=True),
        username=dict(type='str', required=True),
        password=dict(type='str', required=True, no_log=True)
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False
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

    version = module.params['version']
    username = module.params['username']
    password = module.params['password']
    log_path = "/tmp/startosinstall.log"

    # Сопоставляем мажорную версию с именем установщика
    # При необходимости можно расширить словарь новыми версиями
    INSTALLERS = {
        13: "Install macOS Ventura.app",
        14: "Install macOS Sonoma.app",
        15: "Install macOS 15.app"
    }

    if version not in INSTALLERS:
        module.fail_json(msg="Unsupported version: {}. Supported: {}".format(version, list(INSTALLERS.keys())))

    installer_app = INSTALLERS[version]
    installer_path = f"/Applications/{installer_app}/Contents/Resources/startosinstall"

    if not os.path.isfile(installer_path):
        module.fail_json(msg=f"Installer not found: {installer_path}. Make sure the full installer is downloaded.")

    # Формируем команду
    # Запускаем в фоне через nohup, чтобы не блокировать сессию Ansible и позволить машине перезагрузиться.
    # Вывод перенаправим в лог /tmp/startosinstall.log
    cmd = [
        "sh", "-c",
        f"echo '{password}' | nohup '{installer_path}' --agreetolicense --forcequitapps --nointeraction --user '{username}' --stdinpass > '{log_path}' 2>&1 &"
    ]

    try:
        # Запускаем команду
        subprocess.check_call(cmd, shell=False)
    except subprocess.CalledProcessError as e:
        module.fail_json(msg=f"Failed to start OS install: {str(e)}", macos_version=major_version)

    # Проверяем, что процесс начался (ищем строку "Preparing: {x.x}%")
    if not check_log_for_progress(log_path, timeout=30, interval=3):
        # Если строка так и не появилась в течение таймаута
        module.fail_json(msg="MacOS installer '{}' failed to start installing. Check log: {}".format(installer_app, log_path), macos_version=major_version)

    # Если мы дошли до сюда, то процесс стартовал в фоне.
    # Скорее всего начнется установка ОС и машина ребутнется.
    # Мы завершаем модуль сообщая что были изменения.
    module.exit_json(
        changed=True, 
        macos_version=major_version,
        msg="OS installation started, the machine will reboot"
    )


if __name__ == '__main__':
    main()
