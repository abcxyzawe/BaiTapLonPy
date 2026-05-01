"""Semesters router."""
from fastapi import APIRouter

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
    return SemesterService.get(sem_id)


@router.post('')
def create(req: SemesterCreate):
    SemesterService.create(req.sem_id, req.ten, req.nam_hoc, req.bat_dau,
                           req.ket_thuc, trang_thai=req.trang_thai)
    return {'status': 'created'}


@router.patch('/{sem_id}/status')
def set_status(sem_id: str, req: SemesterStatusUpdate):
    SemesterService.set_status(sem_id, req.trang_thai)
    return {'status': 'ok'}


@router.delete('/{sem_id}')
def delete(sem_id: str):
    SemesterService.delete(sem_id)
    return {'status': 'deleted'}
