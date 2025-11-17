# Automated MCP Testing Agent

This project provides an automated testing agent powered by the Model Context Protocol (MCP).  
The agent connects a Python MCP server to a separate Java Maven codebase and can:

- Run Maven tests
- Parse JaCoCo coverage
- Generate JUnit 4 tests
- Improve test coverage
- Stage and commit changes
- Push to GitHub
- Create pull requests

The system behaves like a lightweight CI/CD assistant.

---

## Requirements
- Python 3.10+
- Java 8+
- Maven
- Git
- GitHub CLI (`gh`)
- VS Code (with MCP support)
- Python packages:
  - fastmcp
  - mcp[cli]
  - uvicorn
  - httpx

---

## Installation

### 1. Setup Python environment

uv init
uv venv
source .venv/bin/activate # or .venv\Scripts\Activate on Windows
uv add fastmcp mcp[cli] httpx uvicorn


### 2. Run the MCP server

The server will be available at:

http://127.0.0.1:8000/sse


### 3. Connect MCP to VS Code
1. Open VS Code  
2. Press Ctrl+Shift+P  
3. Choose "MCP: Add Server"  
4. Enter: http://127.0.0.1:8000/sse
5. Name it:


---

## Java Project Setup

Place this file inside your Java project:

.github/prompts/tester.prompt.md



---

## Using the Agent

Open your Java Maven project in VS Code.

Example Chat message:

Use the se333-testing-agent.
Project path: "C:/path/to/project/"
Coverage file: "C:/path/to/project/target/site/jacoco/jacoco.xml"
Run tests and improve coverage. Commit if coverage increases.


The agent will:
1. Run Maven tests  
2. Read JaCoCo coverage  
3. Identify low-coverage classes  
4. Generate JUnit 4 tests (basic or spec-based)  
5. Re-run tests  
6. Commit + push + PR if coverage improves  

---

## MCP Tools (Summary)

### Test & Coverage
- run_maven_tests(project_path)
- read_coverage(xml_path)

### Test Generation
- generate_unit_tests(source_file, test_dir)
- spec_based_test_generator(source_file, test_dir)

### Git Automation
- git_status(repo_path)
- git_add_all(repo_path)
- git_commit(repo_path, message, coverage)
- git_push(repo_path, remote)
- git_pull_request(repo_path, base, title, body)

---

## Notes
- Tests generated are JUnit 4 compatible.
- Commits to `main` or `master` are blocked.
- This project includes a specification-based generator as the required extension tool.

---


## Troubleshooting

### Agent not visible in VS Code:

Restart VS Code and confirm the MCP server is running.

### Coverage report missing:
Run:

mvn test

## Pull request creation fails

Authenticate GitHub CLI:

gh auth login

## Commit blocked

Ensure the current branch is not main or master.



