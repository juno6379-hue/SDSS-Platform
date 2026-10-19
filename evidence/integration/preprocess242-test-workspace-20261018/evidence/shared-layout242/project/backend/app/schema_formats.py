"""Detached JSON Schema format checkers with a dependency-free date-time subset.

This checks calendar/clock/zone syntax, not interval ordering or science policy.
Leap seconds and year 0000 are outside the supported subset.
"""
from datetime import datetime
import re

from jsonschema import FormatChecker


_ZONED_DATE_TIME = re.compile(
    r'[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt][0-9]{2}:[0-9]{2}:[0-9]{2}'
    r'(?:\.[0-9]+)?(?:[Zz]|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])'
)


def create_format_checker():
    """Return a fresh checker without changing class/global or cached checkers."""
    checker = FormatChecker()

    @checker.checks('date-time')
    def date_time(value):
        # JSON Schema's type keyword owns non-string rejection.
        if type(value) is not str:
            return True
        if _ZONED_DATE_TIME.fullmatch(value) is None:
            return False
        try:
            datetime.fromisoformat(value.upper().replace('Z', '+00:00'))
            return True
        except ValueError:
            return False

    return checker
