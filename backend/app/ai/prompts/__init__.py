from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent
SYSTEM_PROMPT_VERSION = "system_v1"


@lru_cache
def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def render_system_prompt(
    *, tenant_name: str, tone: str, working_hours: str, version: str = SYSTEM_PROMPT_VERSION
) -> str:
    return load_prompt(version).format(
        tenant_name=tenant_name, tone=tone, working_hours=working_hours or "—"
    )
