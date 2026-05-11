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
from fastapi import APIRouter, HTTPException, File, UploadFile
import shutil
import os
import uuid

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
        han_nop=req.han_nop, diem_toi_da=req.diem_toi_da,
        file_url=req.file_url
    )
    return {'id': asg_id, 'status': 'created'}


@router.post('/upload')
def upload_assignment_file(file: UploadFile = File(...)):
    """Upload file dinh kem bai tap, tra ve URL de luu vao DB."""
    try:
        upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        ext = os.path.splitext(file.filename)[1]
        new_name = f"asg_{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(upload_dir, new_name)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"file_url": f"/uploads/{new_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")


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
