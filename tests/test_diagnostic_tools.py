import unittest
import os
import tempfile
from unittest.mock import patch, MagicMock
from server import (
    get_system_info,
    get_cpu_usage,
    get_memory_usage,
    get_disk_usage,
    list_processes,
    check_process_running,
    check_port_listening,
    get_network_stats,
    read_log_file,
    get_directory_size,
    get_environment_variable,
)


class TestSystemInfo(unittest.TestCase):
    def test_get_system_info(self):
        result = get_system_info()
        self.assertIn("System Information", result)
        self.assertIn("Os:", result)
        self.assertIn("Hostname:", result)
        self.assertIn("Uptime:", result)

    @patch("server.psutil.boot_time", side_effect=Exception("Test error"))
    def test_get_system_info_error(self, mock_boot):
        result = get_system_info()
        self.assertIn("Error retrieving system information", result)


class TestCPUUsage(unittest.TestCase):
    def test_get_cpu_usage(self):
        result = get_cpu_usage()
        self.assertIn("CPU Usage", result)
        self.assertIn("Overall CPU Usage:", result)
        self.assertIn("Physical Cores:", result)
        self.assertIn("Logical Cores:", result)

    @patch("server.psutil.cpu_percent", side_effect=Exception("Test error"))
    def test_get_cpu_usage_error(self, mock_cpu):
        result = get_cpu_usage()
        self.assertIn("Error retrieving CPU usage", result)


class TestMemoryUsage(unittest.TestCase):
    def test_get_memory_usage(self):
        result = get_memory_usage()
        self.assertIn("Memory Usage", result)
        self.assertIn("Total RAM:", result)
        self.assertIn("Available RAM:", result)
        self.assertIn("RAM Usage:", result)

    @patch("server.psutil.virtual_memory", side_effect=Exception("Test error"))
    def test_get_memory_usage_error(self, mock_mem):
        result = get_memory_usage()
        self.assertIn("Error retrieving memory usage", result)


class TestDiskUsage(unittest.TestCase):
    def test_get_disk_usage_default(self):
        result = get_disk_usage()
        self.assertIn("Disk Usage", result)
        self.assertIn("Total:", result)
        self.assertIn("Used:", result)
        self.assertIn("Free:", result)

    def test_get_disk_usage_custom_path(self):
        result = get_disk_usage("/tmp")
        self.assertIn("Disk Usage", result)
        self.assertIn("/tmp", result)

    def test_get_disk_usage_nonexistent_path(self):
        result = get_disk_usage("/nonexistent/path")
        self.assertIn("Error: Path", result)
        self.assertIn("does not exist", result)

    @patch("server.os.path.exists", return_value=True)
    @patch("server.psutil.disk_usage", side_effect=Exception("Test error"))
    def test_get_disk_usage_error(self, mock_disk, mock_exists):
        result = get_disk_usage("/")
        self.assertIn("Error retrieving disk usage", result)


class TestProcesses(unittest.TestCase):
    def test_list_processes(self):
        result = list_processes(5)
        self.assertIn("Top 5 Processes", result)
        self.assertIn("PID", result)
        self.assertIn("NAME", result)

    def test_list_processes_default_limit(self):
        result = list_processes()
        self.assertIn("Top 10 Processes", result)

    @patch("server.psutil.process_iter", side_effect=Exception("Test error"))
    def test_list_processes_error(self, mock_proc):
        result = list_processes()
        self.assertIn("Error listing processes", result)

    @patch("server.psutil.process_iter")
    def test_check_process_running_found(self, mock_proc_iter):
        mock_proc = MagicMock()
        mock_proc.info = {"pid": 123, "name": "python", "cmdline": ["python"]}
        mock_proc_iter.return_value = [mock_proc]

        result = check_process_running("python")
        self.assertIn("is RUNNING", result)
        self.assertIn("123", result)

    @patch("server.psutil.process_iter")
    def test_check_process_running_not_found(self, mock_proc_iter):
        mock_proc = MagicMock()
        mock_proc.info = {"pid": 123, "name": "bash", "cmdline": ["bash"]}
        mock_proc_iter.return_value = [mock_proc]

        result = check_process_running("nonexistent")
        self.assertIn("is NOT running", result)

    @patch("server.psutil.process_iter", side_effect=Exception("Test error"))
    def test_check_process_running_error(self, mock_proc):
        result = check_process_running("python")
        self.assertIn("Error checking process", result)


