"""Courses + Classes router. Chuyen 17 method CourseService thanh REST."""
from typing import Optional

from fastapi import APIRouter, HTTPException

from backend.api.schemas import ClassCreate, ClassPriceUpdate, ClassUpdate, CourseCreate, CourseUpdate
from backend.services.course_service import CourseService

router = APIRouter()


# ===== Courses =====
@router.get('/courses')
def list_courses():
    return CourseService.get_all_courses()


@router.get('/courses/{ma_mon}')
def get_course(ma_mon: str):
    row = CourseService.get_course(ma_mon)
    if not row:
        raise HTTPException(status_code=404, detail=f'Môn học {ma_mon} không tồn tại')
    return row


@router.post('/courses')
def create_course(req: CourseCreate):
    CourseService.create_course(req.ma_mon, req.ten_mon, req.mo_ta)
    return {'status': 'created'}


@router.put('/courses/{ma_mon}')
def update_course(ma_mon: str, req: CourseUpdate):
    CourseService.update_course(ma_mon, ten_mon=req.ten_mon, mo_ta=req.mo_ta)
    return {'status': 'ok'}


@router.delete('/courses/{ma_mon}')
def delete_course(ma_mon: str):
    affected = CourseService.delete_course(ma_mon)
    if not affected:
        raise HTTPException(status_code=404, detail=f'Môn học {ma_mon} không tồn tại')
    return {'status': 'deleted'}


# ===== Classes =====
@router.get('/classes')
def list_classes():
    return CourseService.get_all_classes()


@router.get('/classes/{ma_lop}')
def get_class(ma_lop: str):
    row = CourseService.get_class(ma_lop)
    if not row:
        raise HTTPException(status_code=404, detail=f'Lớp {ma_lop} không tồn tại')
    return row


@router.get('/classes/teacher/{gv_id}')
def classes_by_teacher(gv_id: int):
    return CourseService.get_classes_by_teacher(gv_id)


@router.get('/classes/student/{hv_id}')
def classes_by_student(hv_id: int):
    return CourseService.get_classes_by_student(hv_id)


@router.get('/classes/{ma_lop}/students')
def students_in_class(ma_lop: str):
    return CourseService.get_students_in_class(ma_lop)


@router.post('/classes')
def create_class(req: ClassCreate):
    CourseService.create_class(
        req.ma_lop, req.ma_mon, gv_id=req.gv_id, lich=req.lich, phong=req.phong,
        siso_max=req.siso_max, gia=req.gia, semester_id=req.semester_id,
        siso_hien_tai=req.siso_hien_tai, so_buoi=req.so_buoi
    )
    return {'status': 'created'}


@router.put('/classes/{ma_lop}')
def update_class(ma_lop: str, req: ClassUpdate):
    fields = req.model_dump(exclude_none=True)
    CourseService.update_class(ma_lop, **fields)
    return {'status': 'ok'}


@router.delete('/classes/{ma_lop}')
def delete_class(ma_lop: str):
    affected = CourseService.delete_class(ma_lop)
    if not affected:
        raise HTTPException(status_code=404, detail=f'Lớp {ma_lop} không tồn tại')
    return {'status': 'deleted'}


@router.patch('/classes/{ma_lop}/price')
def update_class_price(ma_lop: str, req: ClassPriceUpdate):
    CourseService.update_class_price(ma_lop, req.gia)
    return {'status': 'ok'}


# ===== Teachers helper =====
@router.get('/teachers/list')
def get_teachers_list():
    """DS GV cho dropdown admin (id + ten + ma_gv)."""
    return CourseService.get_teachers_list()


@router.get('/teachers/{gv_id}/students')
def students_by_teacher(gv_id: int, lop: Optional[str] = None):
    return CourseService.get_students_by_teacher(gv_id, lop_filter=lop)
