"""FastAPI app cho EAUT - REST API server.

Chay: uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
Docs: http://localhost:8000/docs (Swagger UI auto-generated)
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routers import (
    attendance, audit, auth, courses, curriculum, exams, grades,
    notifications, registrations, schedules, semesters, stats, users
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: kiem tra DB ket noi
    from backend.database.db import db
    if db.is_connected():
        print('[API] Da ket noi PostgreSQL')
    else:
        print('[API] CANH BAO: Khong ket noi duoc DB!')
    yield
    # Shutdown
    print('[API] Shutting down...')


app = FastAPI(
    title='EAUT Course Registration API',
    description='REST API cho he thong dang ky khoa hoc EAUT - 16 service / 90+ endpoints',
    version='1.0.0',
    lifespan=lifespan,
)

# Cho phep frontend PyQt5 (chay local) goi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],  # Production nen restrict origins
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Mount routers - moi service 1 router
app.include_router(auth.router, prefix='/auth', tags=['Auth'])
app.include_router(courses.router, prefix='', tags=['Courses & Classes'])
app.include_router(registrations.router, prefix='/registrations', tags=['Registrations'])
app.include_router(grades.router, prefix='/grades', tags=['Grades'])
app.include_router(notifications.router, prefix='/notifications', tags=['Notifications'])
app.include_router(users.router, prefix='', tags=['Users'])
app.include_router(stats.router, prefix='/stats', tags=['Stats'])
app.include_router(semesters.router, prefix='/semesters', tags=['Semesters'])
app.include_router(curriculum.router, prefix='/curriculum', tags=['Curriculum'])
app.include_router(schedules.router, prefix='/schedules', tags=['Schedules'])
app.include_router(exams.router, prefix='/exams', tags=['Exams'])
app.include_router(attendance.router, prefix='/attendance', tags=['Attendance'])
app.include_router(audit.router, prefix='/audit', tags=['Audit'])


@app.get('/', tags=['Health'])
def root():
    """Health check + API metadata."""
    return {
        'service': 'EAUT API',
        'status': 'ok',
        'docs': '/docs',
        'redoc': '/redoc',
    }


@app.get('/health', tags=['Health'])
def health():
    """Lieveness probe - check DB connection."""
    from backend.database.db import db
    return {
        'api': 'ok',
        'db': 'connected' if db.is_connected() else 'down',
    }
