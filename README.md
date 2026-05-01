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

App tach 2 phan: backend (DB + REST API) va frontend (PyQt5 UI).
Backend chay nen, frontend goi vao API qua HTTP.

### Cach 1 - dung script san (Windows)

Mo 2 cua so cmd, chay tung script:

```cmd
start_backend.bat    : DB + API tai http://localhost:8000
start_frontend.bat   : UI PyQt5
```

### Cach 2 - go lenh tay

Terminal 1 (database):
```bash
docker compose up -d postgres
```

Terminal 2 (API server):
```bash
python -m uvicorn backend.api.main:app --port 8000 --reload
```

Terminal 3 (UI):
```bash
python frontend/main.py
```

### Cach 3 - 1-click build san

```bash
build_exe.bat
dist\run.exe         # bundle ca backend + frontend trong 1 process
```

> Cach 1/2 tach process backend rieng (chuan deploy production hon).
> Cach 3 bundle cho user cuoi - khi click .exe se tu spawn API thread.

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
