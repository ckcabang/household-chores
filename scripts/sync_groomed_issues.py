#!/usr/bin/env python3
"""Sync groomed issue bodies from _docs/groomed/ onto the GitHub issues.

- Creates the follow-up issues listed in _docs/groomed/follow-ups.md (skipping
  any that already exist by exact title).
- Rewrites each "**[NEW] Title**" reference in the groomed bodies to the real
  "#N" of the created follow-up.
- PATCHes issues 4..21 with the resulting bodies.

Auth: uses `git credential fill` for github.com (the token your Git Credential
Manager already holds), or GITHUB_TOKEN if set. The token is never printed.

Usage:
    uv run python scripts/sync_groomed_issues.py --dry-run
    uv run python scripts/sync_groomed_issues.py
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = "ckcabang/household-chores"
API = f"https://api.github.com/repos/{REPO}"
GROOMED = Path(__file__).resolve().parent.parent / "_docs" / "groomed"

# title -> (goal, [parent issue numbers])
FOLLOW_UPS: dict[str, tuple[str, list[int]]] = {
    "Password reset flow": (
        "A user who forgot their password can reset it. Blocked on email "
        "infrastructure, which the MVP omits - revisit once email exists.",
        [4],
    ),
    "Collect and verify email on signup": (
        "Signup captures an email address and confirms it before it is trusted.",
        [4],
    ),
    "Throttle failed login attempts": (
        "Repeated failed logins for one account or IP are rate-limited or "
        "briefly locked out.",
        [4],
    ),
    "Leave or dissolve a household": (
        "A member can leave a household, and a household with no members is "
        "cleaned up; renaming a household is included.",
        [5],
    ),
    "Revoke and regenerate invitations": (
        "The inviting member can invalidate an outstanding invite link and "
        "issue a fresh one.",
        [6],
    ),
    "Reconcile occurrences when cadence changes": (
        "Editing a chore's cadence_days re-spaces its future (not past) "
        "occurrences instead of leaving stale ones.",
        [7, 9],
    ),
    "Undo a completion": (
        "A member can reverse a mistaken completion, restoring the occurrence "
        "to active and removing the Completion (and any credit).",
        [10],
    ),
    "Apply rebalance proposals": (
        "The proposed owners from the rebalance preview can be written to the "
        "chores in one confirmed action.",
        [14, 17],
    ),
    "Fairness weight change history": (
        "Past FairnessWeights changes are recorded with who/when/what so the "
        "household can see how weights evolved.",
        [16],
    ),
    "Dashboard contribution charts": (
        "The dashboard gains a visual trend of contribution / balance over time.",
        [17],
    ),
    "Regenerate AI setup draft": (
        "From the review screen, a member can discard the draft and generate a "
        "new one with revised answers.",
        [19],
    ),
    "Continuous deployment workflow": (
        "Merges to main build and deploy automatically to the chosen host.",
        [21],
    ),
}

NEW_REF = re.compile(r"\*\*\[NEW\] (?P<title>[^*]+?)\*\*")


def get_token() -> str:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token.strip()
    proc = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        sys.exit("git credential fill failed; set GITHUB_TOKEN instead.")
    for line in proc.stdout.splitlines():
        if line.startswith("password="):
            return line[len("password=") :].strip()
    sys.exit("No credential found for github.com; set GITHUB_TOKEN instead.")


def api(token: str, method: str, path: str, payload: dict | None = None) -> dict:
    url = path if path.startswith("http") else f"{API}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "sync-groomed-issues")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read() or "{}")
    except urllib.error.HTTPError as exc:
        sys.exit(f"{method} {url} -> {exc.code}: {exc.read().decode()[:400]}")


def all_issue_titles(token: str) -> dict[str, int]:
    out: dict[str, int] = {}
    page = 1
    while True:
        batch = api(
            token, "GET", f"/issues?state=all&per_page=100&page={page}"
        )
        if not batch:
            break
        for issue in batch:
            if "pull_request" not in issue:
                out[issue["title"]] = issue["number"]
        if len(batch) < 100:
            break
        page += 1
    return out


def follow_up_body(goal: str, parents: list[int]) -> str:
    refs = ", ".join(f"#{n}" for n in parents)
    return (
        f"**Goal:** {goal}\n\n"
        f"Raised while grooming {refs} - moved out of scope so the parent task "
        f"stays sized to one session. Not on the MVP critical path.\n\n"
        f"Groom against `_docs/task-template.md` before implementing."
    )


def groomed_body(path: Path) -> str:
    text = path.read_text(encoding="utf-8").strip()
    # Drop the leading "# Title" heading; the issue already has a title.
    lines = text.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines.pop(0)
    body = "\n".join(lines)
    return (
        body
        + f"\n\n---\n_Groomed from the MVP backlog; source of truth is "
        f"`_docs/groomed/{path.name}`._"
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    token = get_token()
    existing = all_issue_titles(token)

    # 1. Ensure follow-up issues exist.
    numbers: dict[str, int] = {}
    for title, (goal, parents) in FOLLOW_UPS.items():
        if title in existing:
            numbers[title] = existing[title]
            print(f"  follow-up exists  #{existing[title]:>3}  {title}")
            continue
        if args.dry_run:
            print(f"  would create      #???  {title}")
            numbers[title] = 0
            continue
        created = api(
            token,
            "POST",
            "/issues",
            {"title": title, "body": follow_up_body(goal, parents)},
        )
        numbers[title] = created["number"]
        print(f"  created           #{created['number']:>3}  {title}")

    # 2. Patch issues 4..21 with rewritten bodies.
    for path in sorted(GROOMED.glob("[0-9][0-9]-*.md")):
        num = int(path.name[:2])
        body = groomed_body(path)

        def repl(m: re.Match) -> str:
            t = m.group("title").strip()
            n = numbers.get(t)
            return f"#{n}" if n else f"**[NEW] {t}**"

        body, hits = NEW_REF.subn(repl, body)
        leftover = NEW_REF.findall(body)
        if leftover:
            print(f"  WARNING #{num}: unresolved follow-up refs: {leftover}")
        if args.dry_run:
            print(f"  would patch  #{num:>3}  ({hits} refs)  {path.name}")
            continue
        api(token, "PATCH", f"/issues/{num}", {"body": body})
        print(f"  patched      #{num:>3}  ({hits} refs)  {path.name}")

    print("done" + (" (dry run)" if args.dry_run else ""))


if __name__ == "__main__":
    main()
