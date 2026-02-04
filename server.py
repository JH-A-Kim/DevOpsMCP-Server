from mcp.server.fastmcp import FastMCP
import subprocess  # for running commands in terminal
import os
import platform
import psutil
import socket
from datetime import datetime
import json

# Optional imports for cloud providers and containerization
try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False

try:
    from kubernetes import client, config
    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False

try:
    import boto3
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False

try:
    from azure.identity import DefaultAzureCredential
    from azure.mgmt.compute import ComputeManagementClient
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

try:
    from google.cloud import compute_v1
    GCP_AVAILABLE = True
except ImportError:
    GCP_AVAILABLE = False

app = FastMCP("DevOps Diagnostics Server", "3.0.0")


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


# ============================================================================
# Docker Container Inspection Tools
# ============================================================================


@app.tool()
def list_docker_containers(all_containers: bool = False):
    """
    Lists Docker containers running on the system.

    Args:
        all_containers (bool): If True, shows all containers (including stopped).
                              If False, shows only running containers (default).

    Returns information about Docker containers including ID, name, status, and image.
    Useful for monitoring containerized applications.
    """
    if not DOCKER_AVAILABLE:
        return "Error: Docker library not installed. Install with: pip install docker"

    try:
        docker_client = docker.from_env()
        containers = docker_client.containers.list(all=all_containers)

        if not containers:
            status = "all" if all_containers else "running"
            return f"No {status} containers found."

        result = f"=== Docker Containers ({'All' if all_containers else 'Running'}) ===\n\n"
        for container in containers:
            result += f"ID: {container.short_id}\n"
            result += f"Name: {container.name}\n"
            result += f"Status: {container.status}\n"
            result += f"Image: {container.image.tags[0] if container.image.tags else container.image.short_id}\n"
            result += f"Created: {container.attrs['Created'][:19]}\n"
            result += "-" * 60 + "\n"

        return result
    except docker.errors.DockerException as e:
        return f"Docker error: {e}. Is Docker daemon running?"
    except Exception as e:
        return f"Error listing containers: {e}"


@app.tool()
def inspect_docker_container(container_id: str):
    """
    Inspects a Docker container and returns detailed information.

    Args:
        container_id (str): Container ID or name to inspect

    Returns detailed container configuration, network settings, and mounts.
    Essential for troubleshooting container issues.
    """
    if not DOCKER_AVAILABLE:
        return "Error: Docker library not installed. Install with: pip install docker"

    try:
        docker_client = docker.from_env()
        container = docker_client.containers.get(container_id)
        attrs = container.attrs

        result = f"=== Container Inspection: {container.name} ===\n\n"
        result += f"ID: {container.id}\n"
        result += f"Name: {container.name}\n"
        result += f"Status: {container.status}\n"
        result += f"Image: {attrs['Config']['Image']}\n"
        result += f"Created: {attrs['Created'][:19]}\n"

        # Network information
        result += "\n--- Network Settings ---\n"
        networks = attrs.get('NetworkSettings', {}).get('Networks', {})
        for net_name, net_info in networks.items():
            result += f"Network: {net_name}\n"
            result += f"  IP Address: {net_info.get('IPAddress', 'N/A')}\n"
            result += f"  Gateway: {net_info.get('Gateway', 'N/A')}\n"

        # Port bindings
        result += "\n--- Port Bindings ---\n"
        port_bindings = attrs.get('HostConfig', {}).get('PortBindings', {})
        if port_bindings:
            for container_port, host_bindings in port_bindings.items():
                for binding in host_bindings or []:
                    result += f"{container_port} -> {binding.get('HostIp', '0.0.0.0')}:{binding.get('HostPort', 'N/A')}\n"
        else:
            result += "No port bindings\n"

        # Mounts
        result += "\n--- Mounts ---\n"
        mounts = attrs.get('Mounts', [])
        if mounts:
            for mount in mounts:
                result += f"{mount.get('Type', 'unknown')}: {mount.get('Source', 'N/A')} -> {mount.get('Destination', 'N/A')}\n"
        else:
            result += "No mounts\n"

        # Environment variables (first 10)
        result += "\n--- Environment (first 10) ---\n"
        env_vars = attrs.get('Config', {}).get('Env', [])
        for env in env_vars[:10]:
            result += f"{env}\n"
        if len(env_vars) > 10:
            result += f"... and {len(env_vars) - 10} more\n"

        return result
    except docker.errors.NotFound:
        return f"Error: Container '{container_id}' not found."
    except docker.errors.DockerException as e:
        return f"Docker error: {e}"
    except Exception as e:
        return f"Error inspecting container: {e}"


@app.tool()
def get_docker_logs(container_id: str, lines: int = 100, follow: bool = False):
    """
    Retrieves logs from a Docker container.

    Args:
        container_id (str): Container ID or name
        lines (int): Number of log lines to retrieve (default: 100)
        follow (bool): Not implemented for MCP (default: False)

    Returns the last N lines of container logs.
    Critical for debugging containerized applications.
    """
    if not DOCKER_AVAILABLE:
        return "Error: Docker library not installed. Install with: pip install docker"

    try:
        docker_client = docker.from_env()
        container = docker_client.containers.get(container_id)

        logs = container.logs(tail=lines, timestamps=True).decode('utf-8', errors='replace')

        result = f"=== Docker Logs: {container.name} (last {lines} lines) ===\n\n"
        result += logs

        return result
    except docker.errors.NotFound:
        return f"Error: Container '{container_id}' not found."
    except docker.errors.DockerException as e:
        return f"Docker error: {e}"
    except Exception as e:
        return f"Error retrieving logs: {e}"


