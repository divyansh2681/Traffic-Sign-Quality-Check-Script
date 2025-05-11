import os
from typing import Any, Dict, Iterator

import requests

API_KEY = os.environ.get("SCALE_API_KEY")
if not API_KEY:
    raise RuntimeError(
        "Set environment variable SCALE_API_KEY with your a key before running the script."
    )

BASE_URL = "https://api.scale.com/v1"


def stream_completed_tasks(
    project: str,
    batch_size: int = 100,
) -> Iterator[Dict[str, Any]]:
    """
    Yield every completed task one at a time.
    """
    params = {"project": project, "status": "completed", "limit": batch_size}

    while True:
        r = requests.get(f"{BASE_URL}/tasks", params=params, auth=(API_KEY, ""))
        r.raise_for_status()
        docs = r.json().get("docs", [])

        # Yield every task we got this round
        for task in docs:
            yield task

        # If we got fewer than limit, that was the last page → stop
        if len(docs) < batch_size:
            break

        # Otherwise, ask for the next page
        last_id = docs[-1].get("task_id")
        params["last_id"] = last_id
