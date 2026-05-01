"""FastAPI app cho EAUT - REST API server.

Chay: uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
Docs: http://localhost:8000/docs (Swagger UI auto-generated)
"""
from contextlib import asynccontextmanager

import psycopg2
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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


# ===== Global exception handlers =====
# Convert psycopg2 errors thanh HTTP response co message ro rang
# (thay vi 500 Internal Server Error) - giup frontend hien error popup chinh xac

# Map ten constraint -> message tieng Viet de bao loi
_FK_MESSAGES = {
    'classes_ma_mon_fkey': 'Môn học này đang có lớp tham chiếu, không xóa được. Hãy xóa các lớp trước.',
    'registrations_lop_id_fkey': 'Lớp này đang có học viên đăng ký, không xóa được. Hãy hủy đăng ký trước.',
    'grades_lop_id_fkey': 'Lớp này đã có điểm. Xóa sẽ mất dữ liệu điểm.',
    'curriculum_ma_mon_fkey': 'Môn này đang trong khung chương trình.',
    'students_user_id_fkey': 'Học viên đang có dữ liệu liên quan.',
    'teachers_user_id_fkey': 'Giảng viên đang dạy lớp.',
    'employees_user_id_fkey': 'Nhân viên có ràng buộc dữ liệu.',
}


@app.exception_handler(psycopg2.errors.ForeignKeyViolation)
async def fk_violation_handler(request: Request, exc):
    """Tra ve 409 Conflict voi message ro rang khi co FK violation."""
    detail = str(exc.diag.message_detail or exc.diag.constraint_name or '') if exc.diag else str(exc)
    msg = 'Không thể xóa: dữ liệu này đang được tham chiếu ở bảng khác.'
    # Map ten constraint cu the
    cn = exc.diag.constraint_name if exc.diag else None
    if cn and cn in _FK_MESSAGES:
        msg = _FK_MESSAGES[cn]
    return JSONResponse(status_code=409, content={'detail': msg, 'constraint': cn})


@app.exception_handler(psycopg2.errors.UniqueViolation)
async def unique_violation_handler(request: Request, exc):
    """Tra ve 409 Conflict khi vi pham unique."""
    cn = exc.diag.constraint_name if exc.diag else None
    return JSONResponse(
        status_code=409,
        content={'detail': f'Dữ liệu trùng (đã tồn tại): {cn}', 'constraint': cn},
    )


@app.exception_handler(psycopg2.errors.CheckViolation)
async def check_violation_handler(request: Request, exc):
    cn = exc.diag.constraint_name if exc.diag else None
    return JSONResponse(
        status_code=400,
        content={'detail': f'Dữ liệu không hợp lệ (vi phạm CHECK): {cn}', 'constraint': cn},
    )


@app.exception_handler(psycopg2.IntegrityError)
async def integrity_error_handler(request: Request, exc):
    """Catch-all cho cac IntegrityError khac chua co handler rieng."""
    return JSONResponse(status_code=409, content={'detail': f'Lỗi ràng buộc dữ liệu: {exc}'})


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
