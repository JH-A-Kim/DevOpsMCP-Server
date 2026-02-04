import unittest
import os
import tempfile
from unittest.mock import patch, MagicMock
from server import (
    # Docker tools
    list_docker_containers,
    inspect_docker_container,
    get_docker_logs,
    get_docker_stats,
    # Kubernetes tools
    list_k8s_pods,
    get_k8s_pod_logs,
    list_k8s_services,
    # Cloud provider tools
    list_aws_ec2_instances,
    get_aws_s3_buckets,
    list_azure_vms,
    list_gcp_instances,
    # Security scanning tools
    scan_with_trivy,
    scan_with_grype,
    scan_secrets,
    # Performance profiling tools
    get_io_stats,
    analyze_performance_metrics,
    # Automated remediation tools
    suggest_remediation,
    optimize_dockerfile,
)


# ============================================================================
# Docker Container Tests
# ============================================================================


class TestDockerContainers(unittest.TestCase):
    @patch("server.DOCKER_AVAILABLE", False)
    def test_list_docker_containers_not_available(self):
        result = list_docker_containers()
        self.assertIn("Docker library not installed", result)

    @patch("server.DOCKER_AVAILABLE", True)
    @patch("server.docker.from_env")
    def test_list_docker_containers_running(self, mock_docker):
        mock_container = MagicMock()
        mock_container.short_id = "abc123"
        mock_container.name = "test-container"
        mock_container.status = "running"
        mock_container.image.tags = ["nginx:latest"]
        mock_container.attrs = {"Created": "2024-01-01T00:00:00"}

        mock_client = MagicMock()
        mock_client.containers.list.return_value = [mock_container]
        mock_docker.return_value = mock_client

        result = list_docker_containers()
        self.assertIn("Docker Containers", result)
        self.assertIn("test-container", result)
        self.assertIn("running", result)

    @patch("server.DOCKER_AVAILABLE", True)
    @patch("server.docker.from_env")
    def test_list_docker_containers_empty(self, mock_docker):
        mock_client = MagicMock()
        mock_client.containers.list.return_value = []
        mock_docker.return_value = mock_client

        result = list_docker_containers()
        self.assertIn("No running containers found", result)

    @patch("server.DOCKER_AVAILABLE", True)
    @patch("server.docker.from_env")
    def test_inspect_docker_container(self, mock_docker):
        mock_container = MagicMock()
        mock_container.id = "container123"
        mock_container.name = "test-container"
        mock_container.status = "running"
        mock_container.attrs = {
            "Created": "2024-01-01T00:00:00",
            "Config": {"Image": "nginx:latest", "Env": ["PATH=/usr/bin", "HOME=/root"]},
            "NetworkSettings": {"Networks": {"bridge": {"IPAddress": "172.17.0.2", "Gateway": "172.17.0.1"}}},
            "HostConfig": {"PortBindings": {}},
            "Mounts": [],
        }

        mock_client = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_docker.return_value = mock_client

        result = inspect_docker_container("test-container")
        self.assertIn("Container Inspection", result)
        self.assertIn("test-container", result)
        self.assertIn("nginx:latest", result)

    @patch("server.DOCKER_AVAILABLE", True)
    @patch("server.docker.from_env")
    def test_get_docker_logs(self, mock_docker):
        mock_container = MagicMock()
        mock_container.name = "test-container"
        mock_container.logs.return_value = b"Log line 1\nLog line 2\n"

        mock_client = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_docker.return_value = mock_client

        result = get_docker_logs("test-container", lines=50)
        self.assertIn("Docker Logs", result)
        self.assertIn("Log line 1", result)
        self.assertIn("Log line 2", result)

    @patch("server.DOCKER_AVAILABLE", True)
    @patch("server.docker.from_env")
    def test_get_docker_stats(self, mock_docker):
        mock_container = MagicMock()
        mock_container.name = "test-container"
        mock_container.stats.return_value = {
            "cpu_stats": {
                "cpu_usage": {"total_usage": 1000000},
                "system_cpu_usage": 10000000,
                "online_cpus": 2,
            },
            "precpu_stats": {
                "cpu_usage": {"total_usage": 500000},
                "system_cpu_usage": 9000000,
            },
            "memory_stats": {"usage": 104857600, "limit": 1073741824},
            "networks": {"eth0": {"rx_bytes": 1048576, "tx_bytes": 524288}},
            "blkio_stats": {
                "io_service_bytes_recursive": [
                    {"op": "Read", "value": 1048576},
                    {"op": "Write", "value": 524288},
                ]
            },
        }

        mock_client = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_docker.return_value = mock_client

        result = get_docker_stats("test-container")
        self.assertIn("Container Stats", result)
        self.assertIn("CPU Usage", result)
        self.assertIn("Memory Usage", result)


# ============================================================================
# Kubernetes Tests
# ============================================================================


