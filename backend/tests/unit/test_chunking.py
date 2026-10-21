from app.retrieval.chunking import CHARS_PER_TOKEN, chunk_markdown, embedding_text

DOC = """# Narxlar

Kirish matni.

## Stomatologiya

- Stomatolog qabuli: 150 000 so'm

### Bolalar

- Bolalar stomatologi: 120 000 so'm

## Diagnostika

- EKG: 80 000 so'm
"""


def test_heading_paths_follow_hierarchy() -> None:
    chunks = chunk_markdown(DOC)
    assert [c.heading_path for c in chunks] == [
        "Narxlar",
        "Narxlar > Stomatologiya",
        "Narxlar > Stomatologiya > Bolalar",
        "Narxlar > Diagnostika",
    ]
    assert [c.ord for c in chunks] == [0, 1, 2, 3]


def test_long_sections_split_with_overlap() -> None:
    para = " ".join(["so'z"] * 60)  # ~300 chars
    body = "\n\n".join(f"{i}. {para}" for i in range(20))
    chunks = chunk_markdown(f"# Katta bo'lim\n\n{body}", target_tokens=200)
    max_chars = 200 * CHARS_PER_TOKEN
    assert len(chunks) > 1
    assert all(len(c.text) <= max_chars for c in chunks)
    # consecutive chunks share some text (overlap)
    assert chunks[0].text[-50:] in chunks[1].text


def test_embedding_text_prefixes_title_and_path() -> None:
    chunk = chunk_markdown(DOC)[1]
    assert embedding_text("Narxlar ro'yxati", chunk).startswith(
        "Narxlar ro'yxati > Narxlar > Stomatologiya\n\n"
    )


def test_embedding_text_does_not_repeat_title() -> None:
    chunk = chunk_markdown("# Narxlar\n\n## Stomatologiya\n\nmatn")[0]
    assert embedding_text("Narxlar", chunk).startswith("Narxlar > Stomatologiya\n\n")
