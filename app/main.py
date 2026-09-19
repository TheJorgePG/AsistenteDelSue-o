from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.config import settings
from app.api.routes import router as api_router

# Punto de entrada FastAPI
app = FastAPI(title=settings.PROJECT_NAME)

# Registrar las rutas
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return JSONResponse(
        content={"message": f"Bienvenido a {settings.PROJECT_NAME}"},
        headers={"Content-Type": "application/json; charset=utf-8"}
    )