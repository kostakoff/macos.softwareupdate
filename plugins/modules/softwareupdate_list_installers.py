#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ansible.module_utils.basic import AnsibleModule
import subprocess
import re
import platform

def main():
    module_args = dict(
        # Если вам нужны аргументы, можно определить их здесь
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    # Проверяем, что ОС — macOS (Darwin)
    if platform.system() != "Darwin":
        module.fail_json(msg="This module can only run on macOS (Darwin). Current OS: {}".format(platform.system()))
    
    if module.check_mode:
        # В check_mode не делаем изменений
        module.exit_json(changed=False, msg="Check mode: no changes.")

    # Запускаем команду softwareupdate
    try:
        cmd_output = subprocess.check_output(
            ["softwareupdate", "--list-full-installers"],
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
    except subprocess.CalledProcessError as e:
        module.fail_json(msg="Failed to run softwareupdate: {}".format(e.output))

    # Паттерн для парсинга списка установщиков
    pattern = re.compile(
        r"^\* Title:\s+(.*?), Version:\s+(.*?), Size:\s+(\d+)(?:KiB)?, Build:\s+(\S+), Deferred:\s+(.*)$"
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

                # Преобразуем размер
                try:
                    size = int(size_str)
                except ValueError:
                    size = size_str

                installers.append({
                    "title": title,
                    "version": version,
                    "size_kib": size,
                    "build": build,
                    "deferred": deferred
                })

    module.exit_json(
        changed=False,
        installers=installers,
        msg="Installers listed successfully"
    )


if __name__ == '__main__':
    main()
