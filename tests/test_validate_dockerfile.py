import unittest
from unittest.mock import patch, MagicMock
from server import validate_dockerfile


class TestValidateDockerfile(unittest.TestCase):
    @patch("server.subprocess.run")
    def test_validate_dockerfile_valid(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = validate_dockerfile("path/to/valid/Dockerfile")
        self.assertEqual(result, "Dockerfile is valid and follows best practices.")

    @patch("server.subprocess.run")
    def test_validate_dockerfile_errors(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="Error: Invalid instruction"
        )

        result = validate_dockerfile("path/to/invalid/Dockerfile")
        self.assertEqual(result, "Dockerfile errors found:\nError: Invalid instruction")

    @patch("server.subprocess.run")
    def test_validate_dockerfile_issues(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="Warning: Use of latest tag", stderr=""
        )

        result = validate_dockerfile("path/to/issue/Dockerfile")
        self.assertEqual(result, "Dockerfile issues found:\nWarning: Use of latest tag")


if __name__ == "__main__":
    unittest.main()
