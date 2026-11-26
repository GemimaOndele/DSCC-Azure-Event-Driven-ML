"""Pairwise merge-conflict rehearsal. Never modifies refs, index or working tree."""
import json
import re
import subprocess
from pathlib import Path

# Immutable reviewed snapshot. Refresh explicitly if any PR advances.
HEADS = {
    "#14": "867130942074a04d77805a47de5baa4cc3a3fd96",
    "#17": "5886584331997d5b1b5fae7f6602c58d876f0221",
    "#18": "3cb9ffe327abdd68a58cd2c9d23a6797ee2f5bf9",
    "#19": "2f57b6495f5f434a1e26985e7333b9439f0c5048",
    "#20": "b81277f6d66a1d9e2b503e6fc54e7200732eb01f",
    "#21": "503280aa3a03ea74bcf33b913c5999de39a8d93f",
    "#23": "fdfc4325eb18c9e5bd95d26f25b307f956c9657c",
    "#24": "a981b2626deab860139b143a6b4029ce56a7998d",
    "#25": "c2ac5cb11cf7b5ac010611bd689098895021da75",
}
PAIRS = [
    ("#14", "#17"), ("#14", "#18"), ("#14", "#20"),
    ("#17", "#18"), ("#17", "#20"), ("#18", "#20"),
    ("#17", "#21"), ("#18", "#21"), ("#19", "#21"),
    ("#20", "#24"), ("#23", "#24"), ("#21", "#25"),
]


def main():
    before = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    rows = []
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
    assert not subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
    Path("merge-rehearsal.json").write_text(json.dumps({"heads": HEADS, "pairs": rows}, indent=2))
    report = ["# Pairwise conflict rehearsal", "",
              "Pairwise results only: no merge commit, push or runtime guarantee.", "",
              "| PR pair | Outcome | Conflicting paths |", "|---|---|---|"]
    for row in rows:
        paths = ", ".join(row["paths"]) or "—"
        outcome = "CONFLICT" if row["conflict"] else "clean"
        report.append(f"| {row['left']} / {row['right']} | {outcome} | {paths} |")
    text = "\n".join(report) + "\n"
    Path("merge-rehearsal.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
