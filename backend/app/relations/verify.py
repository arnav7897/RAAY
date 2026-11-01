import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class QuoteSpan:
    char_start: int
    char_end: int


def _normalize_with_mapping(value: str) -> tuple[str, list[int]]:
    characters: list[str] = []
    mapping: list[int] = []
    previous_was_space = False
    for index, original in enumerate(value):
        for character in unicodedata.normalize("NFKC", original):
            if character.isspace():
                if characters and not previous_was_space:
                    characters.append(" ")
                    mapping.append(index)
                previous_was_space = True
            else:
                characters.append(character)
                mapping.append(index)
                previous_was_space = False
    while characters and characters[-1] == " ":
        characters.pop()
        mapping.pop()
    return "".join(characters), mapping


def locate_normalized_quote(source: str, quote: str) -> QuoteSpan | None:
    normalized_source, mapping = _normalize_with_mapping(source)
    normalized_quote, _ = _normalize_with_mapping(quote)
    if not normalized_quote:
        return None
    normalized_start = normalized_source.find(normalized_quote)
    if normalized_start < 0:
        return None
    normalized_end = normalized_start + len(normalized_quote)
    return QuoteSpan(
        char_start=mapping[normalized_start],
        char_end=mapping[normalized_end - 1] + 1,
    )
