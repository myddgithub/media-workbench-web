from pathlib import Path

import pytest

from app.config import MediaRoot, parse_media_roots
from app.paths import PathAccessError, PathResolver


def test_parse_media_roots_keeps_labels_and_unique_keys(tmp_path):
    roots = parse_media_roots(f"我的资料={tmp_path};Downloads={tmp_path}")
    assert [root.label for root in roots.values()] == ["我的资料", "Downloads"]
    assert len(roots) == 2


def test_resolver_accepts_relative_path(media_root):
    folder = media_root / "影视" / "剧集"
    folder.mkdir(parents=True)
    resolver = PathResolver({"media": MediaRoot("media", "媒体", media_root)})
    assert resolver.resolve("media", "影视/剧集") == folder.resolve()
    assert resolver.relative("media", folder) == "影视/剧集"


@pytest.mark.parametrize("value", ["../secret", "a/../../secret", "/etc/passwd", "C:/Windows"])
def test_resolver_rejects_escape(media_root, value):
    resolver = PathResolver({"media": MediaRoot("media", "媒体", media_root)})
    with pytest.raises(PathAccessError):
        resolver.resolve("media", value, must_exist=False)


def test_list_directory_sorts_directories_before_files(media_root):
    (media_root / "z-dir").mkdir()
    (media_root / "a.wav").write_bytes(b"wav")
    resolver = PathResolver({"media": MediaRoot("media", "媒体", media_root)})
    result = resolver.list_directory("media")
    assert [item["name"] for item in result["items"]] == ["z-dir", "a.wav"]
    assert result["items"][0]["type"] == "directory"
