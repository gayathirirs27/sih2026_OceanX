from fastapi import FastAPI

app = FastAPI(title="OceanX API")


@app.get("/")
def home():
    return {
        "message": "OceanX API is running"
    }