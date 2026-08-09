from __future__ import annotations

import os
from pathlib import Path, PurePosixPath

from .config import MediaRoot


class PathAccessError(ValueError):
    pass


class PathResolver:
    def __init__(self, roots: dict[str, MediaRoot]):
        self.roots = roots

    def root(self, key: str) -> MediaRoot:
        try:
            return self.roots[key]
        except KeyError as exc:
            raise PathAccessError(f"未知的存储位置: {key}") from exc

    @staticmethod
    def normalize_relative(relative: str | None) -> str:
        value = (relative or "").strip().replace("\\", "/")
        if value in ("", "."):
            return ""
        pure = PurePosixPath(value)
        if pure.is_absolute() or any(part in ("", ".", "..") for part in pure.parts):
            raise PathAccessError("路径必须是存储位置内的相对路径，且不能包含 '..'")
        if pure.parts and ":" in pure.parts[0]:
            raise PathAccessError("不允许使用磁盘绝对路径")
        return pure.as_posix()

    def resolve(
        self,
        root_key: str,
        relative: str | None = "",
        *,
        must_exist: bool = True,
        kind: str | None = None,
    ) -> Path:
        spec = self.root(root_key)
        root_path = spec.path.resolve(strict=False)
        normalized = self.normalize_relative(relative)
        candidate = (root_path / normalized).resolve(strict=False)
        try:
            inside = os.path.commonpath((str(root_path), str(candidate))) == str(root_path)
        except ValueError:
            inside = False
        if not inside:
            raise PathAccessError("路径超出了允许访问的存储位置")
        if must_exist and not candidate.exists():
            raise PathAccessError(f"路径不存在: {normalized or '/'}")
        if kind == "file" and candidate.exists() and not candidate.is_file():
            raise PathAccessError("所选路径不是文件")
        if kind == "dir" and candidate.exists() and not candidate.is_dir():
            raise PathAccessError("所选路径不是目录")
        return candidate

    def relative(self, root_key: str, path: Path) -> str:
        root_path = self.root(root_key).path.resolve(strict=False)
        candidate = path.resolve(strict=False)
        try:
            return candidate.relative_to(root_path).as_posix()
        except ValueError as exc:
            raise PathAccessError("结果文件不在允许的存储位置内") from exc

    def list_directory(self, root_key: str, relative: str = "") -> dict:
        directory = self.resolve(root_key, relative, kind="dir")
        items = []
        try:
            children = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.casefold()))
        except PermissionError as exc:
            raise PathAccessError("没有权限读取该目录") from exc
        for child in children[:2000]:
            if child.name.startswith("."):
                continue
            try:
                is_dir = child.is_dir()
                is_file = child.is_file()
            except OSError:
                continue
            if not (is_dir or is_file):
                continue
            stat = child.stat()
            items.append(
                {
                    "name": child.name,
                    "path": self.relative(root_key, child),
                    "type": "directory" if is_dir else "file",
                    "size": None if is_dir else stat.st_size,
                    "modified": stat.st_mtime,
                }
            )
        normalized = self.normalize_relative(relative)
        parent = str(PurePosixPath(normalized).parent)
        if parent == ".":
            parent = ""
        return {
            "root": root_key,
            "path": normalized,
            "parent": parent,
            "items": items,
            "truncated": len(items) >= 2000,
        }
