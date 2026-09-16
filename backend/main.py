from fastapi import FastAPI
from backend.routes.model import router as model_router
from backend.routes.argo import router as argo_router
from backend.routes.glider import router as glider_router
from backend.routes.comparison import router as comparison_router
from backend.routes.analytics import router as analytics_router
from backend.routes.chlorophyll import router as chlorophyll_router
from fastapi.middleware.cors import CORSMiddleware
from backend.routes.nrt import router as nrt_router
from backend.routes.researcher import router as researcher_router
from backend.routes.forecaster import router as forecaster_router
from backend.routes.fisheries import router as fisheries_router
from backend.routes.search_rescue import router as search_rescue_router
from backend.routes.student import router as student_router
from backend.routes.policymaker import router as policymaker_router

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


#-app.include_router(model_router)
app.include_router(argo_router)
app.include_router(glider_router)
app.include_router(comparison_router)
app.include_router(chlorophyll_router)
app.include_router(analytics_router)
app.include_router(nrt_router)
app.include_router(researcher_router)
app.include_router(forecaster_router)
app.include_router(fisheries_router)
app.include_router(search_rescue_router)
app.include_router(student_router)
app.include_router(policymaker_router)
@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "OceanX API"
    }