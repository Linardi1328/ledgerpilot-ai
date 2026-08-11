from __future__ import annotations

from pathlib import Path

import pytest

from ledgerpilot.storage.local import LocalDocumentStorage
from ledgerpilot.storage.protocol import StorageError


def test_local_storage_stages_promotes_and_opens_for_processing(tmp_path: Path) -> None:
    storage = LocalDocumentStorage(tmp_path / "storage")
    staged_key = "firm/client/document/generated-object"
    accepted_key = "firm/client/document/generated-accepted-object"

    with storage.open_staged_writer(staged_key) as staged_file:
        staged_file.write(b"synthetic document bytes")

    assert storage.exists_staged(staged_key)

    storage.promote(staged_key=staged_key, accepted_key=accepted_key)

    assert not storage.exists_staged(staged_key)
    assert storage.exists_accepted(accepted_key)
    with storage.open_for_processing(accepted_key) as accepted_file:
        assert accepted_file.read() == b"synthetic document bytes"


def test_local_storage_rejects_path_traversal_keys(tmp_path: Path) -> None:
    storage = LocalDocumentStorage(tmp_path / "storage")

    with pytest.raises(StorageError):
        storage.open_staged_writer("../escape")

    assert not (tmp_path / "escape").exists()


def test_local_storage_rejects_backslash_keys(tmp_path: Path) -> None:
    storage = LocalDocumentStorage(tmp_path / "storage")

    with pytest.raises(StorageError):
        storage.open_staged_writer("firm\\client\\document")


def test_local_storage_does_not_use_submitted_filename_when_key_is_generated(
    tmp_path: Path,
) -> None:
    storage = LocalDocumentStorage(tmp_path / "storage")
    submitted_filename = "invoice.pdf"
    generated_key = "firm/client/document/generated-object"

    with storage.open_staged_writer(generated_key) as staged_file:
        staged_file.write(b"%PDF-1.4\n")
    storage.promote(staged_key=generated_key, accepted_key=generated_key)

    stored_paths = [path for path in tmp_path.rglob("*") if path.is_file()]
    assert stored_paths
    assert all(submitted_filename not in str(path) for path in stored_paths)
