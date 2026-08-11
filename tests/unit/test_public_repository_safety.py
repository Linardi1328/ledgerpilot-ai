from __future__ import annotations

from pathlib import Path


def test_gitignore_keeps_runtime_and_sensitive_directories_broadly_ignored() -> None:
    gitignore_lines = set(Path(".gitignore").read_text().splitlines())

    for pattern in {
        "credentials/",
        "secrets/",
        "uploads/",
        "documents/",
        "storage/",
        "local_storage/",
        "exports/",
        "generated/",
    }:
        assert pattern in gitignore_lines
        assert f"/{pattern}" not in gitignore_lines

    assert "!src/ledgerpilot/documents/" in gitignore_lines
    assert "!src/ledgerpilot/documents/**" in gitignore_lines
    assert "!src/ledgerpilot/storage/" in gitignore_lines
    assert "!src/ledgerpilot/storage/**" in gitignore_lines
    assert "src/ledgerpilot/documents/**/__pycache__/" in gitignore_lines
    assert "src/ledgerpilot/documents/**/*.py[cod]" in gitignore_lines
    assert "src/ledgerpilot/storage/**/__pycache__/" in gitignore_lines
    assert "src/ledgerpilot/storage/**/*.py[cod]" in gitignore_lines
