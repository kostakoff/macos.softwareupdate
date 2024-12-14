#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ansible.module_utils.basic import AnsibleModule
import subprocess
import re
import platform

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

def main():
    module_args = dict(
        # Define your module arguments here if needed
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    # Check that the OS is macOS (Darwin)
    if platform.system() != "Darwin":
        module.fail_json(msg="This module can only run on macOS (Darwin). Current OS: {}".format(platform.system()))
    
    # Get the major version of macOS
    major_version = get_macos_major_version()
    if major_version is None:
        module.fail_json(msg="Failed to determine the macOS version.")
    
    # Verify that the major version is supported
    if major_version not in [13, 14, 15]:
        module.fail_json(msg="This module supports only macOS major versions 13, 14, or 15. Current version: {}".format(major_version))
    
    if module.check_mode:
        # In check_mode, do not make any changes
        module.exit_json(changed=False, msg="Check mode: no changes.")

    # Execute the softwareupdate command
    try:
        cmd_output = subprocess.check_output(
            ["softwareupdate", "--list-full-installers"],
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
    except subprocess.CalledProcessError as e:
        module.fail_json(msg="Failed to run softwareupdate: {}".format(e.output), macos_version=major_version)

    # Pattern to parse the list of installers
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

                # Convert size
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
        macos_version=major_version,
        msg="Installers listed successfully."
    )


if __name__ == '__main__':
    main()
