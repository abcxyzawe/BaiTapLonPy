"""Users router: Students, Teachers, Employees, Reviews."""
from fastapi import APIRouter, HTTPException

from backend.api.schemas import (EmployeeCreate, EmployeeUpdate, ReviewSubmit,
                                  StudentCreate, StudentUpdate, TeacherCreate, TeacherUpdate)
from backend.services.user_service import (EmployeeService, ReviewService,
                                            StudentService, TeacherService)

router = APIRouter()


# ===== Students =====
@router.get('/students')
def list_students():
    return StudentService.get_all()


@router.get('/students/{msv}')
def get_student(msv: str):
    return StudentService.get_by_msv(msv)


@router.post('/students')
def create_student(req: StudentCreate):
    uid = StudentService.create(
        req.username, req.password, req.full_name, req.msv,
        email=req.email, sdt=req.sdt, ngaysinh=req.ngaysinh,
        gioitinh=req.gioitinh, diachi=req.diachi
    )
    return {'user_id': uid}


@router.put('/students/{user_id}')
def update_student(user_id: int, req: StudentUpdate):
    fields = req.model_dump(exclude_none=True)
    affected = StudentService.update(user_id, **fields)
    if not affected:
        raise HTTPException(status_code=404, detail=f'Học viên user_id={user_id} không tồn tại')
    return {'status': 'ok'}


@router.delete('/students/{user_id}')
def delete_student(user_id: int):
    affected = StudentService.delete(user_id)
    if not affected:
        raise HTTPException(status_code=404, detail=f'Học viên user_id={user_id} không tồn tại')
    return {'status': 'deactivated'}


# ===== Teachers =====
@router.get('/teachers')
def list_teachers():
    return TeacherService.get_all()


@router.get('/teachers/for-review')
def teachers_for_review():
    return TeacherService.get_for_review()


@router.get('/teachers/by-code/{ma_gv}')
def get_teacher_by_code(ma_gv: str):
    """Lookup teacher info by ma_gv code (vd 'GV001')."""
    row = TeacherService.get_by_code(ma_gv)
    if not row:
        raise HTTPException(status_code=404, detail=f'Teacher {ma_gv} not found')
    return row


@router.post('/teachers')
def create_teacher(req: TeacherCreate):
    uid = TeacherService.create(
        req.username, req.password, req.full_name, req.ma_gv,
        email=req.email, sdt=req.sdt, hoc_vi=req.hoc_vi,
        khoa=req.khoa, chuyen_nganh=req.chuyen_nganh, tham_nien=req.tham_nien
    )
    return {'user_id': uid}


@router.put('/teachers/{user_id}')
def update_teacher(user_id: int, req: TeacherUpdate):
    fields = req.model_dump(exclude_none=True)
    affected = TeacherService.update(user_id, **fields)
    if not affected:
        raise HTTPException(status_code=404, detail=f'Giảng viên user_id={user_id} không tồn tại')
    return {'status': 'ok'}


@router.delete('/teachers/{user_id}')
def delete_teacher(user_id: int):
    affected = TeacherService.delete(user_id)
    if not affected:
        raise HTTPException(status_code=404, detail=f'Giảng viên user_id={user_id} không tồn tại')
    return {'status': 'deactivated'}


# ===== Employees =====
@router.get('/employees')
def list_employees():
    return EmployeeService.get_all()


@router.get('/employees/by-code/{ma_nv}')
def get_employee_by_code(ma_nv: str):
    """Lookup employee info by ma_nv code."""
    row = EmployeeService.get_by_code(ma_nv)
    if not row:
        raise HTTPException(status_code=404, detail=f'Employee {ma_nv} not found')
    return row


@router.post('/employees')
def create_employee(req: EmployeeCreate):
    uid = EmployeeService.create(
        req.username, req.password, req.full_name, req.ma_nv,
        email=req.email, sdt=req.sdt, chuc_vu=req.chuc_vu,
        phong_ban=req.phong_ban, ngay_vao_lam=req.ngay_vao_lam
    )
    return {'user_id': uid}


@router.put('/employees/{user_id}')
def update_employee(user_id: int, req: EmployeeUpdate):
    fields = req.model_dump(exclude_none=True)
    affected = EmployeeService.update(user_id, **fields)
    if not affected:
        raise HTTPException(status_code=404, detail=f'Nhân viên user_id={user_id} không tồn tại')
    return {'status': 'ok'}


@router.delete('/employees/{user_id}')
def delete_employee(user_id: int):
    affected = EmployeeService.delete(user_id)
    if not affected:
        raise HTTPException(status_code=404, detail=f'Nhân viên user_id={user_id} không tồn tại')
    return {'status': 'deactivated'}


# ===== Reviews =====
@router.post('/reviews')
def submit_review(req: ReviewSubmit):
    ReviewService.submit_review(req.hv_id, req.gv_id, req.lop_id, req.diem,
                                 nhan_xet=req.nhan_xet)
    return {'status': 'submitted'}
