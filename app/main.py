from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.core.database import Base, engine
from app.models.user import UserModel
from app.models.sleep import SleepLogModel
from app.models.progress import DailySleepLogModel, UserProfileModel
from app.api.routes import router as api_router
from app.api.auth import router as auth_router
from app.api.progress import router as progress_router

# Crea las tablas en PostgreSQL si no existen todavía
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME)
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Registrar routers de la API y Autenticación en la app principal
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(progress_router, prefix=settings.API_V1_STR)

@app.get("/")
def home_frontend():
    return FileResponse(static_dir / "index.html")