import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import StrEnum


class DiffOperation(StrEnum):
    EQUAL = "EQUAL"
    INSERT = "INSERT"
    DELETE = "DELETE"
    REPLACE = "REPLACE"


@dataclass(frozen=True, slots=True)
class DiffChunk:
    operation: DiffOperation
    old_text: str
    new_text: str


def _sentences(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = re.sub(r"[•●▪◦]", "-", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", normalized) if part.strip()]


def sentence_diff(old_text: str, new_text: str) -> tuple[DiffChunk, ...]:
    old_sentences = _sentences(old_text)
    new_sentences = _sentences(new_text)
    matcher = SequenceMatcher(a=old_sentences, b=new_sentences, autojunk=False)
    chunks: list[DiffChunk] = []
    for operation, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        chunks.append(
            DiffChunk(
                operation=DiffOperation(operation.upper()),
                old_text=" ".join(old_sentences[old_start:old_end]),
                new_text=" ".join(new_sentences[new_start:new_end]),
            )
        )
    return tuple(chunks)
