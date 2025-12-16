# DevOpsMCP-Server

# Local Infrastructure Auditor (MCP Server)

> **A "Shift-Left" DevOps companion that connects LLMs directly to your local infrastructure tooling.**

## 🚀 The Vision
As DevOps engineers, we often juggle dozens of CLI tools to ensure our code is secure, performant, and compliant. The **Local Infrastructure Auditor** is an implementation of the **Model Context Protocol (MCP)** that gives AI agents (like Claude) the ability to run these tools directly on your local machine.

Instead of copy-pasting error logs into a chatbot, this server allows the AI to:
1.  **Read** your local Infrastructure as Code (IaC) files safely.
2.  **Execute** industry-standard auditors (like `hadolint`, `checkov`, or `trufflehog`) locally.
3.  **Analyze** the output and suggest specific, context-aware fixes.

This project enforces the **Shift-Left** philosophy: catching configuration errors and security risks on the developer's machine *before* they ever reach the CI/CD pipeline.

---

## 🏗 Architecture
This project runs entirely on the local host to ensure data privacy and direct system access.

```mermaid
sequenceDiagram
    participant User
    participant LLM as Claude Desktop (Client)
    participant MCP as Python MCP Server
    participant CLI as Local CLI Tools (Docker/Checkov)

    User->>LLM: "Check my Dockerfile for errors."
    LLM->>MCP: Call Tool: validate_dockerfile()
    MCP->>CLI: Execute: hadolint ./Dockerfile
    CLI-->>MCP: Return: Warning DL3007 (Using latest tag)
    MCP-->>LLM: Return Tool Result
    LLM-->>User: "You are using the 'latest' tag. Here is why that is risky..."
