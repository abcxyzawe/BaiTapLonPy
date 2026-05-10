"""Assignments + submissions router.

Endpoints:
  GV side:
    POST   /assignments              tao bai tap moi
    PUT    /assignments/{id}         sua bai tap
    DELETE /assignments/{id}         xoa bai tap
    GET    /assignments/{id}         chi tiet bai tap
    GET    /assignments/teacher/{gv_id}    list bai GV da giao
    GET    /assignments/{id}/submissions   ds bai HV nop cho bai nay
    POST   /submissions/{id}/grade   GV cham + gop y

  HV side:
    GET    /assignments/class/{ma_lop}    list bai cua lop
    GET    /assignments/{id}/submission/{hv_id}  bai HV da nop (neu co)
    POST   /submissions              HV nop bai
    GET    /submissions/student/{hv_id}   lich su nop bai
    GET    /assignments/student/{hv_id}/pending  bai can lam
"""
import os
import re
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse

from backend.api.schemas import (
    AssignmentCreate, AssignmentUpdate,
    SubmissionCreate, SubmissionGrade,
)
from backend.services.assignment_service import AssignmentService

router = APIRouter()

# Folder luu file dinh kem assignments - relative tu repo root
# (backend/uploads/assignments/). Tao luc startup neu chua co.
_UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / 'uploads' / 'assignments'
_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
# Whitelist extension theo yeu cau (anh + tai lieu)
_ALLOWED_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.pdf',
                '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                '.txt', '.zip', '.rar'}
_MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB


def _safe_filename(name: str) -> str:
    """Bo ky tu nguy hiem, giu only alphanumeric + dot/dash/underscore."""
    base = os.path.basename(name or 'file')
    base = re.sub(r'[^\w.\-]+', '_', base, flags=re.UNICODE)
    return base[:120] or 'file'


# ============ ASSIGNMENT CRUD ============

@router.post('')
def create_assignment(req: AssignmentCreate):
    asg_id = AssignmentService.create(
        lop_id=req.lop_id, gv_id=req.gv_id,
        tieu_de=req.tieu_de, mo_ta=req.mo_ta or '',
        file_path=req.file_path,
        han_nop=req.han_nop, diem_toi_da=req.diem_toi_da
    )
    return {'id': asg_id, 'status': 'created'}


@router.post('/upload-file')
async def upload_assignment_file(file: UploadFile = File(...)):
    """GV upload file dinh kem TRUOC khi tao bai tap. Tra ve file_path tuong doi
    de FE truyen vao POST /assignments. Tach 2 buoc cho phep retry tao bai tap
    ma khong phai upload lai file."""
    fname = _safe_filename(file.filename or 'file')
    ext = os.path.splitext(fname)[1].lower()
    if ext and ext not in _ALLOWED_EXT:
        raise HTTPException(status_code=400,
                            detail=f'Loai file khong duoc phep: {ext}. '
                                   f'Cho phep: {", ".join(sorted(_ALLOWED_EXT))}')
    # Prefix timestamp tranh ghi de + de sort theo thoi gian
    saved_name = f'{int(time.time() * 1000)}_{fname}'
    dest = _UPLOAD_DIR / saved_name
    size = 0
    try:
        with open(dest, 'wb') as f:
            while chunk := await file.read(1024 * 64):
                size += len(chunk)
                if size > _MAX_FILE_BYTES:
                    f.close()
                    dest.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f'File qua lon (>{_MAX_FILE_BYTES // (1024 * 1024)} MB)'
                    )
                f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f'Khong luu duoc file: {e}')
    # Relative path de luu DB (frontend dung GET /assignments/file/<path> de download)
    rel_path = f'assignments/{saved_name}'
    return {'file_path': rel_path, 'size': size, 'filename': fname}


@router.get('/file/{file_path:path}')
def download_assignment_file(file_path: str):
    """Tra ve file dinh kem cua bai tap. file_path la relative tu uploads/.
    HV/GV xem chi tiet bai tap goi endpoint nay de tai/mo file."""
    # Chong path traversal - chi cho phep file trong _UPLOAD_DIR's parent (uploads/)
    abs_root = _UPLOAD_DIR.parent.resolve()
    target = (abs_root / file_path).resolve()
    if abs_root not in target.parents and target != abs_root:
        raise HTTPException(status_code=400, detail='file_path invalid')
    if not target.is_file():
        raise HTTPException(status_code=404, detail='File khong ton tai')
    return FileResponse(target, filename=target.name)


@router.put('/{asg_id}')
def update_assignment(asg_id: int, req: AssignmentUpdate):
    affected = AssignmentService.update(asg_id, **req.model_dump(exclude_unset=True))
    if not affected:
        raise HTTPException(status_code=404, detail=f'Bai tap id={asg_id} khong ton tai')
    return {'status': 'ok'}


@router.delete('/{asg_id}')
def delete_assignment(asg_id: int):
    if not AssignmentService.delete(asg_id):
        raise HTTPException(status_code=404, detail=f'Bai tap id={asg_id} khong ton tai')
    return {'status': 'deleted'}


@router.get('/{asg_id}')
def get_assignment(asg_id: int):
    row = AssignmentService.get_by_id(asg_id)
    if not row:
        raise HTTPException(status_code=404, detail=f'Bai tap id={asg_id} khong ton tai')
    return row


# ============ ASSIGNMENT QUERIES ============

@router.get('/teacher/{gv_id}')
def get_assignments_by_teacher(gv_id: int):
    """GV: list bai da giao (tat ca lop), kem so HV nop / cham."""
    return AssignmentService.get_by_teacher(gv_id)


@router.get('/class/{lop_id}')
def get_assignments_by_class(lop_id: str):
    """HV: list bai cua lop (xem trong trang Bai tap)."""
    return AssignmentService.get_by_class(lop_id)


@router.get('/student/{hv_id}/pending')
def get_pending_for_student(hv_id: int):
    """HV: bai can lam (chua nop hoac qua han) - cho banner dashboard."""
    return AssignmentService.get_pending_for_student(hv_id)


@router.get('/{asg_id}/submissions')
def get_submissions(asg_id: int):
    """GV: ds tat ca HV cua lop + status nop bai."""
    return AssignmentService.get_submissions_by_assignment(asg_id)


@router.get('/{asg_id}/submission/{hv_id}')
def get_my_submission(asg_id: int, hv_id: int):
    """HV: xem bai minh da nop (neu co)."""
    return AssignmentService.get_submission(asg_id, hv_id)
