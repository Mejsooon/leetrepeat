"""API: endpointy HTTP. Tylko przyjmują dane, wołają serwis i zwracają odpowiedź / kod błędu."""
from fastapi import APIRouter, HTTPException, Response

from api.schemas import ReviewIn, RunIn, TaskIn
from repository import tasks as repo
from services import runner
from services import tasks as service

NOT_FOUND = "Nie ma takiego zadania"


def create_router(db_path):
    router = APIRouter(prefix="/api")

    @router.get("/tasks")
    def list_tasks(language: str | None = None):
        return repo.list_tasks(db_path, language)

    @router.get("/tasks/{task_id}")
    def get_task(task_id: int):
        task = service.get_task(db_path, task_id)
        if task is None:
            raise HTTPException(404, NOT_FOUND)
        return task

    @router.post("/tasks", status_code=201)
    def create_task(body: TaskIn):
        return {"id": service.create_task(db_path, body.model_dump())}

    @router.put("/tasks/{task_id}")
    def update_task(task_id: int, body: TaskIn):
        if not repo.update_task(db_path, task_id, body.model_dump()):
            raise HTTPException(404, NOT_FOUND)
        return {"id": task_id}

    @router.delete("/tasks/{task_id}", status_code=204)
    def delete_task(task_id: int):
        if not repo.delete_task(db_path, task_id):
            raise HTTPException(404, NOT_FOUND)
        return Response(status_code=204)

    @router.get("/review/due")
    def due_tasks(language: str | None = None):
        return service.due_task_ids(db_path, language)

    @router.get("/summary")
    def summary():
        return service.summary(db_path)

    @router.post("/tasks/{task_id}/review")
    def review(task_id: int, body: ReviewIn):
        result = service.review_task(db_path, task_id, body.model_dump())
        if result is None:
            raise HTTPException(404, NOT_FOUND)
        return result

    @router.post("/tasks/{task_id}/review/undo")
    def undo_review(task_id: int):
        result = service.undo_review(db_path, task_id)
        if result == "missing":
            raise HTTPException(404, NOT_FOUND)
        if result is None:
            raise HTTPException(409, "Tej oceny nie da się cofnąć")
        return result

    @router.post("/run")
    def run(body: RunIn):
        # Zwykła funkcja (nie async): FastAPI uruchamia ją w osobnym wątku, więc serwer się nie blokuje
        try:
            results = runner.run_tests(body.language, body.kind, body.code, body.model_dump()["tests"])
        except runner.RuntimeMissing as e:
            raise HTTPException(400, str(e))
        return {"results": results}

    return router
