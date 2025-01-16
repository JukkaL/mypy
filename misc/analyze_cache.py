#!/usr/bin/env python

from __future__ import annotations

import json
import os
import os.path
from collections import Counter
from collections.abc import Iterable
from typing import Any, Final
from typing_extensions import TypeAlias as _TypeAlias

ROOT: Final = ".mypy_cache/3.5"

JsonDict: _TypeAlias = dict[str, Any]


class CacheData:
    def __init__(
        self,
        filename: str,
        data_json: JsonDict,
        meta_json: JsonDict,
        data_size: int,
        meta_size: int,
    ) -> None:
        self.filename = filename
        self.data = data_json
        self.meta = meta_json
        self.data_size = data_size
        self.meta_size = meta_size

    @property
    def total_size(self) -> int:
        return self.data_size + self.meta_size


def extract_classes(chunks: Iterable[CacheData]) -> Iterable[JsonDict]:
    def extract(chunks: Iterable[JsonDict]) -> Iterable[JsonDict]:
        for chunk in chunks:
            if isinstance(chunk, dict):
                yield chunk
                yield from extract(chunk.values())
            elif isinstance(chunk, list):
                yield from extract(chunk)

    yield from extract([chunk.data for chunk in chunks])


def load_json(data_path: str, meta_path: str) -> CacheData:
    with open(data_path) as ds:
        data_json = json.load(ds)

    with open(meta_path) as ms:
        meta_json = json.load(ms)

    data_size = os.path.getsize(data_path)
    meta_size = os.path.getsize(meta_path)

    return CacheData(
        data_path.replace(".data.json", ".*.json"), data_json, meta_json, data_size, meta_size
    )


def get_files(root: str) -> Iterable[CacheData]:
    for dirpath, dirnames, filenames in os.walk(root):
        for filename in filenames:
            if filename.endswith(".data.json"):
                meta_filename = filename.replace(".data.json", ".meta.json")
                yield load_json(
                    os.path.join(dirpath, filename), os.path.join(dirpath, meta_filename)
                )


def pluck(name: str, chunks: Iterable[JsonDict]) -> Iterable[JsonDict]:
    return (chunk for chunk in chunks if chunk[".class"] == name)


def report_counter(counter: Counter[str], amount: int | None = None) -> None:
    if amount is None:
        amount = len(counter)  # default to the length of the counter if `amount` is None
    for name, count in counter.most_common(amount):
        print(f"    {count: <8} {name}")
    print()


def report_most_common(chunks: list[JsonDict], amount: int | None = None) -> None:
    report_counter(Counter(str(chunk) for chunk in chunks), amount)


def compress(chunk: JsonDict) -> JsonDict:
    cache: dict[int, JsonDict] = {}
    counter = 0

    def helper(chunk: JsonDict) -> JsonDict:
        nonlocal counter
        if not isinstance(chunk, dict):
            return chunk

        if len(chunk) <= 2:
            return chunk
        id = hash(str(chunk))

        if id in cache:
            return cache[id]
        else:
            cache[id] = {".id": counter}
            chunk[".cache_id"] = counter
            counter += 1

        for name in sorted(chunk.keys()):
            value = chunk[name]
            if isinstance(value, list):
                chunk[name] = [helper(child) for child in value]
            elif isinstance(value, dict):
                chunk[name] = helper(value)

        return chunk

    out = helper(chunk)
    return out


def decompress(chunk: JsonDict) -> JsonDict:
    cache: dict[int, JsonDict] = {}

    def helper(chunk: JsonDict) -> JsonDict:
        if not isinstance(chunk, dict):
            return chunk
        if ".id" in chunk:
            return cache[chunk[".id"]]

        counter = None
        if ".cache_id" in chunk:
            counter = chunk[".cache_id"]
            del chunk[".cache_id"]

        for name in sorted(chunk.keys()):
            value = chunk[name]
            if isinstance(value, list):
                chunk[name] = [helper(child) for child in value]
            elif isinstance(value, dict):
                chunk[name] = helper(value)

        if counter is not None:
            cache[counter] = chunk

        return chunk

    return helper(chunk)


def main() -> None:
    json_chunks = list(get_files(ROOT))
    class_chunks = list(extract_classes(json_chunks))

    total_size = sum(chunk.total_size for chunk in json_chunks)
    print(f"Total cache size: {total_size / (1024 * 1024):.3f} megabytes")
    print()

    class_name_counter = Counter(chunk[".class"] for chunk in class_chunks)
    print("Most commonly used classes:")
    report_counter(class_name_counter)

    print("Most common literal chunks:")
    report_most_common(class_chunks, 15)

    build = None
    for chunk in json_chunks:
        if "build.*.json" in chunk.filename:
            build = chunk
            break
    assert build is not None
    original = json.dumps(build.data, sort_keys=True)
    print(f"Size of build.data.json, in kilobytes: {len(original) / 1024:.3f}")

    build.data = compress(build.data)
    compressed = json.dumps(build.data, sort_keys=True)
    print(f"Size of compressed build.data.json, in kilobytes: {len(compressed) / 1024:.3f}")

    build.data = decompress(build.data)
    decompressed = json.dumps(build.data, sort_keys=True)
    print(f"Size of decompressed build.data.json, in kilobytes: {len(decompressed) / 1024:.3f}")

    print("Lossless conversion back", original == decompressed)

    """var_chunks = list(pluck("Var", class_chunks))
    report_most_common(var_chunks, 20)
    print()

    #for var in var_chunks:
    #    if var['fullname'] == 'self' and not (isinstance(var['type'], dict) and var['type']['.class'] == 'AnyType'):
    #        print(var)
    #argument_chunks = list(pluck("Argument", class_chunks))

    symbol_table_node_chunks = list(pluck("SymbolTableNode", class_chunks))
    report_most_common(symbol_table_node_chunks, 20)

    print()
    print("Most common")
    report_most_common(class_chunks, 20)
    print()"""


if __name__ == "__main__":
    main()
