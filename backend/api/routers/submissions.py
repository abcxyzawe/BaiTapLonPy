"""Submissions router (HV nop bai + GV cham)."""
from fastapi import APIRouter, HTTPException

from backend.api.schemas import SubmissionCreate, SubmissionGrade
from backend.services.assignment_service import AssignmentService

router = APIRouter()


@router.post('')
def submit(req: SubmissionCreate):
    """HV nop bai (insert hoac re-submit -> reset diem cu)."""
    try:
        sub_id = AssignmentService.submit(
            req.assignment_id, req.hv_id,
            req.noi_dung or '', req.file_url
        )
    except Exception as e:
        # Catch FK constraint (assignment khong ton tai, HV khong dang ky lop, ...)
        msg = str(e).lower()
        if 'foreign key' in msg or 'fk' in msg or 'violates' in msg:
            raise HTTPException(status_code=400,
                detail='Bai tap khong ton tai hoac ban chua dang ky lop nay')
        raise HTTPException(status_code=500, detail=str(e))
    return {'id': sub_id, 'status': 'submitted'}


@router.post('/{sub_id}/grade')
def grade(sub_id: int, req: SubmissionGrade):
    """GV cham diem + nhan xet cho 1 bai nop."""
    AssignmentService.grade(sub_id, req.diem, req.nhan_xet or '')
    return {'status': 'graded'}


@router.get('/student/{hv_id}')
def get_history(hv_id: int):
    """HV: lich su bai da nop + feedback GV."""
    return AssignmentService.get_submissions_by_student(hv_id)
