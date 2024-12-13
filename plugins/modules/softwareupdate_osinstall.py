#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ansible.module_utils.basic import AnsibleModule
import os
import platform
import subprocess

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

    version = module.params['version']
    username = module.params['username']
    password = module.params['password']

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
        f"echo '{password}' | nohup '{installer_path}' --agreetolicense --forcequitapps --nointeraction --user '{username}' --stdinpass > /tmp/startosinstall.log 2>&1 &"
    ]

    try:
        # Запускаем команду
        subprocess.check_call(cmd, shell=False)
    except subprocess.CalledProcessError as e:
        module.fail_json(msg=f"Failed to start OS install: {str(e)}")

    # Если мы дошли до сюда, то процесс стартовал в фоне.
    # Скорее всего начнется установка ОС и машина ребутнется.
    # Мы завершаем модуль сообщая что были изменения.
    module.exit_json(changed=True, msg="OS installation started, the machine will reboot.")


if __name__ == '__main__':
    main()
