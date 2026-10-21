from app.bot.handlers import render
from app.conversation.pipeline import Reply


def test_appends_sources_when_not_cited() -> None:
    out = render(Reply("Qabul 150 000 so'm.", ["Narxlar ro'yxati"]))
    assert out == "Qabul 150 000 so'm.\n\n📄 Manba: Narxlar ro'yxati"


def test_keeps_inline_citation() -> None:
    text = "Qabul 150 000 so'm. Manba: Narxlar ro'yxati"
    assert render(Reply(text, ["Narxlar ro'yxati"])) == text


def test_inline_citation_of_one_source_is_enough() -> None:
    text = "Qabul 150 000 so'm. Manba: Narxlar ro'yxati"
    assert render(Reply(text, ["Ko'p so'raladigan savollar", "Narxlar ro'yxati"])) == text
