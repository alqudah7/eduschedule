from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import auth, teachers, duties, schedule, substitutions, alerts, reports

app = FastAPI(title="EduSchedule API", version="1.0.0", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(teachers.router, prefix="/api/teachers", tags=["teachers"])
app.include_router(duties.router, prefix="/api/duties", tags=["duties"])
app.include_router(schedule.router, prefix="/api/schedule", tags=["schedule"])
app.include_router(substitutions.router, prefix="/api/substitutions", tags=["substitutions"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
