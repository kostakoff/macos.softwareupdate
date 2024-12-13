#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ansible.module_utils.basic import AnsibleModule
import os
import platform
import subprocess

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
    """Записывает значение ключа в defaults, если check_mode=False.
       Возвращает True, если значение действительно было бы изменено, иначе False."""
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
    """Возвращает вывод plutil -p <path> или None, если файл не существует или ошибка."""
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
        softwareupdate_plist=swu_plist
    )

if __name__ == '__main__':
    main()
