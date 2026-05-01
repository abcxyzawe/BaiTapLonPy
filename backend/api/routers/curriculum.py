"""Curriculum router."""
from typing import Optional

from fastapi import APIRouter

from backend.api.schemas import CurriculumCreate, CurriculumUpdate
from backend.services.curriculum_service import CurriculumService

router = APIRouter()


@router.get('')
def list_all(nganh: Optional[str] = None):
    return CurriculumService.get_all(nganh=nganh)


@router.get('/{cur_id}')
def get(cur_id: int):
    return CurriculumService.get(cur_id)


@router.post('')
def create(req: CurriculumCreate):
    cur_id = CurriculumService.create(
        req.ma_mon, req.tin_chi, req.loai,
        hoc_ky_de_nghi=req.hoc_ky_de_nghi, mon_tien_quyet=req.mon_tien_quyet,
        nganh=req.nganh, ghi_chu=req.ghi_chu
    )
    return {'cur_id': cur_id}


@router.put('/{cur_id}')
def update(cur_id: int, req: CurriculumUpdate):
    fields = req.model_dump(exclude_none=True)
    CurriculumService.update(cur_id, **fields)
    return {'status': 'ok'}


@router.delete('/{cur_id}')
def delete(cur_id: int):
    CurriculumService.delete(cur_id)
    return {'status': 'deleted'}


@router.get('/prerequisites/{ma_mon}')
def prerequisites(ma_mon: str, nganh: str = 'CNTT'):
    return {'ma_mon': ma_mon, 'prerequisites': CurriculumService.get_prerequisites(ma_mon, nganh)}


@router.get('/check/{hv_id}/{ma_mon}')
def check_prereq(hv_id: int, ma_mon: str, nganh: str = 'CNTT'):
    return CurriculumService.check_prerequisites_for_student(hv_id, ma_mon, nganh)


@router.get('/progress/{hv_id}')
def progress(hv_id: int, nganh: str = 'CNTT'):
    return CurriculumService.get_progress_for_student(hv_id, nganh)
