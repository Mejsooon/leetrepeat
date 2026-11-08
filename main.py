"""LeetRepeat — start aplikacji. Uruchomienie: python main.py → http://127.0.0.1:8000

Warstwy:
    api/          endpointy HTTP (routes.py) i walidacja danych (schemas.py)
    services/     logika: powtórki (scheduler.py), uruchamianie kodu (runner.py), zadania (tasks.py)
    repository/   cały SQL (tasks.py)
    core/         połączenie z bazą i schemat tabel (database.py)
"""
import os

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from api.routes import create_router

ROOT = os.path.dirname(os.path.abspath(__file__))


def create_app(db_path):
    app = FastAPI(title="LeetRepeat")
    # Tylko adresy lokalne: strona z internetu podszywająca się pod 127.0.0.1 (DNS rebinding)
    # dostanie 400 i nie uruchomi kodu na tym komputerze
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    app.include_router(create_router(db_path))
    # Frontend (pliki z static/) — montowany na końcu, żeby nie zasłaniał tras /api
    app.mount("/", StaticFiles(directory=os.path.join(ROOT, "static"), html=True), name="static")
    return app


app = create_app(os.environ.get("LEETREPEAT_DB", os.path.join(ROOT, "leetrepeat.db")))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