@app.tool()
def get_docker_stats(container_id: str):
    """
    Gets resource usage statistics for a Docker container.

    Args:
        container_id (str): Container ID or name

    Returns CPU, memory, and network I/O statistics.
    Useful for performance monitoring and capacity planning.
    """
    if not DOCKER_AVAILABLE:
        return "Error: Docker library not installed. Install with: pip install docker"

    try:
        docker_client = docker.from_env()
        container = docker_client.containers.get(container_id)

        # Get stats (stream=False returns a single snapshot)
        stats = container.stats(stream=False)

        result = f"=== Container Stats: {container.name} ===\n\n"

        # CPU stats
        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                   stats['precpu_stats']['cpu_usage']['total_usage']
        system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                      stats['precpu_stats']['system_cpu_usage']
        cpu_count = stats['cpu_stats'].get('online_cpus', 1)

        cpu_percent = 0.0
        if system_delta > 0 and cpu_delta > 0:
            cpu_percent = (cpu_delta / system_delta) * cpu_count * 100.0

        result += f"CPU Usage: {cpu_percent:.2f}%\n"

        # Memory stats
        mem_usage = stats['memory_stats'].get('usage', 0)
        mem_limit = stats['memory_stats'].get('limit', 1)
        mem_percent = (mem_usage / mem_limit) * 100 if mem_limit > 0 else 0

        result += f"Memory Usage: {mem_usage / (1024**2):.2f} MB / {mem_limit / (1024**2):.2f} MB ({mem_percent:.2f}%)\n"

        # Network I/O
        result += "\n--- Network I/O ---\n"
        networks = stats.get('networks', {})
        for interface, net_stats in networks.items():
            rx_bytes = net_stats.get('rx_bytes', 0) / (1024**2)
            tx_bytes = net_stats.get('tx_bytes', 0) / (1024**2)
            result += f"{interface}:\n"
            result += f"  RX: {rx_bytes:.2f} MB\n"
            result += f"  TX: {tx_bytes:.2f} MB\n"

        # Block I/O
        result += "\n--- Block I/O ---\n"
        blkio_stats = stats.get('blkio_stats', {}).get('io_service_bytes_recursive', [])
        total_read = sum(item['value'] for item in blkio_stats if item.get('op') == 'Read')
        total_write = sum(item['value'] for item in blkio_stats if item.get('op') == 'Write')
        result += f"Read: {total_read / (1024**2):.2f} MB\n"
        result += f"Write: {total_write / (1024**2):.2f} MB\n"

        return result
    except docker.errors.NotFound:
        return f"Error: Container '{container_id}' not found."
    except docker.errors.DockerException as e:
        return f"Docker error: {e}"
    except Exception as e:
        return f"Error getting container stats: {e}"


# ============================================================================
# Kubernetes Diagnostics Tools
# ============================================================================


@app.tool()
def list_k8s_pods(namespace: str = "default", all_namespaces: bool = False):
    """
    Lists Kubernetes pods in a namespace.

    Args:
        namespace (str): Kubernetes namespace (default: "default")
        all_namespaces (bool): If True, lists pods from all namespaces

    Returns pod names, status, and basic information.
    Essential for Kubernetes cluster diagnostics.
    """
    if not KUBERNETES_AVAILABLE:
        return "Error: Kubernetes library not installed. Install with: pip install kubernetes"

    try:
        # Try to load config from default location or in-cluster config
        try:
            config.load_kube_config()
        except config.ConfigException:
            config.load_incluster_config()

        v1 = client.CoreV1Api()

        if all_namespaces:
            pods = v1.list_pod_for_all_namespaces(watch=False)
            result = "=== Kubernetes Pods (All Namespaces) ===\n\n"
        else:
            pods = v1.list_namespaced_pod(namespace, watch=False)
            result = f"=== Kubernetes Pods (Namespace: {namespace}) ===\n\n"

        if not pods.items:
            return result + "No pods found."

        for pod in pods.items:
            result += f"Name: {pod.metadata.name}\n"
            result += f"Namespace: {pod.metadata.namespace}\n"
            result += f"Status: {pod.status.phase}\n"
            result += f"Node: {pod.spec.node_name or 'Not assigned'}\n"
            result += f"IP: {pod.status.pod_ip or 'N/A'}\n"

            # Container statuses
            if pod.status.container_statuses:
                result += "Containers:\n"
                for container in pod.status.container_statuses:
                    result += f"  - {container.name}: {'Ready' if container.ready else 'Not Ready'} "
                    result += f"(Restarts: {container.restart_count})\n"

            result += "-" * 60 + "\n"

        return result
    except Exception as e:
        return f"Error listing pods: {e}. Ensure kubeconfig is properly configured."


@app.tool()
def get_k8s_pod_logs(pod_name: str, namespace: str = "default", container: str = None, lines: int = 100):
    """
    Retrieves logs from a Kubernetes pod.

    Args:
        pod_name (str): Name of the pod
        namespace (str): Kubernetes namespace (default: "default")
        container (str): Specific container name (optional, uses first container if not specified)
        lines (int): Number of log lines to retrieve (default: 100)

    Returns pod logs for debugging.
    Critical for troubleshooting Kubernetes applications.
    """
    if not KUBERNETES_AVAILABLE:
        return "Error: Kubernetes library not installed. Install with: pip install kubernetes"

    try:
        try:
            config.load_kube_config()
        except config.ConfigException:
            config.load_incluster_config()

        v1 = client.CoreV1Api()

        logs = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            container=container,
            tail_lines=lines
        )

        result = f"=== Kubernetes Pod Logs: {pod_name} ===\n"
        if container:
            result += f"Container: {container}\n"
        result += f"Namespace: {namespace}\n"
        result += f"Lines: {lines}\n\n"
        result += logs

        return result
    except client.exceptions.ApiException as e:
        return f"Kubernetes API error: {e.reason}. Pod '{pod_name}' may not exist in namespace '{namespace}'."
    except Exception as e:
        return f"Error retrieving pod logs: {e}"


