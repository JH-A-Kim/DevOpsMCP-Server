from mcp.server.fastmcp import FastMCP

app = FastMCP("Local Infrastrcture Auditor", "1.0.0")


@app.tool()
def basic_greeting_test(name: str):
    """
    Test tool so I can test that this can properly be called
    from the client. (Claude Desktop)

    Args:
        name (str): Name to greet.
    """
    return f"Hello, {name}!"


if __name__ == "__main__":
    app.run(transport="stdio")
