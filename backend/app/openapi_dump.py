"""Write the OpenAPI schema to a file (used to generate the Mini App's TypeScript client)."""

import json
import sys
from pathlib import Path

from app.main import create_app

if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "openapi.json")
    out.write_text(json.dumps(create_app().openapi(), indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {out}")
