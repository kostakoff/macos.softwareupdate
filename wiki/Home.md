# Ansible Modules for Managing macOS Updates and Installation

This set of Ansible modules provides automation for controlling macOS updates and installation on remote hosts. 

## Use cases
- In case if we wanna have automation update minor MacOS verison
- In case if we wanna have full controll for MacOS verison without MDM solutions

## How to install
```bash
ansible-galaxy collection install git+git@github.com:kostakoff/macos.softwareupdate.git,main --upgrade
```

## Configuration example
- [Install updates](./install_updates.md)
- [Reinstall macOS](./reInstall_macos.md)

## Advantages
- Automated, repeatable macOS updates and upgrades via Ansible.
- Centralized control over versioning and timing of updates.
- Seamless integration into CI/CD and IT orchestration frameworks.
- Predictable behavior for a fleet of macOS hosts.
> By leveraging these modules, you can streamline and standardize the process of updating and installing macOS versions across multiple machines, ensuring consistency, predictability, and integration into your existing automation pipelines.
