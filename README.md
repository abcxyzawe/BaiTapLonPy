# He thong Dang ky Khoa hoc - EAUT

Bai tap lon mon Python. App quan ly trung tam dao tao - 4 vai tro:
hoc vien, giang vien, nhan vien, quan tri vien.

## Stack
- Frontend: PyQt5
- Backend: FastAPI (REST API)
- DB: PostgreSQL chay trong Docker

## Cai dat

```bash
pip install -r requirements.txt
docker compose up -d postgres
```

## Chay app

Mo 2 terminal:

Terminal 1 (API server):
```bash
uvicorn backend.api.main:app --reload --port 8000
```

Terminal 2 (UI):
```bash
python frontend/main.py
```

Hoac dung 1 file build san:
```bash
build_exe.bat
dist\run.exe
```

## Tai khoan test

| Role | User | Pass |
|------|------|------|
| Hoc vien | student | passuser |
| Giang vien | teacher | passtea |
| Nhan vien | employee | passemp |
| Admin | admin | passadmin |

## Doc

- API docs: http://localhost:8000/docs (sau khi chay uvicorn)
- Mo ta chuc nang: `docs/mo-ta-chuc-nang.md`
- Mo ta he thong: `docs/mo-ta-he-thong.md`
- Mockups: `docs/mockups/`

## Thanh vien
- Do Quoc Anh
- Dao Viet Quang Huy
- Tran Trung Duc
