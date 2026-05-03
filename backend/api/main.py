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
# Ho tro ca DELETE (parent bi tham chieu) va INSERT/UPDATE (child tham chieu parent khong ton tai)
# Format: 'constraint_name': {'on_delete': '...', 'on_insert': '...'}
_FK_MESSAGES = {
    'classes_ma_mon_fkey': {
        'on_delete': 'Môn học này đang có lớp tham chiếu, không xóa được. Hãy xóa các lớp trước.',
        'on_insert': 'Mã môn không tồn tại trong hệ thống. Hãy thêm môn học trước.',
    },
    'registrations_lop_id_fkey': {
        'on_delete': 'Lớp này đang có học viên đăng ký, không xóa được. Hãy hủy đăng ký trước.',
        'on_insert': 'Lớp không tồn tại trong hệ thống.',
    },
    'grades_lop_id_fkey': {
        'on_delete': 'Lớp này đã có điểm. Xóa sẽ mất dữ liệu điểm.',
        'on_insert': 'Lớp không tồn tại trong hệ thống.',
    },
    'curriculum_ma_mon_fkey': {
        'on_delete': 'Môn này đang trong khung chương trình.',
        'on_insert': 'Mã môn không tồn tại trong hệ thống. Hãy thêm môn học trước khi đưa vào khung CT.',
    },
    'students_user_id_fkey': {
        'on_delete': 'Học viên đang có dữ liệu liên quan.',
        'on_insert': 'User_id không tồn tại.',
    },
    'teachers_user_id_fkey': {
        'on_delete': 'Giảng viên đang dạy lớp.',
        'on_insert': 'User_id không tồn tại.',
    },
    'employees_user_id_fkey': {
        'on_delete': 'Nhân viên có ràng buộc dữ liệu.',
        'on_insert': 'User_id không tồn tại.',
    },
    'classes_gv_id_fkey': {
        'on_delete': 'Giảng viên này đang dạy lớp.',
        'on_insert': 'Giảng viên không tồn tại trong hệ thống.',
    },
    'classes_semester_id_fkey': {
        'on_delete': 'Học kỳ này có lớp tham chiếu.',
        'on_insert': 'Học kỳ không tồn tại.',
    },
    'registrations_hv_id_fkey': {
        'on_insert': 'Học viên không tồn tại trong hệ thống.',
    },
    'registrations_nv_dk_fkey': {
        'on_insert': 'Nhân viên đăng ký không tồn tại.',
    },
    'reviews_hv_id_fkey': {
        'on_insert': 'Học viên không tồn tại.',
    },
    'reviews_gv_id_fkey': {
        'on_insert': 'Giảng viên không tồn tại.',
    },
    'reviews_lop_id_fkey': {
        'on_insert': 'Lớp không tồn tại.',
    },
}


@app.exception_handler(psycopg2.errors.ForeignKeyViolation)
async def fk_violation_handler(request: Request, exc):
    """Tra ve 409 Conflict voi message ro rang khi co FK violation."""
    cn = exc.diag.constraint_name if exc.diag else None
    # Detect huong: DELETE (parent has children) vs INSERT/UPDATE (child references missing parent)
    # psycopg2 diag.message_primary chua thong tin: "update or delete on table X violates..." hoac "insert or update on table Y violates..."
    msg_primary = ''
    try:
        if exc.diag:
            msg_primary = (exc.diag.message_primary or '').lower()
    except Exception:
        pass
    is_delete_direction = 'update or delete' in msg_primary

    msg = 'Không thể thực hiện: ràng buộc khóa ngoại bị vi phạm.'
    if cn and cn in _FK_MESSAGES:
        entry = _FK_MESSAGES[cn]
        key = 'on_delete' if is_delete_direction else 'on_insert'
        msg = entry.get(key) or entry.get('on_delete') or entry.get('on_insert') or msg
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
