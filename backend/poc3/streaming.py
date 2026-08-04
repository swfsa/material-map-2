"""Small JSON streaming helpers shared by HTTP-facing PoCs."""

from collections.abc import Callable, Iterable, Iterator
import json
from typing import TypeVar

from pydantic import BaseModel


T = TypeVar("T")
DEFAULT_CHUNK_SIZE = 16 * 1024


def _chunk_bytes(payload: bytes, chunk_size: int) -> Iterator[bytes]:
    if chunk_size < 1:
        raise ValueError("chunk_size must be greater than zero")
    for start in range(0, len(payload), chunk_size):
        yield payload[start : start + chunk_size]


def stream_json_array(
    items: Iterable[T],
    *,
    to_model: Callable[[T], BaseModel],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> Iterator[bytes]:
    """Yield a valid JSON array without first building the complete response."""

    yield b"["
    first = True
    for item in items:
        model = to_model(item)
        prefix = b"" if first else b","
        payload = prefix + model.model_dump_json().encode("utf-8")
        yield from _chunk_bytes(payload, chunk_size)
        first = False
    yield b"]"


def stream_json_object(
    model: BaseModel,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> Iterator[bytes]:
    """Yield one validated model as a valid JSON object, field by field."""

    yield b"{"
    for index, (key, value) in enumerate(model.model_dump(mode="json").items()):
        prefix = "" if index == 0 else ","
        payload = (
            prefix
            + json.dumps(key, ensure_ascii=False)
            + ":"
            + json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        ).encode("utf-8")
        yield from _chunk_bytes(payload, chunk_size)
    yield b"}"
