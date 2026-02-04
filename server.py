from mcp.server.fastmcp import FastMCP
import subprocess  # for running commands in terminal
import os
import platform
import psutil
import socket
from datetime import datetime

app = FastMCP("DevOps Diagnostics Server", "2.0.0")


@app.tool()
def basic_greeting_test(name: str):
    """
    Test tool so I can test that this can properly be called
    from the client. (Claude Desktop)

    Args:
        name (str): Name to greet.
    """
    return f"Hello, {name}!"


@app.tool()
def validate_dockerfile(path: str):
    """
    Validates a Dockerfile and checks for best practices.
    Uses 'hadolint' to validate the given Dockerfile.
    This looks for security risks and best practices in the actual Dockerfile.

    Args:
        path (str): Path to the Dockerfile.
    """

    try:
        if not path:
            return "Error: No path provided."

        path = os.path.abspath(os.path.expanduser(path))

        if not os.path.isfile(path):
            return f"Error: The file at path '{path}' does not exist."

        outcome = subprocess.run(
            ["hadolint", path], capture_output=True, text=True, timeout=10
        )

        if outcome.returncode == 0:
            return "Dockerfile is valid and follows best practices."
        elif outcome.stderr:
            return f"Dockerfile errors found:\n{outcome.stderr}"
        else:
            return f"Dockerfile issues found:\n{outcome.stdout}"

    except FileNotFoundError:
        return (
            "Error: 'hadolint' is not installed or not found in PATH. "
            "Please install hadolint to validate Dockerfiles."
        )
    except subprocess.TimeoutExpired:
        return "Error: Validation process timed out."
    except Exception as e:
        return f"Unexpected error while validating the Dockerfile: {e}"


