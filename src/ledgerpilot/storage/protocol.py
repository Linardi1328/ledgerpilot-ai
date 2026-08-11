from __future__ import annotations

from typing import BinaryIO, Protocol


class StorageError(Exception):
    pass


class DocumentStorage(Protocol):
    backend_name: str

    def open_staged_writer(self, storage_key: str) -> BinaryIO:
        raise NotImplementedError

    def open_staged_reader(self, storage_key: str) -> BinaryIO:
        raise NotImplementedError

    def open_for_processing(self, storage_key: str) -> BinaryIO:
        raise NotImplementedError

    def promote(self, *, staged_key: str, accepted_key: str) -> None:
        raise NotImplementedError

    def quarantine(self, *, staged_key: str, quarantine_key: str) -> None:
        raise NotImplementedError

    def delete_staged(self, storage_key: str) -> None:
        raise NotImplementedError

    def delete_accepted(self, storage_key: str) -> None:
        raise NotImplementedError

    def delete_quarantined(self, storage_key: str) -> None:
        raise NotImplementedError

    def exists_staged(self, storage_key: str) -> bool:
        raise NotImplementedError

    def exists_accepted(self, storage_key: str) -> bool:
        raise NotImplementedError

    def exists_quarantined(self, storage_key: str) -> bool:
        raise NotImplementedError
