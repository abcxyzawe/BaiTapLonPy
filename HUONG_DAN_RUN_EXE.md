# Hướng dẫn chạy app bằng `run.exe`

## Yêu cầu trên máy người dùng

1. **Docker Desktop** đã cài + đang chạy ([tải tại đây](https://www.docker.com/products/docker-desktop))
2. Đã `git clone` toàn bộ repo (vì `docker-compose.yml` cần mount `backend/database/*.sql`)
3. **Không cần cài Python**, không cần cài PyQt5, psycopg2 — đã bundle sẵn trong exe

## Cách dùng

### Lần đầu

1. Mở **Docker Desktop**, đợi nó báo "Docker is running" (~30s sau khi mở máy)
2. Vào folder repo, double-click `dist/run.exe`
3. Splash screen hiện "Đang khởi động hệ thống EAUT..."
4. Tự động: kiểm tra Docker → start container `eaut_postgres` → đợi DB ready → mở cửa sổ login
5. Login bằng 1 trong 4 tài khoản test:

| Vai trò | Username | Password |
|---------|----------|----------|
| Học viên | `student` | `passuser` |
| Admin | `admin` | `passadmin` |
| Giảng viên | `teacher` | `passtea` |
| Nhân viên | `employee` | `passemp` |

### Lần sau

Chỉ cần double-click `run.exe` — container PostgreSQL chạy nền sẵn từ lần trước, không cần init lại.

### Tắt app

- Đóng cửa sổ → app tắt
- Container Docker vẫn chạy nền (data được giữ lại). Muốn dừng hẳn:
  ```bash
  docker compose down
  ```

## Các lỗi thường gặp

| Lỗi popup | Nguyên nhân | Cách fix |
|-----------|-------------|----------|
| **"Thiếu Docker"** | Chưa cài Docker | Cài Docker Desktop |
| **"Docker chưa chạy"** | Docker Desktop chưa khởi động xong | Mở Docker Desktop, đợi 30s |
| **"Database không phản hồi"** | Container start chậm hoặc lỗi config | Xem `docker logs eaut_postgres` |
| **"FileNotFoundError"** | Bundle thiếu file (lỗi build) | Build lại bằng `build_exe.bat` |

## Build lại exe (cho dev)

```bash
# Yêu cầu: Python 3.10+, PyInstaller
pip install -r requirements.txt
pip install pyinstaller

# Build (mất 2-5 phút)
build_exe.bat
# hoặc:
pyinstaller --clean --noconfirm run.spec

# Output: dist/run.exe (~66 MB)
```

## Cấu trúc file build

```
dist/
└── run.exe       ← double-click cái này

build/            ← PyInstaller intermediate (có thể xóa)
*.spec            ← PyInstaller config
run.py            ← Source launcher
```

## Bên trong exe có gì

PyInstaller bundle vào exe:
- `frontend/main.py` + `theme_helper.py` (source code)
- `frontend/ui/*.ui` (PyQt5 UI files - 27 files)
- `frontend/resources/` (icons, screenshots)
- `frontend/styles/` (QSS theme)
- `backend/services/*.py` (13 services)
- `backend/database/db.py` + `schema.sql` + `seed.sql`
- `docker-compose.yml`
- Python 3.13 runtime + PyQt5 5.15 + psycopg2-binary

→ User không cần cài bất cứ thứ gì khác ngoài Docker Desktop.
