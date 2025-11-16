# server.py
from asyncio import subprocess
from fastmcp import FastMCP
import subprocess
import xml.etree.ElementTree as ET
import re
import os

mcp = FastMCP("Demo 🚀")

@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


@mcp.tool()
def run_maven_tests(project_path: str = ".") -> dict:
    """
    Run `mvn test` inside the given project_path.
    Returns stdout, stderr, return code, and a simple parsed summary.
    """
    try:
        result = subprocess.run(
            ["mvn", "test"],
            cwd=project_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stdout = result.stdout
        stderr = result.stderr

        # Very simple parsing: look for lines like:
        # "Tests run: 10, Failures: 1, Errors: 0, Skipped: 0"
        summary = {}
        for line in stdout.splitlines():
            line = line.strip()
            if line.startswith("Tests run:") and "Failures:" in line:
                # Split by commas and parse numbers
                # Example: "Tests run: 10, Failures: 1, Errors: 0, Skipped: 0"
                parts = [p.strip() for p in line.split(",")]
                for p in parts:
                    if ":" in p:
                        key, val = p.split(":", 1)
                        summary[key.strip().lower().replace(" ", "_")] = int(val.strip())
                break

        return {
            "stdout": stdout,
            "stderr": stderr,
            "returncode": result.returncode,
            "summary": summary or None
        }

    except Exception as e:
        return {"error": str(e)}



@mcp.tool()
def read_coverage(xml_path: str) -> dict:
    """
    Parse JaCoCo XML and extract coverage percentages.
    Also identify low-covered classes and suggest where to add tests.
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        totals = {
            "INSTRUCTION": {"missed": 0, "covered": 0},
            "LINE": {"missed": 0, "covered": 0},
            "BRANCH": {"missed": 0, "covered": 0},
        }

        # Aggregate totals
        for counter in root.iter("counter"):
            ctype = counter.get("type")
            if ctype in totals:
                totals[ctype]["missed"] += int(counter.get("missed"))
                totals[ctype]["covered"] += int(counter.get("covered"))

        def pct(covered, missed):
            total = covered + missed
            return round(100 * covered / total, 2) if total else 0.0

        overall = {
            "line_coverage": pct(totals["LINE"]["covered"], totals["LINE"]["missed"]),
            "branch_coverage": pct(totals["BRANCH"]["covered"], totals["BRANCH"]["missed"]),
            "instruction_coverage": pct(totals["INSTRUCTION"]["covered"], totals["INSTRUCTION"]["missed"]),
        }

        # Per-class coverage and low coverage detection
        class_coverages = []
        for pkg in root.findall("package"):
            pkg_name = pkg.get("name")
            for cls in pkg.findall("class"):
                cls_name = cls.get("name")
                line_counter = None
                for counter in cls.findall("counter"):
                    if counter.get("type") == "LINE":
                        line_counter = counter
                        break
                if line_counter is None:
                    continue

                missed = int(line_counter.get("missed"))
                covered = int(line_counter.get("covered"))
                line_cov = pct(covered, missed)

                class_coverages.append({
                    "package": pkg_name,
                    "class": cls_name,
                    "line_coverage": line_cov,
                    "missed_lines": missed,
                    "covered_lines": covered,
                })

        # Identify low coverage classes (for example, under 50 percent)
        low_covered = [c for c in class_coverages if c["line_coverage"] < 50.0]

        # Simple recommendations
        recommendations = []
        for c in sorted(low_covered, key=lambda x: x["line_coverage"]):
            recommendations.append(
                f"Increase tests for {c['package']}.{c['class']} "
                f"(line coverage {c['line_coverage']}%, missed lines {c['missed_lines']})."
            )

        return {
            "overall": overall,
            "raw_totals": totals,
            "class_coverages": class_coverages,
            "low_coverage_classes": low_covered,
            "recommendations": recommendations,
        }

    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def git_status(repo_path: str) -> dict:
    """
    Return Git status information:
    - clean/untracked files
    - staged changes
    - merge conflicts
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        lines = result.stdout.splitlines()

        staged = []
        unstaged = []
        untracked = []
        conflicts = []

        for line in lines:
            code = line[:2]
            file = line[3:]

            if code == "??":
                untracked.append(file)
            elif code.strip() == "UU":
                conflicts.append(file)
            elif code[0] != " ":
                staged.append(file)
            else:
                unstaged.append(file)

        return {
            "staged": staged,
            "unstaged": unstaged,
            "untracked": untracked,
            "conflicts": conflicts
        }

    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def git_add_all(repo_path: str) -> dict:
    """
    Stage all meaningful changes.
    Excludes build artifacts and temporary files.
    """
    ignore_patterns = ["target/", ".idea/", ".vscode/", ".DS_Store"]
    ignore_ext = [".class", ".log"]

    try:
        # Git ls-files shows all modified/untracked files
        result = subprocess.run(
            ["git", "ls-files", "--others", "--modified", "--deleted", "--exclude-standard"],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            text=True
        )

        files = result.stdout.splitlines()
        staged = []

        for f in files:
            if any(f.startswith(p) for p in ignore_patterns):
                continue
            if any(f.endswith(ext) for ext in ignore_ext):
                continue

            subprocess.run(["git", "add", f], cwd=repo_path)
            staged.append(f)

        return {
            "message": "Staged filtered files",
            "count": len(staged),
            "files": staged
        }

    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def git_commit(repo_path: str, message: str, coverage: dict) -> dict:
    """
    Commit staged changes.
    coverage:
      { line_coverage: float, branch_coverage: float }
    """
    try:
        # Protect main branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            text=True
        )
        branch = result.stdout.strip()
        if branch in ("main", "master"):
            return {"error": "Direct commits to main/master are blocked."}

        line_cov = coverage.get("line_coverage", "N/A")
        branch_cov = coverage.get("branch_coverage", "N/A")

        commit_msg = f"{message}\n\nCoverage:\n- Line: {line_cov}%\n- Branch: {branch_cov}%"

        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        return {
            "message": "Commit successful",
            "stdout": result.stdout,
            "stderr": result.stderr
        }

    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def git_push(repo_path: str, remote: str = "origin") -> dict:
    try:
        # Set upstream automatically
        subprocess.run(
            ["git", "push", "-u", remote, "HEAD"],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        return {"message": "Push complete"}

    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def git_pull_request(repo_path: str, base: str = "main",
                     title: str = "Automated Test/Coverage Update",
                     body: str = "") -> dict:
    """
    Create a pull request using GitHub CLI.
    Requires GitHub CLI installed and authenticated.
    """
    try:
        pr_body = f"{body}\n\nAutomated testing agent update."

        result = subprocess.run(
            ["gh", "pr", "create",
             "--base", base,
             "--title", title,
             "--body", pr_body],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        return {
            "message": "Pull request created",
            "output": result.stdout.strip()
        }

    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def spec_based_test_generator(source_file: str, test_dir: str) -> dict:
    """
    Generate a more advanced, spec-based set of JUnit tests using:
    - equivalence classes
    - boundary values
    - invalid inputs

    This extension tool tries to understand the method signatures and produce
    stronger tests than the basic generator.
    """

    try:
        with open(source_file, "r") as f:
            code = f.read()

        # Extract class name
        class_match = re.search(r"class\s+(\w+)", code)
        if not class_match:
            return {"error": "Class name not found."}
        class_name = class_match.group(1)

        # Extract method signatures
        # Example matched:
        # public int add(int a, int b)
        method_pattern = r"public\s+([\w<>]+)\s+(\w+)\s*\(([^)]*)\)"
        methods = re.findall(method_pattern, code)

        if not os.path.exists(test_dir):
            os.makedirs(test_dir)

        test_file_path = os.path.join(test_dir, f"{class_name}SpecTest.java")

        # Start building test file
        test_code = f"""
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class {class_name}SpecTest {{

    {class_name} obj = new {class_name}();
"""

        # Parameter value sets
        boundary_values = ["0", "1", "-1", "Integer.MAX_VALUE", "Integer.MIN_VALUE"]

        for return_type, method_name, params in methods:
            params = params.strip()
            param_list = []

            if params:
                raw_params = [p.strip() for p in params.split(",")]
                for p in raw_params:
                    # "int a" -> type="int", name="a"
                    pieces = p.split()
                    if len(pieces) >= 2:
                        p_type, p_name = pieces[-2], pieces[-1]
                        param_list.append((p_type, p_name))

            # Test header
            test_code += f"""

    @Test
    void test_{method_name}_equivalence_and_boundaries() {{
"""

            # Generate value combinations
            if param_list:
                test_code += "        // Equivalence classes & boundary testing\n"
                for p_type, p_name in param_list:
                    if p_type in ("int", "Integer"):
                        for val in boundary_values:
                            test_code += f"        // Test {method_name} with {p_name} = {val}\n"
                            args = []
                            for p_type2, p_name2 in param_list:
                                if p_name2 == p_name:
                                    args.append(val)
                                else:
                                    args.append("1")  # default
                            arg_string = ", ".join(args)
                            test_code += f"        assertDoesNotThrow(() -> obj.{method_name}({arg_string}));\n"

                # Invalid input testing (if parameters are objects)
                test_code += "        // Invalid input tests\n"
                for p_type, p_name in param_list:
                    if p_type not in ("int", "double", "boolean", "float", "long"):
                        test_code += f"        assertThrows(Exception.class, () -> obj.{method_name}(null));\n"

            test_code += "    }\n"

        test_code += "\n}\n"

        with open(test_file_path, "w") as f:
            f.write(test_code)

        return {
            "message": "Spec-based test file generated",
            "test_file": test_file_path,
            "methods_analyzed": [m[1] for m in methods]
        }

    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    mcp.run(transport="sse")