from fastapi import FastAPI
from backend.routes.model import router as model_router
from backend.routes.argo import router as argo_router
from backend.routes.glider import router as glider_router
from backend.routes.comparison import router as comparison_router
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="OceanX API",
    description="API for OceanX ocean model and observation visualization",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(model_router)
app.include_router(argo_router)
app.include_router(glider_router)
app.include_router(comparison_router)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "OceanX API"
    }