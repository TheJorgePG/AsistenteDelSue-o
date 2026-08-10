from fastapi import FastAPI
from app.config import settings
from app.api.routes import router as api_router

#Punto de entradas FastAPI

app = FastAPI(title=settings.PROJECT_NAME)

# Registrar las rutas
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {"message": f"Bienvenido a {settings.PROJECT_NAME}"}