class TestKubernetes(unittest.TestCase):
    @patch("server.KUBERNETES_AVAILABLE", False)
    def test_list_k8s_pods_not_available(self):
        result = list_k8s_pods()
        self.assertIn("Kubernetes library not installed", result)

    @patch("server.KUBERNETES_AVAILABLE", True)
    @patch("server.config.load_kube_config")
    @patch("server.client.CoreV1Api")
    def test_list_k8s_pods(self, mock_api, mock_config):
        mock_pod = MagicMock()
        mock_pod.metadata.name = "test-pod"
        mock_pod.metadata.namespace = "default"
        mock_pod.status.phase = "Running"
        mock_pod.spec.node_name = "node-1"
        mock_pod.status.pod_ip = "10.0.0.1"
        mock_pod.status.container_statuses = [MagicMock(name="app", ready=True, restart_count=0)]

        mock_list = MagicMock()
        mock_list.items = [mock_pod]

        mock_v1 = MagicMock()
        mock_v1.list_namespaced_pod.return_value = mock_list
        mock_api.return_value = mock_v1

        result = list_k8s_pods(namespace="default")
        self.assertIn("Kubernetes Pods", result)
        self.assertIn("test-pod", result)
        self.assertIn("Running", result)

    @patch("server.KUBERNETES_AVAILABLE", True)
    @patch("server.config.load_kube_config")
    @patch("server.client.CoreV1Api")
    def test_get_k8s_pod_logs(self, mock_api, mock_config):
        mock_v1 = MagicMock()
        mock_v1.read_namespaced_pod_log.return_value = "Pod log line 1\nPod log line 2"
        mock_api.return_value = mock_v1

        result = get_k8s_pod_logs("test-pod", namespace="default", lines=100)
        self.assertIn("Kubernetes Pod Logs", result)
        self.assertIn("Pod log line 1", result)

    @patch("server.KUBERNETES_AVAILABLE", True)
    @patch("server.config.load_kube_config")
    @patch("server.client.CoreV1Api")
    def test_list_k8s_services(self, mock_api, mock_config):
        mock_svc = MagicMock()
        mock_svc.metadata.name = "test-service"
        mock_svc.metadata.namespace = "default"
        mock_svc.spec.type = "ClusterIP"
        mock_svc.spec.cluster_ip = "10.0.0.100"
        mock_svc.spec.ports = [MagicMock(name="http", port=80, target_port=8080, protocol="TCP")]
        mock_svc.status.load_balancer.ingress = None

        mock_list = MagicMock()
        mock_list.items = [mock_svc]

        mock_v1 = MagicMock()
        mock_v1.list_namespaced_service.return_value = mock_list
        mock_api.return_value = mock_v1

        result = list_k8s_services(namespace="default")
        self.assertIn("Kubernetes Services", result)
        self.assertIn("test-service", result)
        self.assertIn("ClusterIP", result)


# ============================================================================
# Cloud Provider Tests
# ============================================================================


class TestCloudProviders(unittest.TestCase):
    @patch("server.AWS_AVAILABLE", False)
    def test_list_aws_ec2_not_available(self):
        result = list_aws_ec2_instances()
        self.assertIn("boto3 library not installed", result)

    @patch("server.AWS_AVAILABLE", True)
    @patch("server.boto3.client")
    def test_list_aws_ec2_instances(self, mock_boto):
        mock_ec2 = MagicMock()
        mock_ec2.describe_instances.return_value = {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-12345",
                            "InstanceType": "t2.micro",
                            "State": {"Name": "running"},
                            "PrivateIpAddress": "10.0.0.1",
                            "PublicIpAddress": "54.1.2.3",
                            "LaunchTime": "2024-01-01T00:00:00",
                            "Tags": [{"Key": "Name", "Value": "test-instance"}],
                        }
                    ]
                }
            ]
        }
        mock_boto.return_value = mock_ec2

        result = list_aws_ec2_instances(region="us-east-1")
        self.assertIn("AWS EC2 Instances", result)
        self.assertIn("i-12345", result)
        self.assertIn("t2.micro", result)
        self.assertIn("running", result)

    @patch("server.AWS_AVAILABLE", True)
    @patch("server.boto3.client")
    def test_get_aws_s3_buckets(self, mock_boto):
        mock_s3 = MagicMock()
        mock_s3.list_buckets.return_value = {"Buckets": [{"Name": "my-bucket", "CreationDate": "2024-01-01T00:00:00"}]}
        mock_boto.return_value = mock_s3

        result = get_aws_s3_buckets()
        self.assertIn("AWS S3 Buckets", result)
        self.assertIn("my-bucket", result)

    @patch("server.AZURE_AVAILABLE", False)
    def test_list_azure_vms_not_available(self):
        result = list_azure_vms("subscription-id")
        self.assertIn("Azure libraries not installed", result)

    @patch("server.GCP_AVAILABLE", False)
    def test_list_gcp_instances_not_available(self):
        result = list_gcp_instances("project-id")
        self.assertIn("Google Cloud libraries not installed", result)


# ============================================================================
# Security Scanning Tests
# ============================================================================


