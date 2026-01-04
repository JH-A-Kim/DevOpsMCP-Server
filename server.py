from mcp.server.fastmcp import FastMCP
import subprocess  # for running commands in terminal
import os

app = FastMCP("Local Infrastructure Auditor", "1.0.0")


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


if __name__ == "__main__":
    app.run(transport="stdio")