@app.tool()
def get_k8s_pod_status(pod_name: str, namespace: str = "default"):
    """
    Gets detailed status and events for a Kubernetes pod.

    Args:
        pod_name (str): Name of the pod
        namespace (str): Kubernetes namespace (default: "default")

    Returns pod status, conditions, and recent events.
    Useful for diagnosing pod issues.
    """
    if not KUBERNETES_AVAILABLE:
        return "Error: Kubernetes library not installed. Install with: pip install kubernetes"

    try:
        try:
            config.load_kube_config()
        except config.ConfigException:
            config.load_incluster_config()

        v1 = client.CoreV1Api()

        # Get pod details
        pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)

        result = f"=== Pod Status: {pod_name} ===\n"
        result += f"Namespace: {namespace}\n"
        result += f"Phase: {pod.status.phase}\n"
        result += f"Start Time: {pod.status.start_time or 'Not started'}\n"
        result += f"Node: {pod.spec.node_name or 'Not assigned'}\n"

        # Conditions
        result += "\n--- Conditions ---\n"
        if pod.status.conditions:
            for condition in pod.status.conditions:
                result += f"{condition.type}: {condition.status} "
                if condition.reason:
                    result += f"(Reason: {condition.reason})"
                result += "\n"

        # Container statuses
        result += "\n--- Container Statuses ---\n"
        if pod.status.container_statuses:
            for container in pod.status.container_statuses:
                result += f"Container: {container.name}\n"
                result += f"  Ready: {container.ready}\n"
                result += f"  Restarts: {container.restart_count}\n"
                result += f"  Image: {container.image}\n"

                if container.state:
                    if container.state.running:
                        result += f"  State: Running (since {container.state.running.started_at})\n"
                    elif container.state.waiting:
                        result += f"  State: Waiting (Reason: {container.state.waiting.reason})\n"
                    elif container.state.terminated:
                        result += f"  State: Terminated (Reason: {container.state.terminated.reason})\n"

        # Get events
        result += "\n--- Recent Events ---\n"
        events = v1.list_namespaced_event(
            namespace=namespace,
            field_selector=f"involvedObject.name={pod_name}"
        )

        if events.items:
            # Sort by last timestamp
            sorted_events = sorted(events.items, key=lambda x: x.last_timestamp or x.event_time, reverse=True)
            for event in sorted_events[:10]:  # Show last 10 events
                result += f"[{event.type}] {event.reason}: {event.message}\n"
        else:
            result += "No recent events\n"

        return result
    except client.exceptions.ApiException as e:
        return f"Kubernetes API error: {e.reason}"
    except Exception as e:
        return f"Error getting pod status: {e}"


@app.tool()
def list_k8s_services(namespace: str = "default", all_namespaces: bool = False):
    """
    Lists Kubernetes services.

    Args:
        namespace (str): Kubernetes namespace (default: "default")
        all_namespaces (bool): If True, lists services from all namespaces

    Returns service names, types, and endpoints.
    Helpful for understanding service connectivity.
    """
    if not KUBERNETES_AVAILABLE:
        return "Error: Kubernetes library not installed. Install with: pip install kubernetes"

    try:
        try:
            config.load_kube_config()
        except config.ConfigException:
            config.load_incluster_config()

        v1 = client.CoreV1Api()

        if all_namespaces:
            services = v1.list_service_for_all_namespaces(watch=False)
            result = "=== Kubernetes Services (All Namespaces) ===\n\n"
        else:
            services = v1.list_namespaced_service(namespace, watch=False)
            result = f"=== Kubernetes Services (Namespace: {namespace}) ===\n\n"

        if not services.items:
            return result + "No services found."

        for svc in services.items:
            result += f"Name: {svc.metadata.name}\n"
            result += f"Namespace: {svc.metadata.namespace}\n"
            result += f"Type: {svc.spec.type}\n"
            result += f"Cluster IP: {svc.spec.cluster_ip}\n"

            if svc.spec.ports:
                result += "Ports:\n"
                for port in svc.spec.ports:
                    result += f"  - {port.name or 'unnamed'}: {port.port}"
                    if port.target_port:
                        result += f" -> {port.target_port}"
                    result += f" ({port.protocol})\n"

            if svc.spec.type == 'LoadBalancer' and svc.status.load_balancer.ingress:
                result += "Load Balancer:\n"
                for ingress in svc.status.load_balancer.ingress:
                    if ingress.ip:
                        result += f"  IP: {ingress.ip}\n"
                    if ingress.hostname:
                        result += f"  Hostname: {ingress.hostname}\n"

            result += "-" * 60 + "\n"

        return result
    except Exception as e:
        return f"Error listing services: {e}"


@app.tool()
def get_k8s_node_status():
    """
    Gets the status of all Kubernetes cluster nodes.

    Returns node health, capacity, and resource usage.
    Critical for cluster capacity planning and troubleshooting.
    """
    if not KUBERNETES_AVAILABLE:
        return "Error: Kubernetes library not installed. Install with: pip install kubernetes"

    try:
        try:
            config.load_kube_config()
        except config.ConfigException:
            config.load_incluster_config()

        v1 = client.CoreV1Api()
        nodes = v1.list_node(watch=False)

        if not nodes.items:
            return "No nodes found in the cluster."

        result = "=== Kubernetes Nodes Status ===\n\n"

        for node in nodes.items:
            result += f"Name: {node.metadata.name}\n"

            # Node conditions
            result += "Status: "
            if node.status.conditions:
                ready_condition = next((c for c in node.status.conditions if c.type == 'Ready'), None)
                if ready_condition:
                    result += f"{'Ready' if ready_condition.status == 'True' else 'Not Ready'}\n"

            # Node info
            if node.status.node_info:
                info = node.status.node_info
                result += f"OS: {info.operating_system} ({info.os_image})\n"
                result += f"Kernel: {info.kernel_version}\n"
                result += f"Container Runtime: {info.container_runtime_version}\n"
                result += f"Kubelet: {info.kubelet_version}\n"

            # Capacity and allocatable resources
            if node.status.capacity:
                result += "\n--- Capacity ---\n"
                result += f"CPU: {node.status.capacity.get('cpu', 'N/A')}\n"
                result += f"Memory: {node.status.capacity.get('memory', 'N/A')}\n"
                result += f"Pods: {node.status.capacity.get('pods', 'N/A')}\n"

            if node.status.allocatable:
                result += "\n--- Allocatable ---\n"
                result += f"CPU: {node.status.allocatable.get('cpu', 'N/A')}\n"
                result += f"Memory: {node.status.allocatable.get('memory', 'N/A')}\n"
                result += f"Pods: {node.status.allocatable.get('pods', 'N/A')}\n"

            result += "-" * 60 + "\n"

        return result
    except Exception as e:
        return f"Error getting node status: {e}"


