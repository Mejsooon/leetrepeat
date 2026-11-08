"""Harmonogram powtórek (spec §5)."""
from datetime import date, timedelta


def next_review(interval_days: float, rating: str, today: date) -> tuple[float, date]:
    # Nowe zadanie (nigdy nieocenione) ma interval_days == 0
    is_new = interval_days == 0

    if rating == "again":
        new_interval = 1
    elif rating == "partial":
        if is_new:
            new_interval = 1
        else:
            # rośnie o 20%, ale zawsze co najmniej o 1 dzień
            new_interval = max(interval_days * 1.2, interval_days + 1)
    elif rating == "good":
        if is_new:
            new_interval = 3
        else:
            new_interval = interval_days * 2.5
    else:
        raise ValueError(f"Nieznana ocena: {rating}")

    # zaokrąglenie "połówka w górę" (round() w Pythonie zaokrągla 2.5 do 2)
    due = today + timedelta(days=int(new_interval + 0.5))
    return new_interval, due


def preview(interval_days: float) -> dict[str, int]:
    # Ile dni do powtórki dla każdej z trzech ocen (do podpisów pod przyciskami)
    today = date.today()
    result = {}
    for rating in ("again", "partial", "good"):
        _, due = next_review(interval_days, rating, today)
        result[rating] = (due - today).days
    return result
