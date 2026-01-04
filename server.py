from mcp.server.fastmcp import FastMCP
import subprocess  # for running commands in terminal

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
    This looks for Security risks and best practices in the actual Dockerfile.

    Args:
        path (str): Path to the Dockerfile.
    """

    try:
        if path == "":
            return "Error: No path provided."

        outcome = subprocess.run(["hadolint", path], capture_output=True, text=True)

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
    except Exception as e:
        return f"Unexpected error while validating the Dockerfile: {e}"


if __name__ == "__main__":
    app.run(transport="stdio")