# ============================================================================
# Cloud Provider Integration Tools
# ============================================================================


@app.tool()
def list_aws_ec2_instances(region: str = "us-east-1", max_results: int = 20):
    """
    Lists AWS EC2 instances in a specific region.

    Args:
        region (str): AWS region (default: "us-east-1")
        max_results (int): Maximum number of instances to return (default: 20)

    Returns EC2 instance information including ID, type, state, and tags.
    Requires AWS credentials to be configured (via environment variables or ~/.aws/credentials).
    """
    if not AWS_AVAILABLE:
        return "Error: boto3 library not installed. Install with: pip install boto3"

    try:
        ec2 = boto3.client('ec2', region_name=region)
        response = ec2.describe_instances(MaxResults=max_results)

        result = f"=== AWS EC2 Instances (Region: {region}) ===\n\n"

        instance_count = 0
        for reservation in response.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                instance_count += 1
                result += f"Instance ID: {instance.get('InstanceId', 'N/A')}\n"
                result += f"Type: {instance.get('InstanceType', 'N/A')}\n"
                result += f"State: {instance.get('State', {}).get('Name', 'N/A')}\n"
                result += f"Private IP: {instance.get('PrivateIpAddress', 'N/A')}\n"
                result += f"Public IP: {instance.get('PublicIpAddress', 'N/A')}\n"
                result += f"Launch Time: {instance.get('LaunchTime', 'N/A')}\n"

                # Tags
                tags = instance.get('Tags', [])
                if tags:
                    result += "Tags:\n"
                    for tag in tags:
                        result += f"  {tag.get('Key', '')}: {tag.get('Value', '')}\n"

                result += "-" * 60 + "\n"

        if instance_count == 0:
            result += "No instances found.\n"
        else:
            result += f"\nTotal instances: {instance_count}\n"

        return result
    except Exception as e:
        return f"Error listing EC2 instances: {e}. Ensure AWS credentials are configured."


@app.tool()
def get_aws_s3_buckets():
    """
    Lists all S3 buckets in the AWS account.

    Returns S3 bucket names and creation dates.
    Requires AWS credentials to be configured.
    """
    if not AWS_AVAILABLE:
        return "Error: boto3 library not installed. Install with: pip install boto3"

    try:
        s3 = boto3.client('s3')
        response = s3.list_buckets()

        result = "=== AWS S3 Buckets ===\n\n"

        buckets = response.get('Buckets', [])
        if not buckets:
            return result + "No buckets found.\n"

        for bucket in buckets:
            result += f"Name: {bucket.get('Name', 'N/A')}\n"
            result += f"Created: {bucket.get('CreationDate', 'N/A')}\n"
            result += "-" * 60 + "\n"

        result += f"\nTotal buckets: {len(buckets)}\n"

        return result
    except Exception as e:
        return f"Error listing S3 buckets: {e}. Ensure AWS credentials are configured."


@app.tool()
def list_azure_vms(subscription_id: str, resource_group: str = None):
    """
    Lists Azure Virtual Machines.

    Args:
        subscription_id (str): Azure subscription ID
        resource_group (str): Optional resource group filter

    Returns Azure VM information including name, size, location, and status.
    Requires Azure credentials to be configured.
    """
    if not AZURE_AVAILABLE:
        return "Error: Azure libraries not installed. Install with: pip install azure-mgmt-compute azure-identity"

    try:
        credential = DefaultAzureCredential()
        compute_client = ComputeManagementClient(credential, subscription_id)

        result = "=== Azure Virtual Machines ===\n"
        if resource_group:
            result += f"Resource Group: {resource_group}\n\n"
        else:
            result += "All Resource Groups\n\n"

        vm_count = 0
        if resource_group:
            vms = compute_client.virtual_machines.list(resource_group)
        else:
            vms = compute_client.virtual_machines.list_all()

        for vm in vms:
            vm_count += 1
            result += f"Name: {vm.name}\n"
            result += f"Location: {vm.location}\n"
            result += f"Size: {vm.hardware_profile.vm_size}\n"
            result += f"OS: {vm.storage_profile.os_disk.os_type}\n"

            # Get instance view for status
            try:
                if resource_group:
                    instance_view = compute_client.virtual_machines.instance_view(resource_group, vm.name)
                else:
                    # Extract resource group from VM ID
                    rg = vm.id.split('/')[4]
                    instance_view = compute_client.virtual_machines.instance_view(rg, vm.name)

                if instance_view.statuses:
                    for status in instance_view.statuses:
                        if status.code.startswith('PowerState/'):
                            result += f"Status: {status.display_status}\n"
            except Exception:
                result += "Status: Unknown\n"

            result += "-" * 60 + "\n"

        if vm_count == 0:
            result += "No virtual machines found.\n"
        else:
            result += f"\nTotal VMs: {vm_count}\n"

        return result
    except Exception as e:
        return f"Error listing Azure VMs: {e}. Ensure Azure credentials are configured."


