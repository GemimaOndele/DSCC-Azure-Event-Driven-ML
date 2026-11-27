"""Sequential integration preview of model 1.1.0; fail closed, no remote writes."""
import json
import os
import subprocess
from pathlib import Path
import tempfile
import shutil
import sys

BASE = "c67bafc929eda90abf27d91c69f1257661f8e7e9"
HEADS = [
    ("24", "78ac96d138b2e565935e92138ea60d089d27c0ec"),
    ("26", "a3f5b23387777b0c18754ba4db2468bf20a140c4"),
    ("14", "131fd715f67a983169451be9492a9b8d1e2b74f1"),
    ("17", "846a697d70fb388cfb9f983bf3b2c14e0a019c2f"),
    ("18", "e7d827263c9dc305656016568be9f8c99ed8f71a"),
    ("20", "65ff2d2ee0e15c41db43fe715be295abbf005229"),
    ("21", "d4e51388cb6979261867fd728748ad7b0f43dbd6"),
    ("19", "c8528772930cd35e1099c43701672b90bd77a5c1"),
    ("22", os.environ.get("PR22_HEAD", "8f41a990bfbc34a390003ae2d6704dd6e9105285")),
    ("23", "478bc82a66dcaef82827ffe50567b8d43aa6d69b"),
    ("25", "ccafaf9ef35c51e12bc5c0e0f4ea6efe18c11968"),
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
    before = git(ROOT, "status", "--porcelain").stdout
    evidence = Path(os.environ.get("DSCC_REPORT_DIR") or tempfile.mkdtemp(prefix="dscc-evidence-"))
    evidence.mkdir(parents=True, exist_ok=True)
    assert ROOT not in evidence.resolve().parents and evidence.resolve() != ROOT
    old_head = git(ROOT, "rev-parse", "HEAD").stdout.strip()
    candidate = Path(tempfile.mkdtemp(prefix="dscc-preview-")) / "tree"
    try:
        git(ROOT, "worktree", "add", "--detach", str(candidate), BASE)
        git(candidate, "config", "user.name", "DSCC disposable integration")
        git(candidate, "config", "user.email", "preview@invalid.example")
        for number, sha in HEADS:
            if number in {"24", "26"}:
                git(ROOT, "merge-base", "--is-ancestor", sha, BASE)
                report.append({"pr": number, "sha": sha, "already_merged": True})
                print(f"PR #{number}: existing merge verified", flush=True)
                continue
            result = git(candidate, "merge", "--no-ff", "--no-commit", sha, check=False)
            conflicts = git(candidate, "diff", "--name-only", "--diff-filter=U").stdout.splitlines()
            assert result.returncode == 0 and not conflicts, f"PR #{number}: {conflicts} {result.stderr}"
            # Commit only into the detached disposable worktree.
            git(candidate, "commit", "-m", f"preview PR {number}", "--allow-empty")
            report.append({"pr": number, "sha": sha, "resolved": conflicts})
            print(f"PR #{number}: {'resolved '+', '.join(conflicts) if conflicts else 'clean'}", flush=True)
        model = json.loads((candidate / "model/features.json").read_text())
        worker = json.loads((candidate / "functions/contract/features.json").read_text())
        assert model == worker
        count = model["feature_count"]
        version = model["model_version"]
        assert type(count) is int and count == len(model["features"]) > 0
        assert version == "1.1.0" and count == 19
        assert {"numAdminTickets", "numTechTickets"}.isdisjoint(f["name"] for f in model["features"])
        assert git(candidate, "hash-object", f"model/model-{version}.onnx").stdout.strip() == "09ee933f16731e7218189d19d7c3ab98162de34e"
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
        (evidence / "sequential-preview.json").write_text(json.dumps({
            "base": BASE, "prs": report, "schema": {"model_version": version, "feature_count": count},
            "checks": ["schema equality", "API preservation", "ignore rules", "no tracked data",
                       "Ruff", "API pytest", "pipeline pytest", "ONNX E2E", "dashboard JS syntax and tests", "observability command guards"]
        }, indent=2))
    finally:
        git(ROOT, "worktree", "remove", "--force", str(candidate), check=False)
        shutil.rmtree(candidate.parent, ignore_errors=True)
        assert git(ROOT, "rev-parse", "HEAD").stdout.strip() == old_head
        assert git(ROOT, "status", "--porcelain").stdout == before


if __name__ == "__main__":
    main()
