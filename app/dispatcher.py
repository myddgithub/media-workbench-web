from __future__ import annotations

from .cme import execute_cut, execute_extract, execute_merge
from .converter import execute_conversion


EXECUTORS = {
    "convert": execute_conversion,
    "cut": execute_cut,
    "merge": execute_merge,
    "extract": execute_extract,
}


def execute(kind: str, payload: dict, **context):
    try:
        executor = EXECUTORS[kind]
    except KeyError as exc:
        raise ValueError(f"未知任务类型: {kind}") from exc
    return executor(payload, **context)
