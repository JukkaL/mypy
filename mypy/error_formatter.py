"""Defines the different custom formats in which mypy can output."""

import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mypy.errors import MypyError


class ErrorFormatter(ABC):
    """Base class to define how errors are formatted before being printed."""

    @abstractmethod
    def report_error(self, error: "MypyError") -> str:
        raise NotImplementedError


class JSONFormatter(ErrorFormatter):
    """Formatter for basic JSON output format."""

    def report_error(self, error: "MypyError") -> str:
        """Prints out the errors as simple, static JSON lines."""
        return json.dumps(
            {
                "file": error.file_path,
                "line": error.line,
                "column": error.column,
                "message": error.message,
                "hint": None if len(error.hints) == 0 else "\n".join(error.hints),
                "code": None if error.errorcode is None else error.errorcode.code,
                "severity": error.severity,
            }
        )


class GitHubFormatter(ErrorFormatter):
    """Formatter for GitHub Actions output format."""

    def report_error(self, error: "MypyError") -> str:
        """Prints out the errors as GitHub Actions annotations."""
        command = "error" if error.severity == "error" else "notice"
        title = f"Mypy ({error.errorcode.code})" if error.errorcode is not None else "Mypy"

        message = f"{error.message}."

        if error.hints:
            message += "%0A%0A"
            message += "%0A".join(error.hints)

        return (
            f"::{command} "
            f"file={error.file_path},"
            f"line={error.line},"
            f"col={error.column},"
            f"title={title}"
            f"::{message}"
        )


OUTPUT_CHOICES = {"json": JSONFormatter(), "github": GitHubFormatter()}
