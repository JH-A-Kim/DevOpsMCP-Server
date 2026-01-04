import unittest
import subprocess
from unittest.mock import patch, MagicMock
from server import validate_dockerfile


class TestValidateDockerfile(unittest.TestCase):
    @patch("server.os.path.isfile", return_value=True)
    @patch("server.subprocess.run")
    def test_validate_dockerfile_valid(self, mock_run, mock_isfile):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = validate_dockerfile("path/to/valid/Dockerfile")
        self.assertEqual(result, "Dockerfile is valid and follows best practices.")

    @patch("server.os.path.isfile", return_value=True)
    @patch("server.subprocess.run")
    def test_validate_dockerfile_errors(self, mock_run, mock_isfile):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="Error: Invalid instruction"
        )

        result = validate_dockerfile("path/to/invalid/Dockerfile")
        self.assertEqual(result, "Dockerfile errors found:\nError: Invalid instruction")

    @patch("server.os.path.isfile", return_value=True)
    @patch("server.subprocess.run")
    def test_validate_dockerfile_issues(self, mock_run, mock_isfile):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="Warning: Use of latest tag", stderr=""
        )

        result = validate_dockerfile("path/to/issue/Dockerfile")
        self.assertEqual(result, "Dockerfile issues found:\nWarning: Use of latest tag")

    @patch("server.os.path.isfile", return_value=True)
    @patch("server.subprocess.run", side_effect=FileNotFoundError)
    def test_validate_dockerfile_hadolint_not_found(self, mock_run, mock_isfile):
        result = validate_dockerfile("path/to/Dockerfile")
        self.assertEqual(
            result,
            "Error: 'hadolint' is not installed or not found in PATH. "
            "Please install hadolint to validate Dockerfiles.",
        )

    @patch("server.os.path.isfile", return_value=True)
    @patch("server.subprocess.run", side_effect=Exception("Some unexpected error"))
    def test_validate_dockerfile_hadolint_unexpected_error(self, mock_run, mock_isfile):
        result = validate_dockerfile("path/to/Dockerfile")
        self.assertEqual(
            result,
            "Unexpected error while validating the Dockerfile: Some unexpected error",
        )

    @patch("server.os.path.isfile", return_value=True)
    @patch("server.subprocess.run")
    def test_validate_dockerfile_no_path(self, mock_run, mock_isfile):
        result = validate_dockerfile("")
        self.assertEqual(result, "Error: No path provided.")

    @patch("server.os.path.isfile", return_value=True)
    @patch(
        "server.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="hadolint", timeout=10),
    )
    def test_validate_dockerfile_timeout(self, mock_run, mock_isfile):
        result = validate_dockerfile("path/to/Dockerfile")
        self.assertEqual(result, "Error: Validation process timed out.")

    def test_validate_dockerfile_file_not_exist(self):
        path = "non/existent/path/Dockerfile"
        result = validate_dockerfile(path)
        self.assertTrue(f"Error: The file at path '{path}' does not exist.", result)


if __name__ == "__main__":
    unittest.main()
