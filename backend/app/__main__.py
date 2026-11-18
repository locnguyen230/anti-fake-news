"""Run with `python -m app` from backend to honor AFN_HOST/AFN_PORT."""

import uvicorn
from pydantic import ValidationError

from app.config import Settings


def main() -> None:
    try:
        settings = Settings()
    except ValidationError:
        raise SystemExit("Invalid AFN configuration; check .env and environment values.") from None
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, access_log=False)


if __name__ == "__main__":
    main()
