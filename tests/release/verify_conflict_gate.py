"""Full conflict gate on immutable PR heads. No remote writes or cloud access."""
import itertools
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = "fae1d192aad6a0b9c447fb74bfe33a5bbb82d9d0"
HEADS = [
    ("14", "867130942074a04d77805a47de5baa4cc3a3fd96"),
    ("17", "8672dfdae562e1b2ce3344f9d913136f1c7ca651"),
    ("18", "3b489d114adbc9364a24b232fdc6504ee9eeaa58"),
    ("20", "e41209f8998c5979ba174fc7a2df9c9e2d0edd34"),
    ("21", "503280aa3a03ea74bcf33b913c5999de39a8d93f"),
    ("19", "2f57b6495f5f434a1e26985e7333b9439f0c5048"),
    ("22", "65c11e9861824cb3f7e24b6e30ece48bf186a158"),
    ("23", "fdfc4325eb18c9e5bd95d26f25b307f956c9657c"),
    ("24", "a981b2626deab860139b143a6b4029ce56a7998d"),
    ("25", "52786980409806d838b23d41d96d2b938068cd38"),
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
            assert model["feature_count"] == worker["feature_count"] == 21
            assert model["features"] == worker["features"]
            assert model["identifier"] == worker["identifier"]
            assert (candidate / "api/main.py").read_bytes() == blob(PINS["17"], "api/main.py")
            assert (candidate / ".gitignore").read_bytes() == blob(PINS["14"], ".gitignore")
            for path in ["README.md", "model/features.json", ".github/workflows/ci-ml.yml"]:
                assert (candidate / path).read_bytes() == blob(PINS["17"], path)
            assert git(candidate, "hash-object", "model/model-1.0.0.onnx").stdout.strip() == "2fc9e022b7029f293bdc3a471f68a91f4d7e57ec"
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
            print(f"RELEASE CHECK: image size {size} bytes; 45 pairs clean; 10 sequential merges clean", flush=True)
        finally:
            git(ROOT, "worktree", "remove", "--force", str(candidate), check=False)
            shutil.rmtree(candidate.parent, ignore_errors=True)
    finally:
        evidence.write_text(json.dumps({"base": BASE, "heads": HEADS, "pairs": pairs, "sequence": steps,
                                       "schema": "21-feature preview only"}, indent=2))
        assert git(ROOT, "rev-parse", "HEAD").stdout.strip() == old_head


if __name__ == "__main__":
    main()
