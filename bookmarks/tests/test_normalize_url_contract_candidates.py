"""Explicit contract hypotheses; failures must remain visible in the evidence."""

import pytest

from bookmarks.utils import normalize_url


@pytest.mark.xfail(
    strict=True,
    reason="Known functional discrepancies; see atividade_normalize_url/RELATORIO.md",
)
@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param(
            "https://EXAMPLE.COM:0", "https://example.com:0", id="CP30-port-zero"
        ),
        pytest.param(
            "https://[2001:DB8::1]:443/",
            "https://[2001:db8::1]:443",
            id="CP31-ipv6-brackets",
        ),
    ],
)
def test_normalize_url_contract_candidate(value, expected):
    assert normalize_url(value) == expected
