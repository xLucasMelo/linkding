import datetime
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from bookmarks.utils import humanize_relative_date


class HumanizeRelativeDateTest(TestCase):
    """Testes para a função humanize_relative_date (caixa-preta + caixa-branca)."""

    def setUp(self):
        # Data de referência fixa para evitar flakiness
        self.now = timezone.datetime(2021, 1, 1, 12, 0, 0)

    
    # CAIXA-PRETA: Classes de equivalência e valor limite
    # ------------------------------------------------------------------

    def test_today(self):
        """CT01: Data de hoje retorna 'Today' (CE06)."""
        result = humanize_relative_date(self.now, self.now)
        self.assertEqual(result, "Today")

    def test_yesterday(self):
        """CT02: Data de ontem retorna 'Yesterday' (CE05)."""
        value = self.now - datetime.timedelta(days=1)
        result = humanize_relative_date(value, self.now)
        self.assertEqual(result, "Yesterday")

    def test_two_days_ago(self):
        """CT03: Data de 2 dias atrás retorna nome do dia (CE04)."""
        value = self.now - datetime.timedelta(days=2)
        result = humanize_relative_date(value, self.now)
        # 2 dias antes de 2021-01-01 (sexta) é 2020-12-30 (quarta)
        self.assertEqual(result, "Wednesday")

    def test_six_days_ago(self):
        """CT04: Data de 6 dias atrás retorna nome do dia (CE04)."""
        value = self.now - datetime.timedelta(days=6)
        result = humanize_relative_date(value, self.now)
        # 6 dias antes de 2021-01-01 (sexta) é 2020-12-26 (sábado)
        self.assertEqual(result, "Saturday")

    def test_one_week_ago(self):
        """CT05: Data de 7 dias atrás retorna '1 week ago' (CE03)."""
        value = self.now - datetime.timedelta(days=7)
        result = humanize_relative_date(value, self.now)
        self.assertEqual(result, "1 week ago")

    def test_one_month_ago(self):
        """CT06: Data de 1 mês atrás retorna '1 month ago' (CE02)."""
      # Usar datas específicas em vez de timedelta, pois o cálculo de meses
        # é baseado em calendário, não em dias corridos.
        value = timezone.datetime(2021, 1, 1)
        now = timezone.datetime(2021, 2, 1)
        result = humanize_relative_date(value, now)
        self.assertEqual(result, "1 month ago")

    def test_one_year_ago(self):
        """CT07: Data de 1 ano atrás retorna '1 year ago' (CE01)."""
        # Usar datas específicas em vez de timedelta, pois o cálculo de anos
     # é baseado em calendário, não em dias corridos.
        value = timezone.datetime(2021, 1, 1)
        now = timezone.datetime(2022, 1, 1)
        result = humanize_relative_date(value, now)
        self.assertEqual(result, "1 year ago")

    def test_future_date(self):
        """CT08: Data futura (CE07). Documenta comportamento inesperado."""
        value = self.now + datetime.timedelta(days=1)
        result = humanize_relative_date(value, self.now)
        # O comportamento não é especificado; documentamos o que acontece
        self.assertIsInstance(result, str)

    
    # CAIXA-BRANCA: Cobertura de decisões (branches)
    # ------------------------------------------------------------------

    def test_now_not_provided(self):
        """CT09: D1=True (now não passado) — usa timezone.now()."""
        with patch.object(timezone, "now", return_value=self.now):
            result = humanize_relative_date(self.now)
            self.assertEqual(result, "Today")

    def test_now_provided(self):
        """CT10: D1=False (now passado) — usa o now fornecido."""
        result = humanize_relative_date(self.now, self.now)
        self.assertEqual(result, "Today")

    def test_years_branch_true(self):
        """CT11: D2=True (delta.years > 0)."""
        value = timezone.datetime(2021, 1, 1)
        now = timezone.datetime(2022, 1, 1)
        result = humanize_relative_date(value, now)
        self.assertEqual(result, "1 year ago")

    def test_years_branch_false(self):
        """CT12: D2=False (delta.years == 0)."""
        value = timezone.datetime(2021, 1, 1)
        now = timezone.datetime(2021, 2, 1)
        result = humanize_relative_date(value, now)
        self.assertEqual(result, "1 month ago")

    def test_months_branch_true(self):
        """CT13: D3=True (delta.months > 0)."""
        value = timezone.datetime(2021, 1, 1)
        now = timezone.datetime(2021, 2, 1)
        result = humanize_relative_date(value, now)
        self.assertEqual(result, "1 month ago")

    def test_months_branch_false(self):
        """CT14: D3=False (delta.months == 0)."""
        value = self.now - datetime.timedelta(days=7)
        result = humanize_relative_date(value, self.now)
        self.assertEqual(result, "1 week ago")

    def test_weeks_branch_true(self):
        """CT15: D4=True (delta.weeks > 0)."""
        value = self.now - datetime.timedelta(days=7)
        result = humanize_relative_date(value, self.now)
        self.assertEqual(result, "1 week ago")

    def test_weeks_branch_false(self):
        """CT16: D4=False (delta.weeks == 0)."""
        value = self.now - datetime.timedelta(days=2)
        result = humanize_relative_date(value, self.now)
        self.assertEqual(result, "Wednesday")

    def test_same_day_branch_true(self):
        """CT17: D5=True (value.day == now.day)."""
        result = humanize_relative_date(self.now, self.now)
        self.assertEqual(result, "Today")

    def test_same_day_branch_false(self):
        """CT18: D5=False (value.day != now.day)."""
        value = self.now - datetime.timedelta(days=1)
        result = humanize_relative_date(value, self.now)
        self.assertEqual(result, "Yesterday")

    def test_yesterday_branch_true(self):
        """CT19: D6=True (value.day == yesterday.day)."""
        value = self.now - datetime.timedelta(days=1)
        result = humanize_relative_date(value, self.now)
        self.assertEqual(result, "Yesterday")

    def test_yesterday_branch_false(self):
        """CT20: D6=False (value.day != yesterday.day)."""
        value = self.now - datetime.timedelta(days=2)
        result = humanize_relative_date(value, self.now)
        self.assertEqual(result, "Wednesday")