@app.tool()
def get_system_info():
    """
    Retrieves comprehensive system information including OS, version,
    architecture, hostname, and uptime.

    Returns detailed system metrics useful for diagnostics and troubleshooting.
    """
    try:
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time

        info = {
            "os": platform.system(),
            "os_version": platform.version(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "hostname": socket.gethostname(),
            "python_version": platform.python_version(),
            "boot_time": boot_time.strftime("%Y-%m-%d %H:%M:%S"),
            "uptime": str(uptime).split(".")[0],  # Remove microseconds
        }

        result = "=== System Information ===\n"
        for key, value in info.items():
            # Special case for 'os' to display as 'OS' instead of 'Os'
            label = key.replace("_", " ").title()
            if key.startswith("os"):
                label = label.replace("Os", "OS")
            result += f"{label}: {value}\n"

        return result
    except Exception as e:
        return f"Error retrieving system information: {e}"


@app.tool()
def get_cpu_usage():
    """
    Monitors CPU usage and provides detailed CPU metrics.

    Returns per-CPU core usage percentages and overall CPU usage.
    Useful for identifying CPU bottlenecks and performance issues.
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count_logical = psutil.cpu_count(logical=True)
        cpu_count_physical = psutil.cpu_count(logical=False)
        per_cpu = psutil.cpu_percent(interval=1, percpu=True)

        result = "=== CPU Usage ===\n"
        result += f"Overall CPU Usage: {cpu_percent}%\n"
        result += f"Physical Cores: {cpu_count_physical}\n"
        result += f"Logical Cores: {cpu_count_logical}\n"
        result += "\nPer-Core Usage:\n"
        for i, percent in enumerate(per_cpu):
            result += f"  Core {i}: {percent}%\n"

        return result
    except Exception as e:
        return f"Error retrieving CPU usage: {e}"


@app.tool()
def get_memory_usage():
    """
    Retrieves detailed memory usage statistics including RAM and swap.

    Returns total, available, used memory and percentages.
    Essential for diagnosing memory leaks and capacity issues.
    """
    try:
        virtual_mem = psutil.virtual_memory()
        swap_mem = psutil.swap_memory()

        def bytes_to_gb(bytes_val):
            return round(bytes_val / (1024**3), 2)

        result = "=== Memory Usage ===\n"
        result += f"Total RAM: {bytes_to_gb(virtual_mem.total)} GB\n"
        result += f"Available RAM: {bytes_to_gb(virtual_mem.available)} GB\n"
        result += f"Used RAM: {bytes_to_gb(virtual_mem.used)} GB\n"
        result += f"RAM Usage: {virtual_mem.percent}%\n"
        result += "\nSwap Memory:\n"
        result += f"Total Swap: {bytes_to_gb(swap_mem.total)} GB\n"
        result += f"Used Swap: {bytes_to_gb(swap_mem.used)} GB\n"
        result += f"Swap Usage: {swap_mem.percent}%\n"

        return result
    except Exception as e:
        return f"Error retrieving memory usage: {e}"


@app.tool()
def get_disk_usage(path: str = "/"):
    """
    Analyzes disk usage for a specified path or mount point.

    Args:
        path (str): Path to check disk usage for (defaults to root "/")

    Returns disk space statistics including total, used, and free space.
    Critical for preventing disk space issues.
    """
    try:
        path = os.path.abspath(os.path.expanduser(path))

        if not os.path.exists(path):
            return f"Error: Path '{path}' does not exist."

        disk = psutil.disk_usage(path)

        def bytes_to_gb(bytes_val):
            return round(bytes_val / (1024**3), 2)

        result = f"=== Disk Usage for {path} ===\n"
        result += f"Total: {bytes_to_gb(disk.total)} GB\n"
        result += f"Used: {bytes_to_gb(disk.used)} GB\n"
        result += f"Free: {bytes_to_gb(disk.free)} GB\n"
        result += f"Usage: {disk.percent}%\n"

        return result
    except Exception as e:
        return f"Error retrieving disk usage: {e}"


@app.tool()
def list_processes(limit: int = 10):
    """
    Lists currently running processes sorted by CPU usage.

    Args:
        limit (int): Maximum number of processes to display (default: 10)

    Returns top processes with PID, name, CPU%, and memory usage.
    Useful for identifying resource-intensive processes.
    """
    try:
        processes = []
        for proc in psutil.process_iter(
            ["pid", "name", "cpu_percent", "memory_percent"]
        ):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Sort by CPU usage
        processes.sort(key=lambda x: x.get("cpu_percent", 0), reverse=True)

        result = f"=== Top {limit} Processes by CPU Usage ===\n"
        result += f"{'PID':<8} {'NAME':<30} {'CPU%':<8} {'MEM%':<8}\n"
        result += "-" * 60 + "\n"

        for proc in processes[:limit]:
            result += f"{proc.get('pid', 'N/A'):<8} "
            result += f"{proc.get('name', 'N/A'):<30} "
            result += f"{proc.get('cpu_percent', 0):<8.1f} "
            result += f"{proc.get('memory_percent', 0):<8.1f}\n"

        return result
    except Exception as e:
        return f"Error listing processes: {e}"


@app.tool()
def check_process_running(process_name: str):
    """
    Checks if a specific process is currently running.

    Args:
        process_name (str): Name of the process to search for

    Returns whether the process is running and lists matching PIDs.
    Helpful for verifying service status.
    """
    try:
        matching_processes = []
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if process_name.lower() in proc.info["name"].lower() or any(
                    process_name.lower() in arg.lower()
                    for arg in proc.info.get("cmdline", [])
                    if arg
                ):
                    matching_processes.append(
                        {"pid": proc.info["pid"], "name": proc.info["name"]}
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if matching_processes:
            result = f"Process '{process_name}' is RUNNING\n\n"
            result += "Matching processes:\n"
            for proc in matching_processes:
                result += f"  PID: {proc['pid']}, Name: {proc['name']}\n"
            return result
        else:
            return f"Process '{process_name}' is NOT running"
    except Exception as e:
        return f"Error checking process: {e}"


@app.tool()
def check_port_listening(port: int, host: str = "127.0.0.1"):
    """
    Checks if a specific port is listening/open on the system.

    Args:
        port (int): Port number to check
        host (str): Host to check (default: 127.0.0.1 for localhost)

    Returns whether the port is open and which process is using it.
    Essential for troubleshooting network services.
    """
    try:
        # Check if port is in use using psutil
        connections = psutil.net_connections(kind="inet")
        port_info = []

        for conn in connections:
            if conn.laddr.port == port:
                try:
                    proc = psutil.Process(conn.pid) if conn.pid else None
                    port_info.append(
                        {
                            "pid": conn.pid,
                            "status": conn.status,
                            "process": proc.name() if proc else "Unknown",
                        }
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    port_info.append(
                        {"pid": conn.pid, "status": conn.status, "process": "Unknown"}
                    )

        if port_info:
            result = f"Port {port} is LISTENING\n\n"
            for info in port_info:
                result += f"PID: {info['pid']}, "
                result += f"Process: {info['process']}, "
                result += f"Status: {info['status']}\n"
            return result
        else:
            # Try to connect to verify
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result_code = sock.connect_ex((host, port))
            sock.close()

            if result_code == 0:
                return f"Port {port} is OPEN but process information unavailable"
            else:
                return f"Port {port} is NOT listening"
    except Exception as e:
        return f"Error checking port: {e}"


@app.tool()
def get_network_stats():
    """
    Retrieves network interface statistics and information.

    Returns data sent/received for each network interface.
    Useful for monitoring network activity and diagnosing connectivity.
    """
    try:
        net_io = psutil.net_io_counters(pernic=True)

        def bytes_to_mb(bytes_val):
            return round(bytes_val / (1024**2), 2)

        result = "=== Network Statistics ===\n\n"
        for interface, stats in net_io.items():
            result += f"Interface: {interface}\n"
            result += f"  Bytes Sent: {bytes_to_mb(stats.bytes_sent)} MB\n"
            result += f"  Bytes Received: {bytes_to_mb(stats.bytes_recv)} MB\n"
            result += f"  Packets Sent: {stats.packets_sent}\n"
            result += f"  Packets Received: {stats.packets_recv}\n"
            result += f"  Errors In: {stats.errin}\n"
            result += f"  Errors Out: {stats.errout}\n"
            result += "\n"

        return result
    except Exception as e:
        return f"Error retrieving network stats: {e}"


@app.tool()
def read_log_file(file_path: str, lines: int = 50, search_term: str = None):
    """
    Reads and optionally filters a log file.

    Args:
        file_path (str): Path to the log file
        lines (int): Number of lines to return from the end (default: 50)
        search_term (str): Optional search term to filter log lines

    Returns the last N lines of the log file, optionally filtered.
    Essential for log analysis and troubleshooting.
    """
    try:
        file_path = os.path.abspath(os.path.expanduser(file_path))

        if not os.path.isfile(file_path):
            return f"Error: File '{file_path}' does not exist."

        # Check file size to prevent reading massive files
        file_size = os.path.getsize(file_path)
        if file_size > 10 * 1024 * 1024:  # 10 MB limit
            return (
                f"Error: File size ({file_size / (1024**2):.2f} MB) exceeds "
                "10 MB limit. Please use a more specific search or smaller file."
            )

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()

        # Filter if search term provided
        if search_term:
            filtered_lines = [line for line in all_lines if search_term in line]
            result_lines = (
                filtered_lines[-lines:]
                if len(filtered_lines) > lines
                else filtered_lines
            )
            result = (
                f"=== Last {len(result_lines)} matching lines from {file_path} ===\n"
            )
            result += f"(Search term: '{search_term}')\n\n"
        else:
            result_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            result = f"=== Last {len(result_lines)} lines from {file_path} ===\n\n"

        result += "".join(result_lines)

        return result
    except Exception as e:
        return f"Error reading log file: {e}"


@app.tool()
def get_directory_size(path: str):
    """
    Calculates the total size of a directory and its contents.

    Args:
        path (str): Path to the directory

    Returns the total size and file count.
    Useful for identifying disk space usage.
    """
    try:
        path = os.path.abspath(os.path.expanduser(path))

        if not os.path.exists(path):
            return f"Error: Path '{path}' does not exist."

        if not os.path.isdir(path):
            return f"Error: Path '{path}' is not a directory."

        total_size = 0
        file_count = 0
        dir_count = 0

        for dirpath, dirnames, filenames in os.walk(path):
            dir_count += len(dirnames)
            for filename in filenames:
                file_count += 1
                file_path = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(file_path)
                except (OSError, FileNotFoundError):
                    pass

        def bytes_to_human(bytes_val):
            for unit in ["B", "KB", "MB", "GB", "TB"]:
                if bytes_val < 1024.0:
                    return f"{bytes_val:.2f} {unit}"
                bytes_val /= 1024.0
            return f"{bytes_val:.2f} PB"

        result = f"=== Directory Size: {path} ===\n"
        result += f"Total Size: {bytes_to_human(total_size)}\n"
        result += f"Files: {file_count}\n"
        result += f"Subdirectories: {dir_count}\n"

        return result
    except Exception as e:
        return f"Error calculating directory size: {e}"


@app.tool()
def get_environment_variable(var_name: str = None):
    """
    Retrieves environment variable(s).

    Args:
        var_name (str): Specific environment variable name (optional).
                       If not provided, returns all environment variables.

    Returns the value of specified variable or all variables.
    Useful for debugging configuration issues.
    """
    try:
        if var_name:
            value = os.environ.get(var_name)
            if value is not None:
                return f"{var_name}={value}"
            else:
                return f"Environment variable '{var_name}' is not set."
        else:
            result = "=== Environment Variables ===\n\n"
            for key, value in sorted(os.environ.items()):
                result += f"{key}={value}\n"
            return result
    except Exception as e:
        return f"Error retrieving environment variable: {e}"


if __name__ == "__main__":
    app.run(transport="stdio")
