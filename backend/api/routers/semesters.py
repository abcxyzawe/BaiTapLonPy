"""Semesters router."""
from fastapi import APIRouter, HTTPException

from backend.api.schemas import SemesterCreate, SemesterStatusUpdate
from backend.services.semester_service import SemesterService

router = APIRouter()


@router.get('')
def list_all():
    return SemesterService.get_all()


@router.get('/current')
def current():
    return SemesterService.get_current()


@router.get('/{sem_id}')
def get(sem_id: str):
    row = SemesterService.get(sem_id)
    if not row:
        raise HTTPException(status_code=404, detail=f'Học kỳ {sem_id} không tồn tại')
    return row


@router.post('')
def create(req: SemesterCreate):
    SemesterService.create(req.sem_id, req.ten, req.nam_hoc, req.bat_dau,
                           req.ket_thuc, trang_thai=req.trang_thai)
    return {'status': 'created'}


@router.patch('/{sem_id}/status')
def set_status(sem_id: str, req: SemesterStatusUpdate):
    affected = SemesterService.set_status(sem_id, req.trang_thai)
    if not affected:
        raise HTTPException(status_code=404, detail=f'Học kỳ {sem_id} không tồn tại')
    return {'status': 'ok'}


@router.delete('/{sem_id}')
def delete(sem_id: str):
    affected = SemesterService.delete(sem_id)
    if not affected:
        raise HTTPException(status_code=404, detail=f'Học kỳ {sem_id} không tồn tại')
    return {'status': 'deleted'}
