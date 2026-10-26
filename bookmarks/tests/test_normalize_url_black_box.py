"""Functional additions: equivalence classes and boundary values (CP IDs)."""

import pytest

from bookmarks.utils import normalize_url

# ID, input, expected result, requirement, technique, justification
CASES = [
    ("CP01", "", "", "R1", "AVL/PE", "Zero characters: empty class"),
    ("CP02", " ", "", "R1", "AVL/PE", "One blank character"),
    ("CP03", "x", "x", "R1", "AVL/PE", "One nonblank character; relative reference"),
    (
        "CP04",
        "\t\n https://EXAMPLE.COM/A \r\n",
        "https://example.com/A",
        "R2",
        "PE",
        "External mixed whitespace",
    ),
    ("CP05", None, "", "R1", "PE", "Absent nonstring input"),
    ("CP06", 0, "", "R1", "PE", "Falsy numeric input"),
    ("CP07", 42, "", "R1", "PE", "Truthy numeric input"),
    ("CP08", b"https://example.com", "", "R1", "PE", "Bytes are not strings"),
    (
        "CP09",
        "https://EXAMPLE.COM/p",
        "https://example.com/p",
        "R3",
        "AVL",
        "Zero trailing slashes",
    ),
    (
        "CP10",
        "https://EXAMPLE.COM/p/",
        "https://example.com/p",
        "R3",
        "AVL",
        "One trailing slash",
    ),
    (
        "CP11",
        "https://EXAMPLE.COM/p//",
        "https://example.com/p",
        "R3",
        "AVL",
        "Two trailing slashes",
    ),
    (
        "CP12",
        "https://EXAMPLE.COM/a//b/",
        "https://example.com/a//b",
        "R3",
        "PE",
        "Internal slash must remain",
    ),
    (
        "CP13",
        "https://EXAMPLE.COM",
        "https://example.com",
        "R4",
        "AVL",
        "Zero query parameters",
    ),
    (
        "CP14",
        "https://EXAMPLE.COM?b=2",
        "https://example.com?b=2",
        "R4",
        "AVL",
        "One query parameter",
    ),
    (
        "CP15",
        "https://EXAMPLE.COM?b=2&a=1",
        "https://example.com?a=1&b=2",
        "R4",
        "AVL",
        "Two unsorted parameters",
    ),
]


@pytest.mark.parametrize(
    "case_id,value,expected,requirement,technique,reason",
    CASES,
    ids=[row[0] for row in CASES],
)
def test_normalize_url_black_box(
    case_id, value, expected, requirement, technique, reason
):
    assert normalize_url(value) == expected, (
        f"{case_id} {requirement} {technique}: {reason}"
    )
