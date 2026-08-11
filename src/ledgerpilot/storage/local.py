from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from ledgerpilot.core.config import DocumentStorageBackend, Settings
from ledgerpilot.storage.protocol import DocumentStorage, StorageError

_STAGING_AREA = "staging"
_ACCEPTED_AREA = "accepted"
_QUARANTINE_AREA = "quarantine"
_LOCAL_DIRECTORY_MODE = 0o700
_LOCAL_FILE_MODE = 0o600


class LocalDocumentStorage:
    backend_name = DocumentStorageBackend.LOCAL.value

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)

    @property
    def root(self) -> Path:
        return self._root

    def open_staged_writer(self, storage_key: str) -> BinaryIO:
        path = self._path_for(_STAGING_AREA, storage_key)
        self._ensure_parent_directories(path)
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, _LOCAL_FILE_MODE)
        except OSError as exc:
            raise StorageError("could not create staged document") from exc
        return os.fdopen(fd, "wb")

    def open_staged_reader(self, storage_key: str) -> BinaryIO:
        path = self._path_for(_STAGING_AREA, storage_key)
        try:
            return path.open("rb")
        except OSError as exc:
            raise StorageError("could not open staged document") from exc

    def open_for_processing(self, storage_key: str) -> BinaryIO:
        path = self._path_for(_ACCEPTED_AREA, storage_key)
        try:
            return path.open("rb")
        except OSError as exc:
            raise StorageError("could not open accepted document") from exc

    def promote(self, *, staged_key: str, accepted_key: str) -> None:
        source = self._path_for(_STAGING_AREA, staged_key)
        destination = self._path_for(_ACCEPTED_AREA, accepted_key)
        self._ensure_parent_directories(destination)
        try:
            source.replace(destination)
        except OSError as exc:
            raise StorageError("could not promote staged document") from exc

    def quarantine(self, *, staged_key: str, quarantine_key: str) -> None:
        source = self._path_for(_STAGING_AREA, staged_key)
        destination = self._path_for(_QUARANTINE_AREA, quarantine_key)
        self._ensure_parent_directories(destination)
        try:
            source.replace(destination)
        except OSError as exc:
            raise StorageError("could not quarantine staged document") from exc

    def delete_staged(self, storage_key: str) -> None:
        self._delete(_STAGING_AREA, storage_key)

    def delete_accepted(self, storage_key: str) -> None:
        self._delete(_ACCEPTED_AREA, storage_key)

    def delete_quarantined(self, storage_key: str) -> None:
        self._delete(_QUARANTINE_AREA, storage_key)

    def exists_staged(self, storage_key: str) -> bool:
        return self._path_for(_STAGING_AREA, storage_key).exists()

    def exists_accepted(self, storage_key: str) -> bool:
        return self._path_for(_ACCEPTED_AREA, storage_key).exists()

    def exists_quarantined(self, storage_key: str) -> bool:
        return self._path_for(_QUARANTINE_AREA, storage_key).exists()

    def _delete(self, area: str, storage_key: str) -> None:
        path = self._path_for(area, storage_key)
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            raise StorageError("could not delete document object") from exc

    def _path_for(self, area: str, storage_key: str) -> Path:
        relative_key = self._validated_relative_key(storage_key)
        area_root = self._area_root(area)
        candidate = area_root.joinpath(*relative_key.parts).resolve(strict=False)
        if not candidate.is_relative_to(area_root):
            raise StorageError("storage key escapes configured storage root")
        return candidate

    def _area_root(self, area: str) -> Path:
        root = self._root.resolve(strict=False)
        self._ensure_directory(root)
        area_root = root / area
        self._ensure_directory(area_root)
        return area_root.resolve(strict=False)

    def _ensure_directory(self, path: Path) -> None:
        if path.exists() and path.is_symlink():
            raise StorageError("storage directory cannot be a symlink")
        try:
            path.mkdir(mode=_LOCAL_DIRECTORY_MODE, parents=True, exist_ok=True)
        except OSError as exc:
            raise StorageError("could not create storage directory") from exc
        if path.is_symlink() or not path.is_dir():
            raise StorageError("storage path is not a safe directory")

    def _ensure_parent_directories(self, path: Path) -> None:
        root = self._root.resolve(strict=False)
        current = path.parent
        if not current.is_relative_to(root):
            raise StorageError("storage parent escapes configured storage root")
        relative_parent = current.relative_to(root)
        safe_current = root
        for part in relative_parent.parts:
            safe_current = safe_current / part
            self._ensure_directory(safe_current)

    def _validated_relative_key(self, storage_key: str) -> PurePosixPath:
        if "\\" in storage_key:
            raise StorageError("storage key contains an unsafe separator")
        pure_key = PurePosixPath(storage_key)
        if pure_key.is_absolute():
            raise StorageError("storage key must be relative")
        if not pure_key.parts or any(part in {"", ".", ".."} for part in pure_key.parts):
            raise StorageError("storage key contains an unsafe path segment")
        return pure_key


def get_document_storage(settings: Settings) -> DocumentStorage:
    if settings.document_storage_backend == DocumentStorageBackend.LOCAL:
        return LocalDocumentStorage(settings.document_storage_root)
    raise StorageError("unsupported document storage backend")
