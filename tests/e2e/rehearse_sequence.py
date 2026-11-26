"""Sequential integration preview in a disposable worktree only.

No remote merges, ref updates or dataset downloads. Current 21-feature schema is
a test assumption, not a team decision. Unexpected conflicts fail closed.
"""
import json
import subprocess
from pathlib import Path
import tempfile
import shutil
import sys

BASE = "c423d6a79dcdeca319e0e7007d9f7d6394356961"
HEADS = [
    ("14", "867130942074a04d77805a47de5baa4cc3a3fd96"),
    ("17", "5886584331997d5b1b5fae7f6602c58d876f0221"),
    ("18", "3cb9ffe327abdd68a58cd2c9d23a6797ee2f5bf9"),
    ("20", "b81277f6d66a1d9e2b503e6fc54e7200732eb01f"),
    ("21", "503280aa3a03ea74bcf33b913c5999de39a8d93f"),
    ("19", "2f57b6495f5f434a1e26985e7333b9439f0c5048"),
    ("22", "52103dd0a8a8ee73bb55bdde6f5004de9f81b30c"),
    ("23", "fdfc4325eb18c9e5bd95d26f25b307f956c9657c"),
    ("24", "a981b2626deab860139b143a6b4029ce56a7998d"),
    ("25", "c2ac5cb11cf7b5ac010611bd689098895021da75"),
]
PINS = dict(HEADS)
ROOT = Path(__file__).resolve().parents[2]


def git(cwd, *args, check=True):
    return subprocess.run(["git", "-C", str(cwd), *args], text=True,
                          capture_output=True, check=check)


def content(sha, path):
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{sha}:{path}"])


def main():
    report = []
    old_head = git(ROOT, "rev-parse", "HEAD").stdout.strip()
    candidate = Path(tempfile.mkdtemp(prefix="dscc-preview-")) / "tree"
    try:
        git(ROOT, "worktree", "add", "--detach", str(candidate), BASE)
        git(candidate, "config", "user.name", "DSCC disposable integration")
        git(candidate, "config", "user.email", "preview@invalid.example")
        allowed = {"README.md", ".gitignore", "model/features.json", ".github/workflows/ci-ml.yml"}
        for number, sha in HEADS:
            result = git(candidate, "merge", "--no-ff", "--no-commit", sha, check=False)
            conflicts = git(candidate, "diff", "--name-only", "--diff-filter=U").stdout.splitlines()
            if result.returncode and (not conflicts or set(conflicts) - allowed):
                raise RuntimeError(f"PR {number}: unexpected conflict {conflicts}: {result.stderr}")
            for path in conflicts:
                # The original texts remain in their branches. Keep the union
                # of ignore rules, current API README and synchronized ML CI.
                source = {"README.md": "17", ".gitignore": "14",
                          "model/features.json": "18", ".github/workflows/ci-ml.yml": "17"}[path]
                (candidate / path).write_bytes(content(PINS[source], path))
                git(candidate, "add", "--", path)
            # Commit only into the detached disposable worktree.
            git(candidate, "commit", "-m", f"preview PR {number}", "--allow-empty")
            report.append({"pr": number, "sha": sha, "resolved": conflicts})
            print(f"PR #{number}: {'resolved '+', '.join(conflicts) if conflicts else 'clean'}", flush=True)
        # Canonical README proposal remains in docs; only the disposable tree
        # uses it at the root. No remote branch is overwritten.
        (candidate / "README.md").write_bytes((candidate / "docs/release-readme.md").read_bytes())
        model = json.loads((candidate / "model/features.json").read_text())
        worker = json.loads((candidate / "functions/contract/features.json").read_text())
        assert model["feature_count"] == worker["feature_count"] == 21
        assert model["features"] == worker["features"]
        assert model["identifier"] == worker["identifier"]
        # Ensure newer R1 API code survived the older R4 branch.
        assert (candidate / "api/main.py").read_bytes() == content(PINS["17"], "api/main.py")
        assert (candidate / ".gitignore").read_bytes() == content(PINS["14"], ".gitignore")
        # No training data fetched or tracked in the candidate's current tree.
        forbidden = git(candidate, "ls-files", "data/*", "Customer_Churn_Dataset.xlsx",
                        "model/test_split.csv").stdout.strip()
        assert not forbidden, f"Unexpected tracked dataset paths: {forbidden}"
        # Separate pytest processes prevent unrelated package names colliding.
        for args in [
            [sys.executable, "-m", "pip", "install", "-r", "api/requirements-dev.txt",
             "-r", "functions/requirements.txt", "ruff==0.9.10"],
            [sys.executable, "-m", "ruff", "check", "api", "functions"],
            [sys.executable, "-m", "pytest", "api/tests", "-q"],
            [sys.executable, "-m", "pytest", "functions/tests", "-q"],
            [sys.executable, "-m", "pytest", "tests/e2e/test_pipeline.py", "-q"],
            ["node", "--check", "web/app.js"],
            ["node", "--test", "tests/dashboard/test_data.cjs"],
            ["bash", "tests/observability/test_guards.sh"],
        ]:
            subprocess.run(args, cwd=candidate, check=True)
        (ROOT / "sequential-preview.json").write_text(json.dumps({
            "base": BASE, "prs": report, "schema": "21-feature preview only",
            "checks": ["schema equality", "API preservation", "ignore rules", "no tracked data",
                       "Ruff", "API pytest", "pipeline pytest", "ONNX E2E", "dashboard JS syntax and tests", "observability command guards"]
        }, indent=2))
    finally:
        git(ROOT, "worktree", "remove", "--force", str(candidate), check=False)
        shutil.rmtree(candidate.parent, ignore_errors=True)
        assert git(ROOT, "rev-parse", "HEAD").stdout.strip() == old_head


if __name__ == "__main__":
    main()
