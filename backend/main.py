"""
File: main.py
Owner: BOTH CAN ADD
Created: 2026-03-21
Project: Learnova (eLearning Platform)
Purpose: Boot the backend API application for Learnova.
What it is: A FastAPI entrypoint with health checks and the initial auth routes.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.modules.admin.router import router as admin_router
from backend.modules.auth.router import router as auth_router
from backend.modules.courses.router import router as course_router


# This creates the shared FastAPI app instance used by local development and future deployment.
app = FastAPI(
    title="Learnova Backend",
    version="0.1.0",
    description="Backend API for Learnova learner and instructor workflows.",
)

# Frontend development currently runs through Vite, so localhost origins are allowed here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["system"])
def root():
    """
    A simple root endpoint helps confirm that the backend process is up.
    """

    return {
        "service": "learnova-backend",
        "status": "ok",
    }


@app.get("/health", tags=["system"])
def health():
    """
    This is the app-level health check and does not depend on the database.
    """

    return {
        "status": "ok",
        "service": "learnova-backend",
    }


# The auth router also exposes /auth and /db/health endpoints.
app.include_router(auth_router)
app.include_router(course_router)
app.include_router(admin_router)
