from __future__ import annotations

import dataclasses
import json
import re
import textwrap
from collections.abc import Generator, Sequence
from pathlib import Path
from typing import Any

DIR = Path(__file__).parent.resolve()


@dataclasses.dataclass(frozen=True)
class ConfigOpt:
    name: str
    type_str: str
    is_global: bool
    description: str
    default: str | None

    def define(self) -> dict[str, str]:
        retval: dict[str, Any] = {"description": self.description}
        if self.default is not None:
            match self.type_str:
                case "boolean":
                    retval["default"] = {"true": True, "false": False}[self.default.lower()]
                case "integer":
                    retval["default"] = int(self.default)
                case "string":
                    retval["default"] = self.default.strip("`")
                case _:
                    msg = f"Default not suppored for {self.type_str}"
                    raise RuntimeError(msg)
        match self.type_str:
            case "boolean" | "integer" | "string":
                retval["type"] = self.type_str
            case "comma-separated list of strings" | "regular expression":
                retval["oneOf"] = [
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string"}},
                ]
            case _:
                msg = f"{self.type_str} not supported for type"
                raise RuntimeError(msg)

        return retval


def parse_rst_docs(txt: str) -> Generator[ConfigOpt, None, None]:
    for match in re.finditer(r".. confval:: ([^\s]*)\n\n((?:    .*\n|\n)*)", txt):
        name, body = match.groups()
        body = textwrap.dedent(body)
        body_match = re.match(r":type: (.*?)\n(?::default: (.*?)\n)?(.*)$", body, re.DOTALL)
        assert body_match is not None, f"{name} missing type and default!\n{body!r}"
        type_str, default, inner = body_match.groups()
        is_global = "only be set in the global section" in body
        description = inner.strip().split("\n\n")[0].replace("\n", " ")
        # Patches
        if name == "mypy_path":
            type_str = "comma-separated list of strings"
        yield ConfigOpt(
            name=name,
            type_str=type_str,
            is_global=is_global,
            description=description,
            default=default,
        )


def make_schema(opts: Sequence[ConfigOpt]) -> dict[str, Any]:
    definitions = {s.name: s.define() for s in opts}
    overrides = {s.name: {"$ref": f"#/properties/{s.name}"} for s in opts if not s.is_global}
    module = {
        "oneOf": [
            {"type": "string"},
            {"type": "array", "items": {"type": "string"}, "minItems": 1},
        ]
    }

    # Improve some fields
    definitions["follow_imports"]["enum"] = ["normal", "silent", "skip", "error"]

    # Undocumented fields
    definitions["show_error_codes"] = {
        "type": "boolean",
        "default": True,
        "description": "DEPRECATED and UNDOCUMENTED: Now defaults to true, use `hide_error_codes` if you need to disable error codes instead.",
        "deprecated": True,
    }
    definitions.setdefault(
        "show_error_code_links",
        {
            "type": "boolean",
            "default": False,
            "description": "UNDOCUMENTED: show links for error codes.",
        },
    )

    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "https://json.schemastore.org/partial-mypy.json",
        "additionalProperties": False,
        "type": "object",
        "properties": {
            **definitions,
            "overrides": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["module"],
                    "minProperties": 2,
                    "properties": {"module": module, **overrides},
                },
            },
        },
    }


if __name__ == "__main__":
    filepath = DIR.parent / "docs/source/config_file.rst"
    opts = parse_rst_docs(filepath.read_text())
    print(json.dumps(make_schema(list(opts)), indent=2))
