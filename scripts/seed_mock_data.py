from urllib import request

API_BASE = "http://localhost:8000"


def post(path: str, payload: bytes) -> str:
    req = request.Request(
        url=f"{API_BASE}{path}",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=10) as response:
        return response.read().decode("utf-8")


def main() -> None:
    print("[1] Trigger ingestion sync")
    print(post("/api/v1/ingestion/sync", b"{}"))

    print("[2] Issue auth token")
    token_payload = post("/api/v1/auth/token", b'{"user_id":"user_dev_01"}')
    print(token_payload)


if __name__ == "__main__":
    main()