@app.tool()
def list_gcp_instances(project_id: str, zone: str = None):
    """
    Lists Google Cloud Platform Compute Engine instances.

    Args:
        project_id (str): GCP project ID
        zone (str): Optional zone filter (e.g., "us-central1-a")

    Returns GCP instance information including name, type, status, and IP addresses.
    Requires GCP credentials to be configured (via GOOGLE_APPLICATION_CREDENTIALS).
    """
    if not GCP_AVAILABLE:
        return "Error: Google Cloud libraries not installed. Install with: pip install google-cloud-compute"

    try:
        instances_client = compute_v1.InstancesClient()

        result = f"=== GCP Compute Instances (Project: {project_id}) ===\n"
        if zone:
            result += f"Zone: {zone}\n\n"
        else:
            result += "All Zones\n\n"

        instance_count = 0

        if zone:
            # List instances in a specific zone
            request = compute_v1.ListInstancesRequest(project=project_id, zone=zone)
            instances = instances_client.list(request=request)

            for instance in instances:
                instance_count += 1
                result += f"Name: {instance.name}\n"
                result += f"Zone: {zone}\n"
                result += f"Machine Type: {instance.machine_type.split('/')[-1]}\n"
                result += f"Status: {instance.status}\n"

                # Network interfaces
                if instance.network_interfaces:
                    for interface in instance.network_interfaces:
                        result += f"Internal IP: {interface.network_i_p}\n"
                        if interface.access_configs:
                            for access_config in interface.access_configs:
                                if access_config.nat_i_p:
                                    result += f"External IP: {access_config.nat_i_p}\n"

                result += "-" * 60 + "\n"
        else:
            # List all zones first, then instances
            zones_client = compute_v1.ZonesClient()
            zones_request = compute_v1.ListZonesRequest(project=project_id)
            zones = zones_client.list(request=zones_request)

            for zone_obj in zones:
                zone_name = zone_obj.name
                request = compute_v1.ListInstancesRequest(project=project_id, zone=zone_name)
                instances = instances_client.list(request=request)

                for instance in instances:
                    instance_count += 1
                    result += f"Name: {instance.name}\n"
                    result += f"Zone: {zone_name}\n"
                    result += f"Machine Type: {instance.machine_type.split('/')[-1]}\n"
                    result += f"Status: {instance.status}\n"

                    if instance.network_interfaces:
                        for interface in instance.network_interfaces:
                            result += f"Internal IP: {interface.network_i_p}\n"

                    result += "-" * 60 + "\n"

        if instance_count == 0:
            result += "No instances found.\n"
        else:
            result += f"\nTotal instances: {instance_count}\n"

        return result
    except Exception as e:
        return f"Error listing GCP instances: {e}. Ensure GCP credentials are configured."


# ============================================================================
# Security Scanning Tools
# ============================================================================


@app.tool()
def scan_with_trivy(target: str, scan_type: str = "image"):
    """
    Scans for security vulnerabilities using Trivy.

    Args:
        target (str): Target to scan (image name, filesystem path, or repository)
        scan_type (str): Type of scan - "image", "fs" (filesystem), or "config"

    Returns security vulnerability report from Trivy.
    Requires Trivy to be installed on the system.
    """
    try:
        # Check if trivy is installed
        check_cmd = subprocess.run(
            ["which", "trivy"], capture_output=True, text=True, timeout=5
        )
        if check_cmd.returncode != 0:
            return (
                "Error: Trivy is not installed. Install from: https://aquasecurity.github.io/trivy/\n"
                "Quick install: curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin"
            )

        # Run trivy scan
        cmd = ["trivy", scan_type, "--severity", "HIGH,CRITICAL", "--format", "table", target]
        result_cmd = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )

        result = f"=== Trivy Security Scan ===\n"
        result += f"Target: {target}\n"
        result += f"Scan Type: {scan_type}\n\n"

        if result_cmd.returncode == 0:
            result += result_cmd.stdout
            if "Total: 0" in result_cmd.stdout:
                result += "\n✓ No HIGH or CRITICAL vulnerabilities found!"
        else:
            result += "Scan completed with warnings:\n"
            result += result_cmd.stdout
            if result_cmd.stderr:
                result += "\nErrors:\n" + result_cmd.stderr

        return result
    except FileNotFoundError:
        return "Error: Trivy not found in PATH. Please install Trivy."
    except subprocess.TimeoutExpired:
        return "Error: Trivy scan timed out (> 120 seconds)."
    except Exception as e:
        return f"Error running Trivy scan: {e}"


@app.tool()
def scan_with_grype(target: str):
    """
    Scans for vulnerabilities using Grype (Anchore).

    Args:
        target (str): Target to scan (container image, directory, archive, SBOM, etc.)

    Returns vulnerability report from Grype.
    Requires Grype to be installed on the system.
    """
    try:
        # Check if grype is installed
        check_cmd = subprocess.run(
            ["which", "grype"], capture_output=True, text=True, timeout=5
        )
        if check_cmd.returncode != 0:
            return (
                "Error: Grype is not installed. Install from: https://github.com/anchore/grype\n"
                "Quick install: curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin"
            )

        # Run grype scan
        cmd = ["grype", target, "-o", "table"]
        result_cmd = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )

        result = f"=== Grype Vulnerability Scan ===\n"
        result += f"Target: {target}\n\n"

        if result_cmd.returncode == 0:
            result += result_cmd.stdout
        else:
            result += "Scan completed with warnings:\n"
            result += result_cmd.stdout
            if result_cmd.stderr:
                result += "\nErrors:\n" + result_cmd.stderr

        return result
    except FileNotFoundError:
        return "Error: Grype not found in PATH. Please install Grype."
    except subprocess.TimeoutExpired:
        return "Error: Grype scan timed out (> 120 seconds)."
    except Exception as e:
        return f"Error running Grype scan: {e}"


