"""Class videos router - GV upload link YouTube/Drive/Vimeo, HV xem lai bai giang.

Endpoints:
  POST   /videos                 GV them video moi
  PUT    /videos/{id}            GV sua thong tin video
  DELETE /videos/{id}            GV xoa video
  GET    /videos/{id}            chi tiet 1 video
  GET    /videos/class/{lop_id}  list video cua 1 lop
  GET    /videos/teacher/{gv_id} list video GV da upload (tat ca lop)
  GET    /videos/student/{hv_id} list video cac lop HV dang ky (optional ?lop_id=)
"""
from fastapi import APIRouter, HTTPException

from backend.api.schemas import ClassVideoCreate, ClassVideoUpdate
from backend.services.video_service import ClassVideoService

router = APIRouter()


@router.post('')
def create_video(req: ClassVideoCreate):
    """GV them video moi. Validate URL bat dau bang http(s)."""
    if not (req.video_url.startswith('http://') or req.video_url.startswith('https://')):
        raise HTTPException(status_code=400,
                            detail='video_url phai bat dau bang http:// hoac https://')
    vid = ClassVideoService.create(
        lop_id=req.lop_id, gv_id=req.gv_id,
        tieu_de=req.tieu_de, video_url=req.video_url,
        mo_ta=req.mo_ta, buoi_so=req.buoi_so,
    )
    return {'id': vid, 'status': 'created'}


@router.put('/{video_id}')
def update_video(video_id: int, req: ClassVideoUpdate):
    fields = req.model_dump(exclude_unset=True)
    if 'video_url' in fields and fields['video_url']:
        if not (fields['video_url'].startswith('http://') or
                fields['video_url'].startswith('https://')):
            raise HTTPException(status_code=400,
                                detail='video_url phai bat dau bang http:// hoac https://')
    affected = ClassVideoService.update(video_id, **fields)
    if not affected:
        raise HTTPException(status_code=404, detail=f'Video id={video_id} khong ton tai')
    return {'status': 'ok'}


@router.delete('/{video_id}')
def delete_video(video_id: int):
    if not ClassVideoService.delete(video_id):
        raise HTTPException(status_code=404, detail=f'Video id={video_id} khong ton tai')
    return {'status': 'deleted'}


@router.get('/{video_id}')
def get_video(video_id: int):
    row = ClassVideoService.get_by_id(video_id)
    if not row:
        raise HTTPException(status_code=404, detail=f'Video id={video_id} khong ton tai')
    return row


@router.get('/class/{lop_id}')
def get_by_class(lop_id: str):
    """HV/GV: list video cua 1 lop."""
    return ClassVideoService.get_by_class(lop_id)


@router.get('/teacher/{gv_id}')
def get_by_teacher(gv_id: int):
    """GV: tat ca video minh da upload."""
    return ClassVideoService.get_by_teacher(gv_id)


@router.get('/student/{hv_id}')
def get_for_student(hv_id: int, lop_id: str = None):
    """HV: list video cac lop minh dang ky. Optional filter theo 1 lop."""
    return ClassVideoService.get_for_student(hv_id, lop_id)
