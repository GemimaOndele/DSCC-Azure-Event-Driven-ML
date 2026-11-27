"""Pairwise merge-conflict rehearsal. Never modifies refs, index or working tree."""
import json
import os
import itertools
import tempfile
import re
import subprocess
from pathlib import Path

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
HEADS = {"#" + number: sha for number, sha in HEADS}
PAIRS = list(itertools.combinations(HEADS, 2))


def main():
    before = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    rows = []
    before_status = subprocess.check_output(["git", "status", "--porcelain"], text=True)
    evidence = Path(os.environ.get("DSCC_REPORT_DIR") or tempfile.mkdtemp(prefix="dscc-evidence-")).resolve()
    root = Path.cwd().resolve()
    assert root not in evidence.parents and root != evidence
    evidence.mkdir(parents=True, exist_ok=True)
    for left, right in PAIRS:
        result = subprocess.run(
            ["git", "merge-tree", "--write-tree", "--name-only", "--no-messages",
             HEADS[left], HEADS[right]],
            capture_output=True, text=True, check=False,
        )
        if result.returncode not in (0, 1):
            raise RuntimeError(f"Git could not rehearse {left}/{right}: {result.stderr}")
        lines = result.stdout.splitlines()
        if not lines or not re.fullmatch(r"[a-f0-9]{40,64}", lines[0]):
            raise RuntimeError(f"Unexpected merge-tree output for {left}/{right}")
        files = sorted({line for line in lines[1:] if line.strip()})
        rows.append({"left": left, "right": right, "conflict": result.returncode == 1,
                     "paths": files})
    after = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    assert before == after, "HEAD must not change"
    assert subprocess.check_output(["git", "status", "--porcelain"], text=True) == before_status
    (evidence / "merge-rehearsal.json").write_text(json.dumps({"base": BASE, "heads": HEADS, "pairs": rows}, indent=2))
    report = ["# Pairwise conflict rehearsal", "",
              "Pairwise results only: no merge commit, push or runtime guarantee.", "",
              "| PR pair | Outcome | Conflicting paths |", "|---|---|---|"]
    for row in rows:
        paths = ", ".join(row["paths"]) or "—"
        outcome = "CONFLICT" if row["conflict"] else "clean"
        report.append(f"| {row['left']} / {row['right']} | {outcome} | {paths} |")
    text = "\n".join(report) + "\n"
    (evidence / "merge-rehearsal.md").write_text(text)
    print(text)
    print(f'{sum(not row["conflict"] for row in rows)}/{len(rows)} pairs clean')
    assert not any(row['conflict'] for row in rows), 'Conflicts remain'


if __name__ == "__main__":
    main()