@app.tool()
def scan_secrets(path: str, max_depth: int = 3):
    """
    Scans for exposed secrets in files using git-secrets or truffleHog patterns.

    Args:
        path (str): Directory or file path to scan
        max_depth (int): Maximum directory depth to scan (default: 3)

    Returns potential secrets found in the codebase.
    Uses basic pattern matching for common secret types.
    """
    try:
        path = os.path.abspath(os.path.expanduser(path))

        if not os.path.exists(path):
            return f"Error: Path '{path}' does not exist."

        result = f"=== Secret Scanning: {path} ===\n\n"

        # Common secret patterns
        patterns = {
            "AWS Access Key": r"AKIA[0-9A-Z]{16}",
            "Generic API Key": r"[aA][pP][iI][-_]?[kK][eE][yY][\s:=]+['\"]?[a-zA-Z0-9]{20,}",
            "Generic Secret": r"[sS][eE][cC][rR][eE][tT][\s:=]+['\"]?[a-zA-Z0-9]{20,}",
            "Private Key": r"-----BEGIN (RSA |EC )?PRIVATE KEY-----",
            "JWT Token": r"eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+",
        }

        import re
        findings = []

        if os.path.isfile(path):
            files_to_scan = [path]
        else:
            files_to_scan = []
            for root, dirs, files in os.walk(path):
                # Limit depth
                depth = root[len(path):].count(os.sep)
                if depth >= max_depth:
                    dirs.clear()

                # Skip common directories
                dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__', '.venv', 'venv']]

                for file in files:
                    # Only scan text-like files
                    if file.endswith(('.py', '.js', '.ts', '.java', '.go', '.rb', '.php', '.env', '.yaml', '.yml', '.json', '.xml', '.sh', '.txt', '.md')):
                        files_to_scan.append(os.path.join(root, file))

        for file_path in files_to_scan[:100]:  # Limit to 100 files
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                for secret_type, pattern in patterns.items():
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        # Get line number
                        line_num = content[:match.start()].count('\n') + 1
                        findings.append({
                            'file': file_path,
                            'type': secret_type,
                            'line': line_num,
                            'preview': match.group()[:50] + '...' if len(match.group()) > 50 else match.group()
                        })
            except Exception:
                continue

        if findings:
            result += f"⚠️  Found {len(findings)} potential secret(s):\n\n"
            for finding in findings[:50]:  # Show first 50
                result += f"File: {finding['file']}\n"
                result += f"  Type: {finding['type']}\n"
                result += f"  Line: {finding['line']}\n"
                result += f"  Preview: {finding['preview']}\n"
                result += "-" * 60 + "\n"

            if len(findings) > 50:
                result += f"\n... and {len(findings) - 50} more findings.\n"
        else:
            result += "✓ No obvious secrets found.\n"

        result += "\nNote: This is a basic pattern-based scan. For production, use specialized tools like:\n"
        result += "- TruffleHog: https://github.com/trufflesecurity/trufflehog\n"
        result += "- git-secrets: https://github.com/awslabs/git-secrets\n"
        result += "- Gitleaks: https://github.com/gitleaks/gitleaks\n"

        return result
    except Exception as e:
        return f"Error scanning for secrets: {e}"


# ============================================================================
# Performance Profiling Tools
# ============================================================================


@app.tool()
def get_io_stats():
    """
    Gets I/O statistics for all disk devices.

    Returns disk I/O metrics including read/write counts and bytes.
    Useful for identifying I/O bottlenecks.
    """
    try:
        io_counters = psutil.disk_io_counters(perdisk=True)

        result = "=== Disk I/O Statistics ===\n\n"

        for disk, stats in io_counters.items():
            result += f"Device: {disk}\n"
            result += f"  Read Count: {stats.read_count:,}\n"
            result += f"  Write Count: {stats.write_count:,}\n"
            result += f"  Read Bytes: {stats.read_bytes / (1024**3):.2f} GB\n"
            result += f"  Write Bytes: {stats.write_bytes / (1024**3):.2f} GB\n"
            result += f"  Read Time: {stats.read_time / 1000:.2f} seconds\n"
            result += f"  Write Time: {stats.write_time / 1000:.2f} seconds\n"
            result += "-" * 60 + "\n"

        return result
    except Exception as e:
        return f"Error retrieving I/O stats: {e}"


@app.tool()
def analyze_performance_metrics(duration: int = 5):
    """
    Analyzes system performance metrics over a specified duration.

    Args:
        duration (int): Duration in seconds to collect metrics (default: 5, max: 60)

    Returns comprehensive performance analysis including CPU, memory, and I/O trends.
    Helpful for identifying performance patterns.
    """
    try:
        import time

        if duration > 60:
            duration = 60
        if duration < 1:
            duration = 1

        result = f"=== Performance Analysis ({duration} seconds) ===\n\n"

        # Initial readings
        cpu_samples = []
        mem_samples = []

        result += "Collecting metrics"
        for i in range(duration):
            cpu_samples.append(psutil.cpu_percent(interval=1))
            mem_samples.append(psutil.virtual_memory().percent)
            if i % 5 == 0 and i > 0:
                result += "."

        result += " Done!\n\n"

        # CPU Analysis
        result += "--- CPU Usage ---\n"
        result += f"Average: {sum(cpu_samples) / len(cpu_samples):.2f}%\n"
        result += f"Maximum: {max(cpu_samples):.2f}%\n"
        result += f"Minimum: {min(cpu_samples):.2f}%\n"

        # Memory Analysis
        result += "\n--- Memory Usage ---\n"
        result += f"Average: {sum(mem_samples) / len(mem_samples):.2f}%\n"
        result += f"Maximum: {max(mem_samples):.2f}%\n"
        result += f"Minimum: {min(mem_samples):.2f}%\n"

        # Network I/O Delta
        net_io_start = psutil.net_io_counters()
        time.sleep(1)
        net_io_end = psutil.net_io_counters()

        bytes_sent = (net_io_end.bytes_sent - net_io_start.bytes_sent) / 1024
        bytes_recv = (net_io_end.bytes_recv - net_io_start.bytes_recv) / 1024

        result += "\n--- Network Activity (per second) ---\n"
        result += f"Sent: {bytes_sent:.2f} KB/s\n"
        result += f"Received: {bytes_recv:.2f} KB/s\n"

        # Analysis
        result += "\n--- Analysis ---\n"
        avg_cpu = sum(cpu_samples) / len(cpu_samples)
        avg_mem = sum(mem_samples) / len(mem_samples)

        if avg_cpu > 80:
            result += "⚠️  HIGH CPU usage detected. Consider investigating top processes.\n"
        elif avg_cpu < 20:
            result += "✓ CPU usage is low.\n"
        else:
            result += "✓ CPU usage is moderate.\n"

        if avg_mem > 80:
            result += "⚠️  HIGH memory usage detected. Check for memory leaks.\n"
        elif avg_mem < 50:
            result += "✓ Memory usage is healthy.\n"
        else:
            result += "✓ Memory usage is moderate.\n"

        return result
    except Exception as e:
        return f"Error analyzing performance: {e}"


