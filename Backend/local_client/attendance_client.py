"""Local attendance capture client.

This script is intended to run on a machine with camera access.
It should:
1) pull latest embeddings/model from your Hugging Face repo,
2) run local recognition,
3) push recognized attendance events to backend /attendance/import.
"""

import requests


BACKEND_URL = "http://localhost:8000"


def send_sample_event() -> None:
    payload = {
        "items": [
            {
                "student_id": "demo-student-id",
                "date": "2026-03-27",
                "time": "10:01:00",
                "confidence": 0.91,
                "source": "local_client",
            }
        ]
    }
    response = requests.post(f"{BACKEND_URL}/attendance/import", json=payload, timeout=20)
    print(response.status_code, response.text)


if __name__ == "__main__":
    send_sample_event()
