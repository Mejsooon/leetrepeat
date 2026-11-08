"""Service: logika aplikacji — daty, harmonogram powtórek. Nie zna HTTP ani SQL."""
from datetime import date, datetime, timedelta

from repository import tasks as repo
from services.scheduler import next_review, preview


def today():
    # Lokalna data komputera ("dziś" dla powtórek). Testy podmieniają tę funkcję.
    return date.today()


def now():
    return datetime.now().isoformat(timespec="seconds")


def get_task(db_path, task_id):
    """Zadanie do wyświetlenia: dane z bazy + podgląd terminów dla trzech ocen. None, gdy brak."""
    task = repo.get_task(db_path, task_id)
    if task is None:
        return None
    task["preview"] = preview(task["interval_days"])
    return task


def create_task(db_path, task):
    # Nowe zadanie jest do powtórki od razu (od dziś)
    return repo.create_task(db_path, task, now(), today().isoformat())


def due_task_ids(db_path, language=None):
    return repo.due_task_ids(db_path, today().isoformat(), language)


def summary(db_path):
    result = {}
    for language in ("python", "csharp"):
        due, total = repo.count_tasks(db_path, language, today().isoformat())
        result[language] = {"due": due, "total": total}
    result["last_session"] = repo.last_session(db_path)
    return result


def queue(db_path, language=None):
    return repo.queue(db_path, today().isoformat(), language)


def forecast(db_path, language=None):
    """14 dni od dziś: [{date, count}], zaległe zadania liczą się do dziś."""
    start = today()
    end = start + timedelta(days=13)
    counts = repo.due_counts_between(db_path, start.isoformat(), end.isoformat(), language)
    days = []
    for i in range(14):
        day = (start + timedelta(days=i)).isoformat()
        days.append({"date": day, "count": counts.get(day, 0)})
    return days


def review_task(db_path, task_id, review):
    """Zapisuje ocenę i wylicza nowy termin. Zwraca {interval_days, due_date} albo None, gdy brak zadania."""
    task = repo.get_task(db_path, task_id)
    if task is None:
        return None
    new_interval, due = next_review(task["interval_days"], review["rating"], today())
    repo.save_review(db_path, task_id, review, new_interval, due.isoformat(), now(),
                     task["interval_days"], task["due_date"])
    return {"interval_days": new_interval, "due_date": due.isoformat()}


def undo_review(db_path, task_id):
    """Cofa najnowszą ocenę. Zwraca "missing" (brak zadania), None (nie da się cofnąć) albo nowy stan."""
    if repo.get_task(db_path, task_id) is None:
        return "missing"
    return repo.undo_last_review(db_path, task_id)
