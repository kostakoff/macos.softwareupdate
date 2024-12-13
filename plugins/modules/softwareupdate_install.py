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
module: softwareupdate_install
short_description: Installs a specific macOS software update by label
description:
  - This module installs a specific macOS software update using the `softwareupdate` tool.
  - The module ensures the update is available, starts the installation process in the background, and verifies that it has started successfully.
  - Requires root privileges to execute.
version_added: "1.0.1"
options:
  label:
    description:
      - The label of the macOS update to install.
      - This label must match the output of the `softwareupdate --list` command.
    required: true
    type: str
  username:
    description:
      - The username of the local administrator for accepting the license agreement.
    required: true
    type: str
  password:
    description:
      - The password for the provided local administrator username.
      - This password will be passed to the `softwareupdate` tool via `--stdinpass`.
    required: true
    type: str
    no_log: true
author:
  - Your Name (@your_handle)
'''

EXAMPLES = r'''
- name: Install a specific macOS update
  softwareupdate_install:
    label: "macOS Sonoma 14.7.2-23H311"
    username: "admin"
    password: "mypassword"
  become: true
  ignore_errors: true

- name: Wait for the system to reboot after update
  wait_for_connection:
    delay: 60
    timeout: 600
'''

RETURN = r'''
msg:
  description: Message indicating the result of the operation.
  returned: always
  type: str
  sample: "Update 'macOS Sonoma 14.7.2-23H311' installation started successfully in background."
changed:
  description: Indicates whether the update process was successfully started.
  returned: always
  type: bool
'''

def check_log_for_progress(log_path, timeout=30, interval=3):
    """Проверяет лог на наличие строки 'Downloading: {x.x}%' в течение указанного времени."""
    start_time = time.time()
    download_pattern = re.compile(r"Downloading: \d+\.\d+%")

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
        label=dict(type='str', required=True),
        username=dict(type='str', required=True),
        password=dict(type='str', required=True, no_log=True),
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

    label = module.params['label']
    username = module.params['username']
    password = module.params['password']
    log_path = "/tmp/softwareupdate_install.log"

    # Проверим, что обновление доступно
    try:
        list_output = subprocess.check_output(
            ["softwareupdate", "--list"],
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
    except subprocess.CalledProcessError as e:
        module.fail_json(msg="Failed to run 'softwareupdate --list': {}".format(e.output))

    label_pattern = re.compile(r"^\* Label:\s+(.+)$", re.MULTILINE)
    labels_found = label_pattern.findall(list_output)

    if label not in labels_found:
        module.fail_json(msg="Update with label '{}' not found in available updates.".format(label))

    # Формируем команду с nohup и stdinpass
    cmd = "echo '{password}' | nohup softwareupdate --install \"{label}\" --agree-to-license --verbose --no-scan --restart --stdinpass --user \"{username}\" > {log_path} 2>&1 &".format(
        password=password,
        label=label,
        username=username,
        log_path=log_path
    )

    # Запускаем команду в фоне через шелл
    try:
        subprocess.check_call(cmd, shell=True)
    except subprocess.CalledProcessError as e:
        module.fail_json(msg="Failed to start update '{}'. Error: {}".format(label, str(e)))

    # Проверяем, что процесс начался (ищем строку "Downloading: {x.x}%")
    if not check_log_for_progress(log_path, timeout=30, interval=3):
        # Если строка так и не появилась в течение таймаута
        module.fail_json(msg="Update '{}' failed to start downloading. Check log: {}".format(label, log_path))

    # Если мы здесь, обновление успешно запустилось
    module.exit_json(changed=True, msg="Update '{}' installation started successfully in background.".format(label))

if __name__ == '__main__':
    main()
