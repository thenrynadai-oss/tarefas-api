from datetime import date, datetime, timedelta, timezone

import pytest

from app.clock import local_today


def test_late_evening_in_sao_paulo_is_still_the_same_day():
    # 01h30 UTC de 02/10 = 22h30 de 01/10 em São Paulo.
    assert local_today(datetime(2026, 10, 2, 1, 30, tzinfo=timezone.utc)) == date(2026, 10, 1)


def test_from_three_am_utc_it_is_the_next_day():
    assert local_today(datetime(2026, 10, 2, 3, 0, tzinfo=timezone.utc)) == date(2026, 10, 2)


def test_accepts_any_input_time_zone():
    tokyo = timezone(timedelta(hours=9))
    assert local_today(datetime(2026, 10, 2, 10, 0, tzinfo=tokyo)) == date(2026, 10, 1)


def test_follows_historic_daylight_saving_time():
    # Em janeiro de 2019 São Paulo estava em horário de verão (UTC-2).
    # Com um offset fixo de -3, este instante cairia em 14/01.
    assert local_today(datetime(2019, 1, 15, 2, 30, tzinfo=timezone.utc)) == date(2019, 1, 15)


def test_naive_datetime_is_refused():
    with pytest.raises(ValueError):
        local_today(datetime(2026, 10, 1, 12, 0))