class TestPortChecking(unittest.TestCase):
    @patch("server.psutil.net_connections")
    def test_check_port_listening_open(self, mock_conn):
        mock_connection = MagicMock()
        mock_connection.laddr.port = 8080
        mock_connection.pid = 123
        mock_connection.status = "LISTEN"
        mock_conn.return_value = [mock_connection]

        with patch("server.psutil.Process") as mock_process:
            mock_process.return_value.name.return_value = "nginx"
            result = check_port_listening(8080)

        self.assertIn("is LISTENING", result)
        self.assertIn("8080", result)

    @patch("server.psutil.net_connections")
    @patch("server.socket.socket")
    def test_check_port_not_listening(self, mock_socket, mock_conn):
        mock_conn.return_value = []
        mock_sock_instance = MagicMock()
        mock_sock_instance.connect_ex.return_value = 1  # Connection refused
        mock_socket.return_value = mock_sock_instance

        result = check_port_listening(9999)
        self.assertIn("is NOT listening", result)

    @patch("server.psutil.net_connections", side_effect=Exception("Test error"))
    def test_check_port_error(self, mock_conn):
        result = check_port_listening(8080)
        self.assertIn("Error checking port", result)


class TestNetworkStats(unittest.TestCase):
    @patch("server.psutil.net_io_counters")
    def test_get_network_stats(self, mock_net):
        mock_stats = MagicMock()
        mock_stats.bytes_sent = 1024000
        mock_stats.bytes_recv = 2048000
        mock_stats.packets_sent = 100
        mock_stats.packets_recv = 200
        mock_stats.errin = 0
        mock_stats.errout = 0
        mock_net.return_value = {"eth0": mock_stats}

        result = get_network_stats()
        self.assertIn("Network Statistics", result)
        self.assertIn("eth0", result)
        self.assertIn("Bytes Sent:", result)

    @patch("server.psutil.net_io_counters", side_effect=Exception("Test error"))
    def test_get_network_stats_error(self, mock_net):
        result = get_network_stats()
        self.assertIn("Error retrieving network stats", result)


class TestLogFile(unittest.TestCase):
    def test_read_log_file(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            for i in range(100):
                f.write(f"Log line {i}\n")
            temp_file = f.name

        try:
            result = read_log_file(temp_file, lines=10)
            self.assertIn("Last 10 lines", result)
            self.assertIn("Log line 99", result)
        finally:
            os.unlink(temp_file)

    def test_read_log_file_with_search(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            f.write("ERROR: Something failed\n")
            f.write("INFO: Normal operation\n")
            f.write("ERROR: Another error\n")
            temp_file = f.name

        try:
            result = read_log_file(temp_file, search_term="ERROR")
            self.assertIn("matching lines", result)
            self.assertIn("ERROR", result)
            self.assertNotIn("INFO: Normal operation", result)
        finally:
            os.unlink(temp_file)

    def test_read_log_file_nonexistent(self):
        result = read_log_file("/nonexistent/file.log")
        self.assertIn("Error: File", result)
        self.assertIn("does not exist", result)

    @patch("server.os.path.getsize", return_value=11 * 1024 * 1024)
    @patch("server.os.path.isfile", return_value=True)
    def test_read_log_file_too_large(self, mock_isfile, mock_size):
        result = read_log_file("/some/large/file.log")
        self.assertIn("exceeds", result)
        self.assertIn("10 MB limit", result)


class TestDirectorySize(unittest.TestCase):
    def test_get_directory_size(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some test files
            for i in range(3):
                with open(os.path.join(tmpdir, f"file{i}.txt"), "w") as f:
                    f.write("x" * 1024)

            result = get_directory_size(tmpdir)
            self.assertIn("Directory Size", result)
            self.assertIn("Total Size:", result)
            self.assertIn("Files: 3", result)

    def test_get_directory_size_nonexistent(self):
        result = get_directory_size("/nonexistent/path")
        self.assertIn("Error: Path", result)
        self.assertIn("does not exist", result)

    def test_get_directory_size_not_directory(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name

        try:
            result = get_directory_size(temp_file)
            self.assertIn("is not a directory", result)
        finally:
            os.unlink(temp_file)


class TestEnvironmentVariable(unittest.TestCase):
    def test_get_specific_env_var(self):
        os.environ["TEST_VAR"] = "test_value"
        result = get_environment_variable("TEST_VAR")
        self.assertIn("TEST_VAR=test_value", result)

    def test_get_nonexistent_env_var(self):
        result = get_environment_variable("NONEXISTENT_VAR_12345")
        self.assertIn("is not set", result)

    def test_get_all_env_vars(self):
        result = get_environment_variable()
        self.assertIn("Environment Variables", result)
        # PATH should exist in most environments
        self.assertIn("PATH=", result)

    @patch("server.os.environ.get", side_effect=Exception("Test error"))
    def test_get_env_var_with_error(self, mock_get):
        result = get_environment_variable("TEST")
        self.assertIn("Error retrieving environment variable", result)


if __name__ == "__main__":
    unittest.main()