# ============================================================================
# Automated Remediation Tools
# ============================================================================


@app.tool()
def suggest_remediation(issue_type: str, details: str = ""):
    """
    Suggests remediation steps for common DevOps issues.

    Args:
        issue_type (str): Type of issue (e.g., "high_cpu", "disk_full", "pod_crash", "container_restart")
        details (str): Additional details about the issue

    Returns suggested remediation steps and best practices.
    Helpful for quick issue resolution guidance.
    """
    remediations = {
        "high_cpu": """
=== Remediation: High CPU Usage ===

Immediate Actions:
1. Identify top CPU consumers: Use list_processes() tool
2. Check for runaway processes or infinite loops
3. Investigate recent deployments or changes

Investigation Steps:
1. Review application logs for errors or unusual patterns
2. Check for inefficient algorithms or queries
3. Profile the application to find bottlenecks
4. Monitor for CPU spikes correlation with specific events

Long-term Solutions:
1. Optimize application code and algorithms
2. Implement caching where appropriate
3. Scale horizontally (add more instances)
4. Consider upgrading to higher CPU tier
5. Implement rate limiting and throttling

Prevention:
- Set up CPU usage alerts and monitoring
- Perform load testing before deployments
- Implement auto-scaling policies
""",
        "high_memory": """
=== Remediation: High Memory Usage ===

Immediate Actions:
1. Check memory-intensive processes
2. Look for memory leaks in applications
3. Review recent changes or deployments

Investigation Steps:
1. Profile application memory usage
2. Check for large data structures in memory
3. Review caching strategies
4. Analyze object lifecycle and garbage collection

Long-term Solutions:
1. Fix memory leaks in application code
2. Implement proper resource cleanup
3. Optimize data structures and caching
4. Add more RAM or scale horizontally
5. Implement memory limits for containers

Prevention:
- Set up memory monitoring and alerts
- Regular memory profiling in development
- Implement memory limits in container/pod specs
""",
        "disk_full": """
=== Remediation: Disk Full ===

Immediate Actions:
1. Identify large files and directories: Use get_directory_size() tool
2. Clean up temporary files (/tmp, /var/tmp)
3. Rotate or compress old log files
4. Clear package manager caches

Investigation Steps:
1. Find top disk consumers: du -sh /* | sort -h
2. Check for rapidly growing directories
3. Review log retention policies
4. Identify unnecessary files

Long-term Solutions:
1. Implement log rotation (logrotate)
2. Set up automated cleanup jobs
3. Expand disk capacity
4. Implement monitoring and alerts
5. Archive old data to cheaper storage

Prevention:
- Set disk usage alerts (e.g., at 70%, 80%, 90%)
- Implement automated log rotation
- Regular audits of disk usage
- Use volume mounts for container logs
""",
        "pod_crash": """
=== Remediation: Kubernetes Pod Crash ===

Immediate Actions:
1. Check pod logs: Use get_k8s_pod_logs() tool
2. Check pod events: Use get_k8s_pod_status() tool
3. Review recent deployments

Investigation Steps:
1. Check pod status and conditions
2. Review application logs for errors
3. Verify resource limits (CPU, memory)
4. Check liveness and readiness probes
5. Verify dependencies (databases, APIs, secrets)

Common Causes:
- OOMKilled: Increase memory limits
- CrashLoopBackOff: Fix application startup issues
- ImagePullBackOff: Check image name and registry access
- ConfigMap/Secret not found: Verify resources exist

Long-term Solutions:
1. Implement proper error handling and logging
2. Set appropriate resource requests and limits
3. Configure health checks properly
4. Use init containers for dependencies
5. Implement graceful shutdown

Prevention:
- Thorough testing before deployment
- Gradual rollouts with monitoring
- Set up pod failure alerts
- Resource quota management
""",
        "container_restart": """
=== Remediation: Container Restart Loop ===

Immediate Actions:
1. Check container logs: Use get_docker_logs() tool
2. Inspect container configuration
3. Verify health checks

Investigation Steps:
1. Review exit codes and restart count
2. Check application logs for crash reasons
3. Verify environment variables and configurations
4. Test the container locally
5. Check resource constraints

Common Causes:
- Application crash on startup
- Failed health checks
- Out of memory
- Missing dependencies or configurations
- Permission issues

Long-term Solutions:
1. Fix application bugs causing crashes
2. Adjust health check timeouts
3. Increase resource allocation
4. Improve error handling and logging
5. Use restart policies appropriately

Prevention:
- Comprehensive integration testing
- Proper health check configuration
- Resource monitoring and alerts
- Staged rollouts with canary deployments
""",
        "high_network": """
=== Remediation: High Network Usage ===

Immediate Actions:
1. Check network statistics: Use get_network_stats() tool
2. Identify processes with high network activity
3. Check for DDoS or unusual traffic patterns

Investigation Steps:
1. Monitor network connections
2. Review application data transfer patterns
3. Check for large file transfers
4. Investigate API call volumes
5. Review content delivery strategy

Long-term Solutions:
1. Implement caching (CDN, application-level)
2. Optimize data transfer (compression, pagination)
3. Use more efficient protocols
4. Implement rate limiting
5. Scale network capacity

Prevention:
- Network monitoring and alerts
- Regular traffic analysis
- Implement bandwidth limits where appropriate
""",
    }

    result = remediations.get(issue_type, f"No specific remediation found for issue type: {issue_type}")

    if details:
        result += f"\n--- Additional Context ---\n{details}\n"

    result += "\n--- General Best Practices ---\n"
    result += "1. Always backup before making changes\n"
    result += "2. Test remediation steps in non-production first\n"
    result += "3. Document all changes made\n"
    result += "4. Monitor the impact of changes\n"
    result += "5. Have a rollback plan ready\n"

    return result


