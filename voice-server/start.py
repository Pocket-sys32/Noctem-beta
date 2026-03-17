import os

import uvicorn


def main() -> None:
    port = int(os.environ.get("PORT", "5050"))
    uvicorn.run("server:app", host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()

