# EAUT - He thong Dang ky khoa hoc

## Thanh vien
- Do Quoc Anh (cacbuoi / pipipipipia23) - Team lead, Frontend, run.exe
- Dao Viet Quang Huy (Quanghuy-1611) - Backend services, integration
- Tran Trung Duc (ducfaklt2005) - Backend services, attendance

## Mo ta
Ung dung quan ly dang ky khoa hoc cho trung tam EAUT. Ho tro 4 vai tro:
**Hoc vien, Giang vien, Nhan vien, Quan tri vien** - moi role co dashboard rieng.

Tinh nang chinh:
- Dang nhap + phan quyen 4 role
- HV: dang ky lop, xem lich, xem diem, danh gia GV, xem tien do CT
- GV: lich day, danh sach HV, gui thong bao, **diem danh tung buoi**, nhap diem
- NV: dang ky cho HV, ghi nhan thanh toan, quan ly lop
- Admin: full CRUD course/class/student/teacher/employee/semester/curriculum, thong ke

## Kien truc 3-tier client-server

```
PyQt5 frontend  --HTTP/JSON-->  FastAPI server  --psycopg2-->  PostgreSQL
(local app)                    (uvicorn :8000)                 (Docker container)
```

## Cong nghe

| Layer | Stack |
|-------|-------|
| Frontend | **PyQt5 5.15** + Qt Designer (.ui files) + requests |
| API Gateway | **FastAPI 0.115** + Pydantic 2 + uvicorn |
| Service Layer | Python 3.13 + psycopg2-binary |
| Database | **PostgreSQL 16** (Docker) - 18 tables, 5 views |
| Build/Deploy | Docker Compose, PyInstaller (1-click .exe) |

## Cau truc thu muc

```
BaiTapLonPy/
├── backend/
│   ├── api/                    # FastAPI REST server (97 endpoints)
│   │   ├── main.py             # App entry
│   │   ├── schemas.py          # Pydantic models
│   │   └── routers/            # 13 router files
│   ├── services/               # Business logic (16 service classes)
│   ├── database/
│   │   ├── db.py               # Singleton psycopg2 connection
│   │   ├── schema.sql          # DDL
│   │   └── seed.sql            # Mock data
│   └── models/                 # Domain entities (Entity ABC + 13 concrete)
├── frontend/
│   ├── main.py                 # PyQt5 app (4 Window + dialogs)
│   ├── api_client.py           # HTTP client wrapper (replaces direct service import)
│   ├── theme_helper.py         # Theme + styling
│   ├── ui/                     # 27 .ui files (Qt Designer)
│   ├── styles/                 # QSS theme
│   └── resources/icons/        # Icons
├── docs/
│   ├── architecture.md         # Kien truc 3-tier + diagram
│   ├── mo-ta-he-thong.md       # Mo ta nghiep vu
│   ├── mo-ta-chuc-nang.md      # Functional spec
│   └── mockups/                # UI mockups
├── docker-compose.yml          # PostgreSQL container config
├── requirements.txt
├── run.py                      # Launcher: docker + uvicorn + PyQt5
├── run.spec                    # PyInstaller config
├── build_exe.bat               # Build run.exe
├── HUONG_DAN_RUN_EXE.md        # User guide
└── README.md
```

## Chay app

### Cach 1: Dung run.exe (recommended - 1 click)

1. Cai [Docker Desktop](https://www.docker.com/products/docker-desktop) + bat no
2. Build exe (chi can lam 1 lan):
   ```cmd
   build_exe.bat
   ```
3. Double-click `dist/run.exe` → tu dong start Postgres + API + UI

Xem chi tiet trong [HUONG_DAN_RUN_EXE.md](HUONG_DAN_RUN_EXE.md).

### Cach 2: Chay tay (cho dev)

```bash
# 1. Cai dependencies
pip install -r requirements.txt

# 2. Start PostgreSQL
docker compose up -d postgres

# 3. Start REST API server (terminal 1)
uvicorn backend.api.main:app --reload --port 8000

# 4. Start frontend (terminal 2)
python frontend/main.py
```

API docs (Swagger UI auto-generated): http://localhost:8000/docs

## Tai khoan test

| Vai tro | Username | Password |
|---------|----------|----------|
| Hoc vien | `student` | `passuser` |
| Giang vien | `teacher` | `passtea` |
| Nhan vien | `employee` | `passemp` |
| Quan tri vien | `admin` | `passadmin` |

## API Endpoints (97 routes)

| Resource | Endpoints | Methods |
|----------|-----------|---------|
| `/auth/*` | login, password | POST, PUT |
| `/courses/*` `/classes/*` | CRUD courses + classes | GET, POST, PUT, DELETE, PATCH |
| `/registrations/*` | DK + thanh toan | GET, POST, DELETE |
| `/grades/*` | Bang diem + GPA | GET, POST |
| `/notifications/*` | Gui + xem thong bao | GET, POST, DELETE |
| `/students` `/teachers` `/employees` `/reviews` | User CRUD | GET, POST, PUT, DELETE |
| `/stats/*` | 9 endpoint dashboard | GET |
| `/semesters/*` | Quan ly hoc ky | GET, POST, PATCH, DELETE |
| `/curriculum/*` | Khung CT + tien do | GET, POST, PUT, DELETE |
| `/schedules/*` | Lich hoc theo tuan | GET, POST |
| `/exams/*` | Lich thi | GET, POST |
| `/attendance/*` | Diem danh + ti le | GET, POST |
| `/audit/*` | Nhat ky he thong | GET, POST, DELETE |

Full Swagger UI: `GET /docs` khi server dang chay.

## Repo

https://github.com/abcxyzawe/BaiTapLonPy