@app.tool()
def optimize_dockerfile(dockerfile_path: str):
    """
    Analyzes a Dockerfile and suggests optimizations.

    Args:
        dockerfile_path (str): Path to the Dockerfile

    Returns optimization suggestions for the Dockerfile.
    Complements validate_dockerfile with actionable improvement suggestions.
    """
    try:
        dockerfile_path = os.path.abspath(os.path.expanduser(dockerfile_path))

        if not os.path.isfile(dockerfile_path):
            return f"Error: File '{dockerfile_path}' does not exist."

        with open(dockerfile_path, 'r') as f:
            content = f.read()
            lines = content.split('\n')

        result = f"=== Dockerfile Optimization Suggestions: {dockerfile_path} ===\n\n"

        suggestions = []

        # Check for multi-stage builds
        if content.count('FROM ') == 1:
            suggestions.append({
                'category': 'Build Optimization',
                'suggestion': 'Consider using multi-stage builds to reduce final image size',
                'example': 'FROM node:16 AS builder\nWORKDIR /app\n...\nFROM node:16-alpine\nCOPY --from=builder /app/dist /app'
            })

        # Check for specific base image tag
        if 'FROM' in content and ':latest' in content:
            suggestions.append({
                'category': 'Reproducibility',
                'suggestion': 'Avoid using :latest tag. Use specific version tags for reproducible builds',
                'example': 'FROM node:16.14.2-alpine instead of FROM node:latest'
            })

        # Check for layer optimization
        run_count = content.count('\nRUN ')
        if run_count > 5:
            suggestions.append({
                'category': 'Layer Optimization',
                'suggestion': f'Found {run_count} RUN commands. Consider combining related RUN commands to reduce layers',
                'example': 'RUN apt-get update && apt-get install -y \\\n    package1 \\\n    package2 && \\\n    rm -rf /var/lib/apt/lists/*'
            })

        # Check for .dockerignore
        dockerignore_path = os.path.join(os.path.dirname(dockerfile_path), '.dockerignore')
        if not os.path.exists(dockerignore_path):
            suggestions.append({
                'category': 'Build Context',
                'suggestion': 'Create a .dockerignore file to exclude unnecessary files from build context',
                'example': '.dockerignore content:\nnode_modules\n.git\n*.md\n.env'
            })

        # Check for COPY optimization
        if 'COPY . ' in content or 'ADD . ' in content:
            suggestions.append({
                'category': 'Cache Optimization',
                'suggestion': 'Copy dependency files first, then install, then copy source code for better cache utilization',
                'example': 'COPY package*.json ./\nRUN npm install\nCOPY . .'
            })

        # Check for non-root user
        if 'USER ' not in content:
            suggestions.append({
                'category': 'Security',
                'suggestion': 'Run container as non-root user for better security',
                'example': 'RUN addgroup -g 1001 appgroup && adduser -D -u 1001 -G appgroup appuser\nUSER appuser'
            })

        # Check for health check
        if 'HEALTHCHECK' not in content:
            suggestions.append({
                'category': 'Reliability',
                'suggestion': 'Add HEALTHCHECK instruction for container health monitoring',
                'example': 'HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\\n  CMD curl -f http://localhost:8080/health || exit 1'
            })

        # Check for apt-get cleanup
        if 'apt-get install' in content and 'rm -rf /var/lib/apt/lists' not in content:
            suggestions.append({
                'category': 'Image Size',
                'suggestion': 'Clean up apt cache after installing packages',
                'example': 'RUN apt-get update && apt-get install -y package && rm -rf /var/lib/apt/lists/*'
            })

        # Check for alpine base image
        if 'FROM' in content and 'alpine' not in content.lower() and 'scratch' not in content.lower():
            suggestions.append({
                'category': 'Image Size',
                'suggestion': 'Consider using Alpine-based images for smaller image size',
                'example': 'FROM node:16-alpine instead of FROM node:16'
            })

        # Display suggestions
        if suggestions:
            for i, suggestion in enumerate(suggestions, 1):
                result += f"{i}. [{suggestion['category']}] {suggestion['suggestion']}\n"
                result += f"   Example:\n"
                for line in suggestion['example'].split('\n'):
                    result += f"     {line}\n"
                result += "\n"

            result += f"Total suggestions: {len(suggestions)}\n"
        else:
            result += "✓ No obvious optimizations found. Dockerfile looks good!\n"

        result += "\n--- Additional Resources ---\n"
        result += "- Docker Best Practices: https://docs.docker.com/develop/develop-images/dockerfile_best-practices/\n"
        result += "- Use hadolint for comprehensive Dockerfile linting\n"

        return result
    except Exception as e:
        return f"Error analyzing Dockerfile: {e}"


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
