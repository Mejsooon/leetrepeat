from datetime import date

import pytest

from scheduler import next_review, preview

today = date(2026, 11, 8)


@pytest.mark.parametrize("interval, rating, new_interval, due", [
    (0, "again", 1, date(2026, 11, 9)),
    (0, "partial", 1, date(2026, 11, 9)),
    (0, "good", 3, date(2026, 11, 11)),
    (6, "again", 1, date(2026, 11, 9)),
    (6, "partial", 7.2, date(2026, 11, 15)),
    (1, "partial", 2, date(2026, 11, 10)),     # max(1.2, 1+1)
    (6, "good", 15, date(2026, 11, 23)),
    (1, "good", 2.5, date(2026, 11, 11)),      # 2.5 zaokrąglone w górę, nie bankowo
])
def test_next_review(interval, rating, new_interval, due):
    got_interval, got_due = next_review(interval, rating, today)
    assert got_interval == pytest.approx(new_interval)
    assert got_due == due


def test_preview_new_task():
    assert preview(0) == {"again": 1, "partial": 1, "good": 3}


def test_preview_existing():
    assert preview(6) == {"again": 1, "partial": 7, "good": 15}


def test_unknown_rating_raises():
    with pytest.raises(ValueError):
        next_review(1, "maybe", today)
