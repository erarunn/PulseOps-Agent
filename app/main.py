from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import settings, BASE_DIR
from app.db.database import init_db
from app.api.routes import router as api_router

app = FastAPI(
    title="PulseOps Engineering Assistant",
    description="A lightweight Engineering Operations Agent for Northstar Checkout",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router)

# Mount Web Directory
web_dir = BASE_DIR / "web"
if web_dir.exists():
    app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/", include_in_schema=False)
def serve_index():
    index_path = BASE_DIR / "web" / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "PulseOps API running. Visit /docs for Swagger API documentation."}

if __name__ == "__main__":
    import uvicorn
    init_db()
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
