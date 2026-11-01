from app.relations.diff import DiffOperation, sentence_diff


def test_sentence_diff_normalizes_bullets_and_marks_replacement() -> None:
    old = "8.1 - Qualifying assets shall be 75 per cent. The rule applies continuously."
    new = "Paragraph 8.1: Qualifying assets shall be 60 percent. The rule applies continuously."

    changes = sentence_diff(old, new)

    assert any(change.operation is DiffOperation.REPLACE for change in changes)
    assert any("75 per cent" in change.old_text for change in changes)
    assert any("60 percent" in change.new_text for change in changes)
    assert any(change.operation is DiffOperation.EQUAL for change in changes)
