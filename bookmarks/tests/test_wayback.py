from datetime import UTC, datetime
from unittest.mock import patch

from django.test import SimpleTestCase

from bookmarks.services.wayback import generate_fallback_webarchive_url


class WaybackUrlBlackBoxTestCase(SimpleTestCase):
    """Equivalence partitions and boundary values of the public URL contract."""

    def test_builds_url_for_supplied_timestamp(self):
        # CP01: a nonempty URL and a supplied date produce an exact archive URL.
        timestamp = datetime(2023, 8, 11, 21, 45, 11, tzinfo=UTC)

        result = generate_fallback_webarchive_url("https://example.com/", timestamp)

        self.assertEqual(
            result, "https://web.archive.org/web/20230811214511/https://example.com/"
        )

    def test_preserves_original_url(self):
        # CP02: schemes, case, port, Unicode, query and fragment are preserved.
        urls = [
            "http://example.com",
            "https://EXAMPLE.com:8443/Path/?a=1&b=two%20words#Section",
            "https://example.com/café?q=a+b",
        ]
        timestamp = datetime(2026, 10, 22, 9, 5, 3, tzinfo=UTC)

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(
                    generate_fallback_webarchive_url(url, timestamp),
                    f"https://web.archive.org/web/20261022090503/{url}",
                )

    def test_returns_none_for_empty_url(self):
        # CP03: the empty-input partition has no archive URL.
        self.assertIsNone(
            generate_fallback_webarchive_url("", datetime(2026, 10, 22, tzinfo=UTC))
        )

    def test_returns_none_for_none_url(self):
        # CP04: None is also handled by the existing empty-input behavior.
        self.assertIsNone(
            generate_fallback_webarchive_url(None, datetime(2026, 10, 22, tzinfo=UTC))
        )

    def test_formats_midnight_with_leading_zeroes(self):
        # CP05: lower time boundary, 00:00:00; month and day also need padding.
        result = generate_fallback_webarchive_url(
            "https://example.com", datetime(2026, 1, 2, tzinfo=UTC)
        )

        self.assertEqual(
            result, "https://web.archive.org/web/20260102000000/https://example.com"
        )

    def test_formats_both_sides_of_year_boundary(self):
        # CP06: the last second of a year and the first second of the next.
        cases = [
            (datetime(1999, 12, 31, 23, 59, 59, tzinfo=UTC), "19991231235959"),
            (datetime(2000, 1, 1, 0, 0, 0, tzinfo=UTC), "20000101000000"),
        ]
        for timestamp, expected in cases:
            with self.subTest(timestamp=timestamp):
                self.assertEqual(
                    generate_fallback_webarchive_url("https://example.com", timestamp),
                    f"https://web.archive.org/web/{expected}/https://example.com",
                )

    def test_formats_leap_day_boundary(self):
        # CP07: the leap-day transition must retain the calendar date.
        cases = [
            (datetime(2024, 2, 28, 23, 59, 59, tzinfo=UTC), "20240228235959"),
            (datetime(2024, 2, 29, 0, 0, 0, tzinfo=UTC), "20240229000000"),
            (datetime(2024, 2, 29, 23, 59, 59, tzinfo=UTC), "20240229235959"),
            (datetime(2024, 3, 1, 0, 0, 0, tzinfo=UTC), "20240301000000"),
        ]
        for timestamp, expected in cases:
            with self.subTest(timestamp=timestamp):
                self.assertEqual(
                    generate_fallback_webarchive_url("https://example.com", timestamp),
                    f"https://web.archive.org/web/{expected}/https://example.com",
                )

    def test_uses_second_precision_without_rounding(self):
        # CP08: microsecond limits must not round into the following second/year.
        for microsecond in (0, 1, 999999):
            with self.subTest(microsecond=microsecond):
                timestamp = datetime(2026, 12, 31, 23, 59, 59, microsecond, tzinfo=UTC)
                self.assertEqual(
                    generate_fallback_webarchive_url("https://example.com", timestamp),
                    "https://web.archive.org/web/20261231235959/https://example.com",
                )


class WaybackUrlWhiteBoxTestCase(SimpleTestCase):
    """The three feasible paths of two sequential, single-condition decisions."""

    @patch("bookmarks.services.wayback.timezone.now")
    def test_empty_url_returns_before_reading_clock(self, clock):
        # CB01: D1=true; D2 is not reached, even when the date is absent.
        self.assertIsNone(generate_fallback_webarchive_url("", None))
        clock.assert_not_called()

    @patch("bookmarks.services.wayback.timezone.now")
    def test_supplied_timestamp_bypasses_clock(self, clock):
        # CB02: D1=false, D2=false. The supplied date must be used.
        result = generate_fallback_webarchive_url(
            "https://example.com", datetime(2026, 10, 22, 9, 5, 3, tzinfo=UTC)
        )

        self.assertEqual(
            result, "https://web.archive.org/web/20261022090503/https://example.com"
        )
        clock.assert_not_called()

    @patch(
        "bookmarks.services.wayback.timezone.now",
        return_value=datetime(2026, 10, 22, 9, 5, 3, tzinfo=UTC),
    )
    def test_missing_timestamp_reads_current_time(self, clock):
        # CB03: D1=false, D2=true. Control the external clock, not the helper.
        result = generate_fallback_webarchive_url("https://example.com", None)

        self.assertEqual(
            result, "https://web.archive.org/web/20261022090503/https://example.com"
        )
        clock.assert_called_once_with()

    @patch(
        "bookmarks.services.wayback.timezone.now",
        side_effect=[
            datetime(2026, 12, 31, 23, 59, 59, tzinfo=UTC),
            datetime(2027, 1, 1, tzinfo=UTC),
        ],
    )
    def test_missing_timestamp_is_recomputed_on_each_call(self, clock):
        # CB04: repeated fallback calls must not cache a date across the boundary.
        first = generate_fallback_webarchive_url("https://example.com", None)
        second = generate_fallback_webarchive_url("https://example.com", None)

        self.assertEqual(
            first, "https://web.archive.org/web/20261231235959/https://example.com"
        )
        self.assertEqual(
            second, "https://web.archive.org/web/20270101000000/https://example.com"
        )
        self.assertEqual(clock.call_count, 2)
