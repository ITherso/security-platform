"""One-command offline product demonstration.

Runs only the real command-line tools of this repository on committed example
inputs. Policy results, logs and DEMO_SUMMARY.md go into one new output
directory. The analyst-chain workspace (a copy of the repository plus all
phase outputs) goes to <output-dir>/offline-chain when the output directory is
outside the repository; for the default in-repository output it is created in
the system temporary directory, kept for inspection, and its path is recorded
in the summary (delete it when no longer needed). Nothing is simulated: a step
whose external input was not supplied is reported NOT_RUN, a step that fails
is reported FAILED. No server is started, no network is used, no device or
scanner is contacted. Results describe example data only; they are not an
assessment of any real system.

usage: python -B scripts/run_demo.py [--output-dir DIR] [--hbf-root DIR]
                                     [--termivar-root DIR] [--phase30-delivery-zip FILE]
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
POLICY = [sys.executable, "-B", "-m", "security_platform.policy_contracts.cli"]
STEP_TIMEOUT = 900


def _run(command: list[str], log: Path, *, cwd: Path) -> tuple[int, float]:
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONIOENCODING": "utf-8"}
    started = time.monotonic()
    with log.open("xb") as handle:
        try:
            result = subprocess.run(command, cwd=cwd, env=environment, stdin=subprocess.DEVNULL, stdout=handle,
                                    stderr=subprocess.STDOUT, timeout=STEP_TIMEOUT, check=False)
            code = result.returncode
        except subprocess.TimeoutExpired:
            code = 124
    return code, round(time.monotonic() - started, 1)


def _read(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _policy_steps(out: Path, hbf_root: Path | None) -> list[dict]:
    steps = []
    jobs = [("policy-preconditions", "check-preconditions", "examples/policy-preconditions.json", []),
            ("policy-rollout", "validate-rollout", "examples/policy-rollout.json",
             ["--evaluation-time", "2030-01-01T00:30:00Z"])]
    if hbf_root is not None:
        jobs.insert(0, ("policy-preview", "preview", "examples/policy-preview.json", ["--hbf-root", str(hbf_root)]))
    else:
        steps.append({"step": "policy-preview", "status": "NOT_RUN",
                      "detail": "needs --hbf-root (local HostBasedFirewall evaluator source)"})
    for name, command, source, extra in jobs:
        target = out / "policy" / f"{name}.json"
        code, seconds = _run([*POLICY, command, "--input", str(ROOT / source), *extra, "--output", str(target)],
                             out / "logs" / f"{name}.log", cwd=ROOT)
        result = _read(target) if code == 0 else None
        if result is None:
            steps.append({"step": name, "status": "FAILED", "exit_code": code, "seconds": seconds,
                          "detail": f"see logs/{name}.log"})
            continue
        detail = f"result status={result.get('status')}; blockers={len(result.get('blocker_codes', []))}"
        if name == "policy-preview":
            detail += f"; scenarios={len(result.get('results', []))}"
        detail += f"; execution_authorized={str(result.get('execution_authorized')).lower()}"
        steps.append({"step": name, "status": "PASSED", "exit_code": code, "seconds": seconds,
                      "output": f"policy/{name}.json", "detail": detail})
    return steps


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _chain_step(out: Path, termivar_root: Path | None, delivery_zip: Path | None) -> dict:
    runner = ROOT / "scripts" / "run_offline_chain.py"
    if not runner.is_file():
        return {"step": "offline-analyst-chain", "status": "NOT_RUN", "detail": "scripts/run_offline_chain.py missing"}
    # The chain runner refuses a workspace inside the repository (it copies the
    # repository into the workspace), so the default in-repository demo output
    # gets a new workspace in the system temporary directory instead.
    workspace = (Path(tempfile.mkdtemp(prefix="sp-offline-chain-")) if _inside(out, ROOT)
                 else out / "offline-chain")
    command = [sys.executable, "-B", str(runner), "--workspace", str(workspace)]
    if termivar_root is not None:
        command += ["--termivar-root", str(termivar_root)]
    if delivery_zip is not None:
        command += ["--phase30-delivery-zip", str(delivery_zip)]
    code, seconds = _run(command, out / "logs" / "offline-analyst-chain.log", cwd=ROOT)
    scope = "phases 16-44" if termivar_root and delivery_zip else (
        "phases 16-30" if termivar_root else "phases 16-19 (pass --termivar-root for more)")
    return {"step": "offline-analyst-chain", "status": "PASSED" if code == 0 else "FAILED", "exit_code": code,
            "seconds": seconds, "output": str(workspace),
            "detail": f"{scope}; workspace {workspace}; table in logs/offline-analyst-chain.log"}


def _console_step() -> dict:
    # The same verification serve.py performs before it starts: dist layout,
    # manifest rows, digests and licence header. Nothing is served here.
    try:
        spec = importlib.util.spec_from_file_location("operator_console_build", ROOT / "operator-console" / "build.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.read_dist()
    except (OSError, ValueError, TypeError, RecursionError, ImportError, AttributeError):
        return {"step": "operator-console", "status": "NOT_RUN",
                "detail": "no verified console build in operator-console/dist; use the packaged console build "
                          "or run pnpm build"}
    return {"step": "operator-console", "status": "READY",
            "detail": "start with: python -B operator-console/serve.py --port 8787 (then open http://127.0.0.1:8787/)"}


def _write_summary(out: Path, steps: list[dict], started: str) -> None:
    (out / "demo-summary.json").write_text(json.dumps({"started_utc": started, "steps": steps}, indent=2) + "\n",
                                           encoding="utf-8")
    lines = ["# Offline demo run", "", f"Started (UTC): {started}", "",
             "Example and synthetic inputs only. No real system, device or customer data was assessed; "
             "no output here is a verification, approval or authorization.", "",
             "| Step | Status | Exit | Seconds | Detail |", "| --- | --- | --- | --- | --- |"]
    for step in steps:
        lines.append(f"| {step['step']} | {step['status']} | {step.get('exit_code', '')} | {step.get('seconds', '')} "
                     f"| {step['detail']} |")
    (out / "DEMO_SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the offline product demo into one new output directory")
    parser.add_argument("--output-dir", type=Path,
                        help="new directory for all demo outputs (default: demo-output/run-<UTC time>)")
    parser.add_argument("--hbf-root", type=Path, help="local HostBasedFirewall source for the policy preview")
    parser.add_argument("--termivar-root", type=Path,
                        help="Termivar checkout at commit 6a2639348c2366d0bf71b9a34e5484d40aa393a3 (phases 20-30)")
    parser.add_argument("--phase30-delivery-zip", type=Path,
                        help="recorded Phase30 delivery ZIP (needed for phases 31-44)")
    args = parser.parse_args(argv)
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = (args.output_dir or ROOT / "demo-output" / ("run-" + started.replace(":", ""))).resolve()
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        print("demo: output directory must be new or empty", file=sys.stderr)
        return 2
    (out / "logs").mkdir(parents=True, exist_ok=True)
    (out / "policy").mkdir(exist_ok=True)
    steps = _policy_steps(out, args.hbf_root and args.hbf_root.resolve())
    steps.append(_chain_step(out, args.termivar_root and args.termivar_root.resolve(),
                             args.phase30_delivery_zip and args.phase30_delivery_zip.resolve()))
    steps.append(_console_step())
    _write_summary(out, steps, started)
    width = max(len(step["step"]) for step in steps)
    for step in steps:
        print(f"{step['step']:<{width}}  {step['status']:<8}  {step['detail']}")
    print(f"summary: {out / 'DEMO_SUMMARY.md'}")
    return 1 if any(step["status"] == "FAILED" for step in steps) else 0


if __name__ == "__main__":
    raise SystemExit(main())
