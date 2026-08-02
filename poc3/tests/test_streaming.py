import json

from pydantic import BaseModel

from poc3.streaming import stream_json_array, stream_json_object


class DemoItem(BaseModel):
    name: str
    values: list[int]


def test_stream_json_array_is_chunked_and_remains_valid_json() -> None:
    items = [
        DemoItem(name="第一条", values=[1, 2]),
        DemoItem(name="第二条", values=[3]),
    ]

    chunks = list(
        stream_json_array(items, to_model=lambda item: item, chunk_size=5)
    )

    assert chunks[0] == b"["
    assert chunks[-1] == b"]"
    assert len(chunks) > len(items) + 2
    assert json.loads(b"".join(chunks)) == [
        {"name": "第一条", "values": [1, 2]},
        {"name": "第二条", "values": [3]},
    ]


def test_stream_json_object_is_chunked_and_remains_valid_json() -> None:
    item = DemoItem(name="流式报告", values=list(range(20)))

    chunks = list(stream_json_object(item, chunk_size=7))

    assert chunks[0] == b"{"
    assert chunks[-1] == b"}"
    assert len(chunks) > 4
    assert json.loads(b"".join(chunks)) == item.model_dump(mode="json")
