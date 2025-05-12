import argparse
import json

from checks import run_checks_on_task
from scale_api import stream_completed_tasks


def _get_image_url(task: dict) -> str | None:
    """Return the first attachment URL or None if not found."""
    p = task.get("params", {})
    if "attachment" in p:
        return p["attachment"]
    return None


# -------- main CLI -----------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="Run QC checks on Scale tasks")
    ap.add_argument(
        "--project", required=True, help="Exact project name in the Scale dashboard"
    )
    ap.add_argument(
        "--out", default="quality_issues.json", help="Path of the JSON report to write"
    )
    ap.add_argument("--limit", type=int, help="Stop after N tasks")
    args = ap.parse_args()

    written = 0
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("[\n")  # JSON array opener
        first = True

        for idx, task in enumerate(stream_completed_tasks(args.project)):
            if args.limit and idx >= args.limit:
                break

            issues = run_checks_on_task(task)
            if not issues:  # skip clean tasks
                continue

            entry = {
                "task_id": task.get("task_id"),
                "image_url": _get_image_url(task),
                "num_errors": sum(i["severity"] == "error" for i in issues),
                "num_warnings": sum(i["severity"] == "warning" for i in issues),
                "issues": issues,
            }

            if not first:
                f.write(",\n")
            json.dump(entry, f, indent=2)
            first = False
            written += 1

        f.write("\n]\n")  # JSON array closer

    print(f"Wrote quality check results for {written} task(s) → {args.out}")


if __name__ == "__main__":
    main()
