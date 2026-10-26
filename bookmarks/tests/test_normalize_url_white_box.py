"""Structural complement after black-box cases: independent guard conditions."""

import builtins
import urllib.parse
from unittest.mock import patch

import pytest

from bookmarks.utils import normalize_url


# A = not url, B = not isinstance(url, str), D = A or B.
# Logical unique-cause pairs: A -> MC01/MC02; B -> MC02/MC03.
# B is NOT EVALUATED in MC01, due to Python short-circuit semantics.
# Its logical value is false because the empty string is still a string.
@pytest.mark.parametrize(
    "value,expected,b_evaluated,parser_called",
    [
        pytest.param("", "", False, False, id="MC01-A1-B0-D1"),
        pytest.param(
            "https://example.com", "https://example.com", True, True, id="MC02-A0-B0-D0"
        ),
        pytest.param(42, "", True, False, id="MC03-A0-B1-D1"),
    ],
)
def test_normalize_url_mcdc(value, expected, b_evaluated, parser_called):
    # Spies delegate to the real operations; no fabricated parser output.
    with (
        patch(
            "bookmarks.utils.isinstance", wraps=builtins.isinstance, create=True
        ) as type_check,
        patch(
            "bookmarks.utils.urllib.parse.urlparse", wraps=urllib.parse.urlparse
        ) as parser,
    ):
        assert normalize_url(value) == expected
    assert type_check.call_count == int(b_evaluated)
    assert parser.call_count == int(parser_called)
