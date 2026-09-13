from fastapi import FastAPI
from routes.model import router as model_router
from routes.argo import router as argo_router
from routes.comparison import router as comparison_router


app = FastAPI(
    title="OceanX API",
    description="API for OceanX ocean model and observation visualization",
    version="1.0.0"
)


app.include_router(model_router)
app.include_router(argo_router)
app.include_router(comparison_router)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "OceanX API"
    }