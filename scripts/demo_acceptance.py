"""Run the separate-process TLS/PostgreSQL fixture acceptance without secrets in argv."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run two-tenant, three-device TLS fixture acceptance")
    parser.add_argument("--report", type=Path, default=Path("reports/e2e-inventory-flow.json"))
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    report = args.report.resolve()
    environment = dict(os.environ)
    environment["SP_ACCEPTANCE_REPORT"] = str(report)
    run_id = str(uuid4())
    environment["SP_ACCEPTANCE_RUN_ID"] = run_id
    result = subprocess.run([sys.executable, "-m", "pytest", "tests/e2e/test_inventory_flow.py", "-q", "--tb=short"],
                            cwd=root, env=environment, stdin=subprocess.DEVNULL)
    if result.returncode:
        print(json.dumps({"status": "failed", "report": "not_produced"}))
        return result.returncode
    if not report.is_file() or json.loads(report.read_text(encoding="utf-8")).get("run_id") != run_id:
        print(json.dumps({"status": "not_run", "reason": "real_postgresql_fixture_required"}))
        return 1
    print(json.dumps({"status": "passed", "report": str(report)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