class TestSecurityScanning(unittest.TestCase):
    @patch("server.subprocess.run")
    def test_scan_with_trivy_not_installed(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        result = scan_with_trivy("nginx:latest")
        self.assertIn("Trivy is not installed", result)

    @patch("server.subprocess.run")
    def test_scan_with_trivy_success(self, mock_run):
        # First call checks if trivy is installed
        check_result = MagicMock(returncode=0)
        # Second call runs the scan
        scan_result = MagicMock(returncode=0, stdout="Total: 0 (HIGH: 0, CRITICAL: 0)")
        mock_run.side_effect = [check_result, scan_result]

        result = scan_with_trivy("nginx:latest")
        self.assertIn("Trivy Security Scan", result)
        self.assertIn("nginx:latest", result)

    @patch("server.subprocess.run")
    def test_scan_with_grype_not_installed(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        result = scan_with_grype("nginx:latest")
        self.assertIn("Grype is not installed", result)

    def test_scan_secrets_nonexistent_path(self):
        result = scan_secrets("/nonexistent/path")
        self.assertIn("does not exist", result)

    def test_scan_secrets_in_temp_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("api_key = 'AKIAIOSFODNN7EXAMPLE'\n")
            f.write("secret = 'my_secret_password_1234567890'\n")
            temp_path = f.name

        try:
            result = scan_secrets(temp_path)
            self.assertIn("Secret Scanning", result)
            # Should find at least one pattern
            self.assertIn("potential secret", result.lower())
        finally:
            os.unlink(temp_path)


# ============================================================================
# Performance Profiling Tests
# ============================================================================


class TestPerformanceProfiling(unittest.TestCase):
    def test_get_io_stats(self):
        result = get_io_stats()
        self.assertIn("Disk I/O Statistics", result)
        self.assertIn("Read Count", result)
        self.assertIn("Write Count", result)

    @patch("server.psutil.disk_io_counters", side_effect=Exception("Test error"))
    def test_get_io_stats_error(self, mock_io):
        result = get_io_stats()
        self.assertIn("Error retrieving I/O stats", result)

    @patch("server.psutil.cpu_percent")
    @patch("server.psutil.virtual_memory")
    @patch("server.psutil.net_io_counters")
    def test_analyze_performance_metrics(self, mock_net, mock_mem, mock_cpu):
        mock_cpu.return_value = 50.0
        mock_mem.return_value = MagicMock(percent=60.0)
        mock_net.return_value = MagicMock(bytes_sent=1000, bytes_recv=2000)

        result = analyze_performance_metrics(duration=1)
        self.assertIn("Performance Analysis", result)
        self.assertIn("CPU Usage", result)
        self.assertIn("Memory Usage", result)
        self.assertIn("Network Activity", result)


# ============================================================================
# Automated Remediation Tests
# ============================================================================


class TestAutomatedRemediation(unittest.TestCase):
    def test_suggest_remediation_high_cpu(self):
        result = suggest_remediation("high_cpu")
        self.assertIn("High CPU Usage", result)
        self.assertIn("Immediate Actions", result)
        self.assertIn("Investigation Steps", result)
        self.assertIn("Long-term Solutions", result)

    def test_suggest_remediation_disk_full(self):
        result = suggest_remediation("disk_full")
        self.assertIn("Disk Full", result)
        self.assertIn("Immediate Actions", result)

    def test_suggest_remediation_pod_crash(self):
        result = suggest_remediation("pod_crash")
        self.assertIn("Pod Crash", result)
        self.assertIn("OOMKilled", result)

    def test_suggest_remediation_unknown_issue(self):
        result = suggest_remediation("unknown_issue")
        self.assertIn("No specific remediation found", result)
        self.assertIn("General Best Practices", result)

    def test_suggest_remediation_with_details(self):
        result = suggest_remediation("high_cpu", details="CPU usage at 95% for 10 minutes")
        self.assertIn("Additional Context", result)
        self.assertIn("CPU usage at 95%", result)

    def test_optimize_dockerfile_nonexistent(self):
        result = optimize_dockerfile("/nonexistent/Dockerfile")
        self.assertIn("does not exist", result)

    def test_optimize_dockerfile_suggestions(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix="Dockerfile", delete=False) as f:
            f.write("FROM node:latest\n")
            f.write("COPY . /app\n")
            f.write("RUN apt-get update\n")
            f.write("RUN apt-get install -y vim\n")
            temp_path = f.name

        try:
            result = optimize_dockerfile(temp_path)
            self.assertIn("Dockerfile Optimization Suggestions", result)
            # Should suggest avoiding :latest tag
            self.assertIn("latest", result.lower())
        finally:
            os.unlink(temp_path)

    def test_optimize_dockerfile_good_practices(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix="Dockerfile", delete=False) as f:
            f.write("FROM node:16-alpine AS builder\n")
            f.write("WORKDIR /app\n")
            f.write("COPY package*.json ./\n")
            f.write("RUN npm install\n")
            f.write("COPY . .\n")
            f.write("FROM node:16-alpine\n")
            f.write("WORKDIR /app\n")
            f.write("COPY --from=builder /app /app\n")
            f.write("USER node\n")
            f.write("HEALTHCHECK CMD curl -f http://localhost:3000/health\n")
            temp_path = f.name

        try:
            result = optimize_dockerfile(temp_path)
            self.assertIn("Dockerfile Optimization Suggestions", result)
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    unittest.main()
