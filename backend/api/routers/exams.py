"""Exams router."""
from typing import Optional

from fastapi import APIRouter, HTTPException

from backend.api.schemas import ExamCreate
from backend.services.exam_service import ExamService

router = APIRouter()


@router.get('')
def list_all(semester_id: Optional[str] = None):
    return ExamService.get_all(semester_id=semester_id)


@router.get('/student/{hv_id}')
def for_student(hv_id: int, semester_id: Optional[str] = None):
    return ExamService.get_for_student(hv_id, semester_id=semester_id)


@router.get('/teacher/{gv_id}')
def for_teacher(gv_id: int):
    return ExamService.get_for_teacher(gv_id)


@router.get('/class/{lop_id}')
def for_class(lop_id: str):
    return ExamService.get_for_class(lop_id)


@router.post('')
def create(req: ExamCreate):
    exam_id = ExamService.create(
        req.lop_id, req.ngay_thi, req.ca_thi, phong=req.phong,
        hinh_thuc=req.hinh_thuc, semester_id=req.semester_id,
        gio_bat_dau=req.gio_bat_dau, gio_ket_thuc=req.gio_ket_thuc,
        so_cau=req.so_cau, thoi_gian_phut=req.thoi_gian_phut
    )
    return {'id': exam_id, 'status': 'created'}


@router.delete('/{exam_id}')
def delete_exam(exam_id: int):
    if not ExamService.delete(exam_id):
        raise HTTPException(status_code=404, detail=f'Lich thi id={exam_id} khong ton tai')
    return {'status': 'deleted'}
