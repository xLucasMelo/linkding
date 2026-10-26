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
