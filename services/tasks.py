"""Service: logika aplikacji — daty, harmonogram powtórek. Nie zna HTTP ani SQL."""
from datetime import date, datetime

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
    return result


def review_task(db_path, task_id, review):
    """Zapisuje ocenę i wylicza nowy termin. Zwraca {interval_days, due_date} albo None, gdy brak zadania."""
    task = repo.get_task(db_path, task_id)
    if task is None:
        return None
    new_interval, due = next_review(task["interval_days"], review["rating"], today())
    repo.save_review(db_path, task_id, review, new_interval, due.isoformat(), now())
    return {"interval_days": new_interval, "due_date": due.isoformat()}
