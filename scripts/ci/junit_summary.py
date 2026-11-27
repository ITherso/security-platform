"""Summarise a pytest JUnit report and refuse skipped tests in guarded packages.

The pytest step's own exit status decides whether the tests passed. This step
adds the counts, the ids of failed and erroring tests and the skip reasons to
the GitHub job summary (GITHUB_STEP_SUMMARY, or stdout without it). It also
applies one CI rule: every test whose JUnit classname starts with a guarded
prefix must run. The PostgreSQL integration and end-to-end tests skip when the
test database configuration is missing; in CI that must fail the job, not pass
it with fewer tests. Failure messages are not copied: they can show fixture
values.

Exit status: 0 when the rule holds, 1 when it does not, 2 for an unreadable report.
"""
from __future__ import annotations

import argparse
from collections import Counter
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ElementTree

LISTED = 200


def outcomes(path):
    root = ElementTree.parse(path).getroot()
    rows = []
    for case in root.iter("testcase"):
        tags = {child.tag: child for child in case if child.tag in ("error", "failure", "skipped")}
        outcome = next((tag for tag in ("error", "failure", "skipped") if tag in tags), "passed")
        reason = tags["skipped"].get("message", "") if outcome == "skipped" else ""
        rows.append((case.get("classname", ""), case.get("name", ""), outcome, reason))
    return rows


def guarded(classname, prefix):
    return classname == prefix or classname.startswith(prefix + ".")


def report(rows, prefixes):
    counts = Counter(outcome for _, _, outcome, _ in rows)
    lines = ["## pytest JUnit summary", "",
             "| tests | passed | failed | errors | skipped |", "|---:|---:|---:|---:|---:|",
             f"| {len(rows)} | {counts['passed']} | {counts['failure']} | {counts['error']} | {counts['skipped']} |"]
    for title, outcome in (("Failed", "failure"), ("Errors", "error")):
        ids = [f"{classname}::{name}" for classname, name, kind, _ in rows if kind == outcome]
        if ids:
            lines += ["", f"### {title} ({len(ids)})", ""] + [f"- `{value}`" for value in ids[:LISTED]]
            if len(ids) > LISTED:
                lines.append(f"- ... {len(ids) - LISTED} more in the JUnit artifact")
    reasons = Counter(reason for _, _, kind, reason in rows if kind == "skipped")
    if reasons:
        lines += ["", "### Skip reasons", "", "| tests | reason |", "|---:|---|"]
        lines += [f"| {count} | {reason.replace('|', '/')} |" for reason, count in reasons.most_common()]
    problems = []
    if prefixes:
        lines += ["", "### Packages that must run in CI", "", "| prefix | tests | skipped |", "|---|---:|---:|"]
    for prefix in prefixes:
        selected = [row for row in rows if guarded(row[0], prefix)]
        skipped = [f"{classname}::{name}" for classname, name, kind, _ in selected if kind == "skipped"]
        lines.append(f"| `{prefix}` | {len(selected)} | {len(skipped)} |")
        if not selected:
            problems.append(f"No test ran under {prefix}")
        problems += [f"Skipped in CI: {value}" for value in skipped[:LISTED]]
    return "\n".join(lines) + "\n", problems


def main(argv=None):
    parser = argparse.ArgumentParser(description="Summarise a pytest JUnit report for the GitHub job summary")
    parser.add_argument("junit", type=Path)
    parser.add_argument("--no-skips-in", action="append", default=[], metavar="PREFIX",
                        help="a JUnit classname prefix whose tests must not be skipped, e.g. tests.integration")
    args = parser.parse_args(argv)
    try:
        rows = outcomes(args.junit)
    except (OSError, ElementTree.ParseError) as exc:
        print(f"::error::The JUnit report could not be read ({type(exc).__name__})")
        return 2
    if not rows:
        print("::error::The JUnit report contains no test cases")
        return 2
    text, problems = report(rows, args.no_skips_in)
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if target:
        with open(target, "a", encoding="utf-8") as stream:
            stream.write(text)
    sys.stdout.write(text)
    for problem in problems:
        print("::error::" + problem)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
