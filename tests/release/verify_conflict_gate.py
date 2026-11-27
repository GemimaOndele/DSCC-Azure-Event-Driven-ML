"""Full conflict gate on immutable PR heads. No remote writes or cloud access."""
import itertools
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = "fae1d192aad6a0b9c447fb74bfe33a5bbb82d9d0"
HEADS = [
    ("24", "78ac96d138b2e565935e92138ea60d089d27c0ec"),
    ("14", "131fd715f67a983169451be9492a9b8d1e2b74f1"),
    ("17", "846a697d70fb388cfb9f983bf3b2c14e0a019c2f"),
    ("18", "e7d827263c9dc305656016568be9f8c99ed8f71a"),
    ("20", "65ff2d2ee0e15c41db43fe715be295abbf005229"),
    ("21", "d4e51388cb6979261867fd728748ad7b0f43dbd6"),
    ("19", "c8528772930cd35e1099c43701672b90bd77a5c1"),
    ("22", "8f41a990bfbc34a390003ae2d6704dd6e9105285"),
    ("23", "57436cb1f4923d61c7d5a79ad5bd64dd571bfbfd"),
    # The workflow passes the reviewed PR head so this self-referential PR is
    # not validated against a stale pre-commit SHA.
    ("25", os.environ.get("PR25_HEAD") or "7b06dfba01790a7fbf5859d8493bb70a765c28a1"),
]
PINS = dict(HEADS)


def git(cwd, *args, check=True):
    return subprocess.run(["git", "-C", str(cwd), *args], text=True,
                          capture_output=True, check=check)


def blob(sha, path):
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{sha}:{path}"])


def main():
    old_head = git(ROOT, "rev-parse", "HEAD").stdout.strip()
    pairs = []
    steps = []
    evidence = ROOT / "release-conflict-gate.json"
    try:
        # All C(10,2) pairs, rather than only the original 12.
        for (a, x), (b, y) in itertools.combinations(HEADS, 2):
            result = git(ROOT, "merge-tree", "--write-tree", "--name-only",
                         "--no-messages", x, y, check=False)
            if result.returncode not in (0, 1):
                raise RuntimeError(result.stderr)
            paths = result.stdout.splitlines()[1:] if result.returncode else []
            pairs.append({"pair": [a,b], "conflict": result.returncode == 1, "paths": paths})
            print(f"PAIR #{a}/#{b}: {'CONFLICT '+', '.join(paths) if result.returncode else 'clean'}", flush=True)
        assert not any(row["conflict"] for row in pairs), "Pairwise conflicts remain"

        candidate = Path(tempfile.mkdtemp(prefix="dscc-release-")) / "tree"
        try:
            git(ROOT, "worktree", "add", "--detach", str(candidate), BASE)
            git(candidate, "config", "user.name", "DSCC disposable preview")
            git(candidate, "config", "user.email", "preview@invalid.example")
            for number, sha in HEADS:
                result = git(candidate, "merge", "--no-ff", "--no-commit", sha, check=False)
                conflicts = git(candidate, "diff", "--name-only", "--diff-filter=U").stdout.splitlines()
                steps.append({"pr": number, "sha": sha, "conflicts": conflicts, "exit": result.returncode})
                assert result.returncode == 0 and not conflicts, f"PR #{number}: {conflicts} {result.stderr}"
                git(candidate, "commit", "-m", f"disposable preview PR #{number}", "--allow-empty")
                print(f"SEQUENCE #{number}: clean; no manual resolution", flush=True)
            model = json.loads((candidate / "model/features.json").read_text())
            worker = json.loads((candidate / "functions/contract/features.json").read_text())
            assert model == worker
            assert model["feature_count"] == 19 and model["model_version"] == "1.1.0"
            assert {"numAdminTickets", "numTechTickets"}.isdisjoint(f["name"] for f in model["features"])
            assert model["features"] == worker["features"]
            assert model["identifier"] == worker["identifier"]
            assert (candidate / "api/main.py").read_bytes() == blob(PINS["17"], "api/main.py")
            assert (candidate / ".gitignore").read_bytes() == blob(PINS["14"], ".gitignore")
            for path in ["README.md", "model/features.json", ".github/workflows/ci-ml.yml"]:
                assert (candidate / path).read_bytes() == blob(PINS["17"], path)
            assert git(candidate, "hash-object", "model/model-1.1.0.onnx").stdout.strip() == "09ee933f16731e7218189d19d7c3ab98162de34e"
            assert not (candidate / "model/model-1.0.0.onnx").exists()
            assert not git(candidate, "ls-files", "data/*", "Customer_Churn_Dataset.xlsx",
                           "model/test_split.csv").stdout.strip()
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
                ["docker", "build", "-f", "api/Dockerfile", "-t", "dscc-release-preview:local", "."],
            ]:
                subprocess.run(args, cwd=candidate, check=True)
            size = int(subprocess.check_output(
                ["docker", "image", "inspect", "dscc-release-preview:local", "--format", "{{.Size}}"],
                text=True).strip())
            assert size < 500000000, f"Image too large: {size}"
            print(f"RELEASE CHECK: image size {size} bytes; {len(pairs)} pairs clean; {len(steps)} sequential merges clean", flush=True)
        finally:
            git(ROOT, "worktree", "remove", "--force", str(candidate), check=False)
            shutil.rmtree(candidate.parent, ignore_errors=True)
    finally:
        evidence.write_text(json.dumps({"base": BASE, "heads": HEADS, "pairs": pairs, "sequence": steps,
                                       "schema": "19-feature 1.1.0 preview only"}, indent=2))
        assert git(ROOT, "rev-parse", "HEAD").stdout.strip() == old_head


if __name__ == "__main__":
    main()
