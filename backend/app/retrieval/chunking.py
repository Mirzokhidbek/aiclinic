"""Heading-aware markdown chunking: split by headings, then ~400 tokens with 15% overlap."""

import re
from dataclasses import dataclass

# ~4 chars per token is a reasonable estimate for Uzbek Latin text.
CHARS_PER_TOKEN = 4
TARGET_TOKENS = 400
OVERLAP_RATIO = 0.15

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")


@dataclass(frozen=True)
class TextChunk:
    ord: int
    text: str
    heading_path: str


def _sections(markdown: str) -> list[tuple[str, str]]:
    """Return (heading_path, body) pairs in document order."""
    stack: list[tuple[int, str]] = []
    sections: list[tuple[str, str]] = []
    buf: list[str] = []

    def flush() -> None:
        body = "\n".join(buf).strip()
        if body:
            sections.append((" > ".join(title for _, title in stack), body))
        buf.clear()

    for line in markdown.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            flush()
            level = len(match.group(1))
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, match.group(2)))
        else:
            buf.append(line)
    flush()
    return sections


def _split_long(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    pieces: list[str] = []
    current = ""
    for para in paragraphs:
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            pieces.append(current)
            tail = current[-overlap_chars:]
            current = f"{tail}\n\n{para}" if len(tail) + len(para) <= max_chars else para
        else:
            current = para
        while len(current) > max_chars:
            pieces.append(current[:max_chars])
            current = current[max_chars - overlap_chars :]
    if current:
        pieces.append(current)
    return pieces


def chunk_markdown(markdown: str, target_tokens: int = TARGET_TOKENS) -> list[TextChunk]:
    max_chars = target_tokens * CHARS_PER_TOKEN
    overlap_chars = int(max_chars * OVERLAP_RATIO)
    chunks: list[TextChunk] = []
    for heading_path, body in _sections(markdown):
        for piece in _split_long(body, max_chars, overlap_chars):
            chunks.append(TextChunk(ord=len(chunks), text=piece, heading_path=heading_path))
    return chunks


def embedding_text(title: str, chunk: TextChunk) -> str:
    path = chunk.heading_path
    if path == title or path.startswith(f"{title} > "):
        path = path[len(title) :].removeprefix(" > ")  # H1 usually repeats the title
    prefix = f"{title} > {path}" if path else title
    return f"{prefix}\n\n{chunk.text}"
