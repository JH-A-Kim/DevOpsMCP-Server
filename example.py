#!/usr/bin/env python3
"""
Example script demonstrating the DevOps Diagnostics Server tools.

This script shows how to use the various diagnostic tools available
in the MCP server for system monitoring and troubleshooting.
"""

from server import (
    get_system_info,
    get_cpu_usage,
    get_memory_usage,
    get_disk_usage,
    list_processes,
    check_process_running,
    get_network_stats,
    get_environment_variable,
)


def main():
    print("=" * 70)
    print("DevOps Diagnostics Server - Example Usage")
    print("=" * 70)
    print()

    # System Information
    print("1. System Information")
    print("-" * 70)
    print(get_system_info())
    print()

    # CPU Usage
    print("2. CPU Usage")
    print("-" * 70)
    print(get_cpu_usage())
    print()

    # Memory Usage
    print("3. Memory Usage")
    print("-" * 70)
    print(get_memory_usage())
    print()

    # Disk Usage
    print("4. Disk Usage")
    print("-" * 70)
    print(get_disk_usage("/"))
    print()

    # Top Processes
    print("5. Top 5 Processes by CPU")
    print("-" * 70)
    print(list_processes(5))
    print()

    # Check Process
    print("6. Check if Python is Running")
    print("-" * 70)
    print(check_process_running("python"))
    print()

    # Network Stats
    print("7. Network Statistics")
    print("-" * 70)
    print(get_network_stats())
    print()

    # Environment Variable
    print("8. PATH Environment Variable")
    print("-" * 70)
    print(get_environment_variable("PATH"))
    print()

    print("=" * 70)
    print("Example completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
