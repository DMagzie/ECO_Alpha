# tests/test_cibd22x_parser_dedupe.py
from pathlib import Path

def test_only_one_parser_file_exists():
    repo_root = Path(__file__).resolve().parents[1]
    # Catch "loose" duplicates anywhere in repo
    candidates = list(repo_root.rglob("translate_cibd22x_to_v5*.py"))
    # Allow exactly one: the canonical module file
    assert len(candidates) == 1, f"Expected 1 parser file, found {len(candidates)}: {candidates}"
    assert candidates[0].as_posix().endswith('cbecc/translate_cibd22x_to_v5.py')
