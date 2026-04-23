# Bản mô tả hệ thống — Quản lý trung tâm đào tạo ngoại khóa EAUT

> Tài liệu mô tả tổng thể cho bài tập lớn môn Python.
> Cập nhật cuối: tháng 4/2026.

---

## 1. Thông tin chung

| Mục | Nội dung |
|---|---|
| **Đề tài** | Xây dựng ứng dụng quản lý trung tâm đào tạo ngoại khóa |
| **Trường** | Đại học Công nghệ Đông Á (EAUT) |
| **Hình thức** | Bài tập lớn nhóm, môn Python |
| **Repository** | github.com/abcxyzawe/BaiTapLonPy |
| **Ngôn ngữ chính** | Python 3.13 |
| **GUI** | PyQt5 5.15.10 (QStackedWidget pattern, 28 file .ui) |
| **CSDL** | PostgreSQL 16 (Alpine), psycopg2-binary |
| **Đóng gói** | Docker Compose (postgres + pgAdmin) |
| **Kích thước** | ~3800 dòng frontend + 700 dòng services + 500 dòng models + 550 dòng SQL |

---

## 2. Mục tiêu & phạm vi

### 2.1. Mục tiêu chính
- Quản lý toàn bộ nghiệp vụ của một trung tâm đào tạo ngoại khóa nhỏ: đăng ký lớp, thu học phí, nhập/xem điểm, điểm danh, đánh giá giảng viên.
- Giao diện native desktop cho 4 vai trò với quyền hạn riêng biệt.
- Có thể chạy được trong 2 chế độ: với DB thật (PostgreSQL qua Docker) hoặc fallback MOCK data (không cần Docker).

### 2.2. Phạm vi
Trung tâm nhỏ/vừa (~100 học viên), không tích hợp cổng thanh toán online — thanh toán được nhân viên thu tại quầy. Không phải là hệ thống quản lý trường đại học lớn (chưa có bằng cấp, quản lý ngành, phòng khoa phức tạp).

---

## 3. Vai trò & quyền hạn

| Vai trò | Tài khoản demo | Chức năng chính |
|---|---|---|
| **Học viên** (Student) | `user` / `passuser` | Xem lịch học, lịch thi, bảng điểm, đánh giá giảng viên, nhận thông báo |
| **Giảng viên** (Teacher) | `teacher` / `passtea` | Xem lịch dạy, danh sách học viên, nhập điểm, gửi thông báo đến lớp |
| **Nhân viên** (Employee) | `employee` / `passemp` | Đăng ký lớp cho HV, thu học phí, in biên lai, quản lý danh sách đăng ký |
| **Quản trị viên** (Admin) | `admin` / `passadmin` | CRUD môn học / lớp / học viên / giảng viên / nhân viên / học kỳ / khung CT, xem nhật ký + thống kê |

Các mật khẩu lưu ở bảng `users.password` dạng plain text (cho demo dễ test) + hỗ trợ đổi mật khẩu qua SHA-256 hash.

---

## 4. Kiến trúc hệ thống

Phân tầng 3 lớp rõ ràng:

```
┌─────────────────────────────────────────────────────────────┐
│ PRESENTATION LAYER  (PyQt5)                                  │
│ App → LoginWindow → MainWindow / AdminWindow /               │
│                     TeacherWindow / EmployeeWindow           │
│ Mỗi Window quản lý nhiều page qua QStackedWidget             │
└──────────────────────────┬──────────────────────────────────┘
                           │ gọi service
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ SERVICE LAYER  (Business Logic)                              │
│ AuthService · CourseService · RegistrationService            │
│ GradeService · NotificationService · StudentService          │
│ TeacherService · EmployeeService · ReviewService             │
│ StatsService                                                  │
└──────────────────────────┬──────────────────────────────────┘
                           │ gọi db
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ DATA ACCESS LAYER                                            │
│ Database (Singleton) → psycopg2 → PostgreSQL 16              │
│ 19 domain model class (Entity abstract + User abstract)      │
└─────────────────────────────────────────────────────────────┘
```

Cờ `DB_AVAILABLE` kiểm tra kết nối lúc khởi động. Nếu có Docker → dùng service thật. Nếu không → fallback MOCK.

---

## 5. Danh sách chức năng chi tiết

### 5.1. Học viên (7 trang)

| Trang | Chức năng |
|---|---|
| **Trang chủ** | 3 stat card (số lớp đăng ký, GPA, học phí còn nợ) |
| **Lịch học** | Calendar tuần hiển thị lịch học từ bảng `schedules` |
| **Lịch thi** | Bảng lịch thi cuối kỳ, lọc theo học kỳ |
| **Xem điểm** | Bảng điểm tất cả lớp đã học, GPA tích lũy, xuất PDF (đang phát triển) |
| **Đánh giá giảng viên** | Search + lọc, chấm 1-5 sao kèm nhận xét, ghi vào bảng `reviews` |
| **Thông báo** | Scroll list thông báo (chung + theo lớp đang học) |
| **Profile** | Sửa email/SDT/địa chỉ, đổi mật khẩu (hash SHA-256 vào DB) |

### 5.2. Giảng viên (7 trang)

| Trang | Chức năng |
|---|---|
| **Tổng quan** | Lịch hôm nay + 5 hoạt động gần đây |
| **Lịch dạy** | Calendar tuần hiển thị các buổi dạy của GV |
| **Lớp của tôi** | Danh sách lớp phụ trách, xem chi tiết (sĩ số, học phí, lịch) |
| **Học viên** | DS học viên trong tất cả lớp, lọc theo lớp, search, xuất CSV |
| **Gửi thông báo** | Chọn lớp + tiêu đề + nội dung → insert vào `notifications` |
| **Nhập điểm** | Chỉnh điểm QT/Thi trực tiếp trong bảng, **tự tính tổng kết 30/70** + xếp loại A+→F, lưu bằng UPSERT vào `grades` |
| **Profile** | Lưu thông tin, đổi mật khẩu |

### 5.3. Nhân viên (6 trang)

| Trang | Chức năng |
|---|---|
| **Tổng quan** | 4 stat card (đăng ký hôm nay, đã thu, đang chờ, doanh thu) |
| **Đăng ký cho HV** | Tra MSV → auto-fill form, chọn môn → cbo lớp tự lọc theo môn, xác nhận → insert vào `registrations` |
| **DS đăng ký** | Search, lọc trạng thái/ngày, xem chi tiết, xuất CSV |
| **Thu học phí** | Chọn dòng → confirm → **transaction**: INSERT `payments` + UPDATE `registrations.trang_thai='paid'`, đồng bộ bên DS đăng ký, in biên lai `.txt` |
| **Quản lý lớp** | Xem danh sách lớp, search, lọc môn/trạng thái |
| **Profile** | Lưu, đổi mật khẩu |

### 5.4. Quản trị viên (10 trang)

| Trang | Chức năng |
|---|---|
| **Dashboard** | Top 5 lớp đông HV (query từ DB), 5 hoạt động gần nhất |
| **Môn học** | CRUD `courses`, search, lọc khoa (IT/MA/EN) |
| **Lớp** | CRUD `classes`, dialog sửa đầy đủ 8 trường có validate sĩ số ≤ max, filter môn/GV/trạng thái |
| **Học viên** | List từ `StudentService.get_all()` có aggregated `cac_lop`, search, filter lớp/khoa, xem chi tiết dialog đẹp |
| **Giảng viên** | List từ `TeacherService.get_all()` có `so_lop`, `diem_tb`, xem chi tiết có điểm đánh giá ⭐ |
| **Nhân viên** | List từ `EmployeeService.get_all()`, filter chức vụ/trạng thái |
| **Học kỳ** | Thêm/toggle mở-đóng đăng ký, hiển thị từ bảng `semesters` |
| **Khung chương trình** | CRUD `curriculum` đầy đủ 6 trường (loại, HK, tiên quyết), lọc ngành/loại/HK, xuất CSV |
| **Nhật ký hệ thống** | View `audit_logs`, search, filter user/action/ngày, xuất CSV |
| **Thống kê** | 3 dataset khác nhau theo HK2-2526 / HK1-2526 / HK2-2425 |

---

## 6. Thiết kế CSDL

### 6.1. Tổng quan: 18 bảng, 3 view, 4 trigger, 29 index

**Tầng xác thực (5 bảng)**: `users`, `students`, `teachers`, `employees`, `admins`

**Tầng học vụ (4 bảng)**: `courses`, `semesters`, `curriculum`, `classes`

**Tầng giao dịch (5 bảng)**: `registrations`, `payments`, `grades`, `schedules`, `exam_schedules`

**Tầng phụ trợ (4 bảng)**: `notifications`, `reviews`, `attendance`, `audit_logs`

### 6.2. View
- `v_class_detail` — join lớp + môn + GV + học kỳ (hay dùng cho UI)
- `v_student_grade_summary` — tính GPA tự động theo HV
- `v_today_schedule` — lịch hôm nay (dùng `CURRENT_DATE`)

### 6.3. Trigger
- `trg_reg_siso` — tự cộng/trừ `siso_hien_tai` khi INSERT/DELETE `registrations`
- `trg_check_class_full` — **chặn** INSERT nếu lớp đã đầy (RAISE EXCEPTION)
- `trg_audit_registrations`, `trg_audit_payments` — auto ghi vào `audit_logs`

### 6.4. Ràng buộc quan trọng
- `registrations.UNIQUE(hv_id, lop_id)` — 1 HV chỉ đăng ký 1 lớp 1 lần
- `grades.PK = (hv_id, lop_id)` — composite primary key
- `payments.reg_id ON DELETE CASCADE` — xóa đăng ký là xóa thanh toán (composition)
- `classes.ma_mon ON DELETE RESTRICT` — không xóa được môn nếu còn lớp
- `reviews.UNIQUE(hv_id, gv_id, lop_id)` — 1 HV chỉ đánh giá 1 GV của 1 lớp 1 lần

---

## 7. Mô hình OOP — 19 class domain

### 7.1. Abstract base
- `Entity` (abstract) — định nghĩa `from_row()` và `to_dict()` cho mọi entity
- `User` (abstract) — định nghĩa thuộc tính chung + `get_display_role()`

### 7.2. User hierarchy (4 role)
- `Student` extends `User` — thêm `msv`, `ngaysinh`, `diachi`
- `Teacher` extends `User` — thêm `ma_gv`, `hoc_vi`, `khoa`, `tham_nien`
- `Employee` extends `User` — thêm `ma_nv`, `chuc_vu`, `phong_ban`
- `Admin` extends `User` — thêm `ma_admin`

### 7.3. Entity hierarchy (13 class)
| Class | Business methods |
|---|---|
| `Course` | — |
| `Semester` | `is_open`, `duration_days` |
| `Klass` (đại diện "lớp", đặt Klass vì `class` là keyword Python) | `is_full`, `available_slots`, `fill_percent`, `format_price` |
| `Curriculum` | `has_prerequisite`, `get_prerequisites` |
| `Registration` | `is_paid`, `is_pending`, `is_cancelled` |
| `Payment` | `format_amount` |
| `Grade` | `compute_total()$`, `compute_letter()$`, `recompute`, `is_passing` |
| `Notification` | `is_urgent`, `is_broadcast` |
| `Review` | `stars` (render ⭐⭐⭐⭐⭐) |
| `Schedule` | `is_past`, `is_today`, `duration_minutes` |
| `ExamSchedule` | `is_past`, `is_upcoming` |
| `Attendance` | `is_present`, `is_late`, `is_absent` |
| `AuditLog` | — |

### 7.4. Cấu trúc thư mục
```
backend/models/
├── __init__.py          (re-export 19 class)
├── entity.py            (abstract Entity)
├── user/
│   ├── __init__.py
│   ├── base.py          (abstract User)
│   ├── student.py
│   ├── teacher.py
│   ├── employee.py
│   └── admin.py
├── course.py
├── semester.py
├── klass.py
├── curriculum.py
├── registration.py
├── payment.py
├── grade.py
├── notification.py
├── review.py
├── schedule.py
├── exam_schedule.py
├── attendance.py
└── audit_log.py
```

---

## 8. Service Layer — 10 class business

| Service | Method tiêu biểu | Ghi chú |
|---|---|---|
| `AuthService` | `login(u, p) → User` | **Factory**: build subclass Student/Teacher/Employee/Admin tùy role |
| `CourseService` | `get_all_courses`, `create_class`, `get_students_by_teacher` | CRUD môn + lớp |
| `RegistrationService` | `register_student → reg_id`, `confirm_payment` | **Transaction** (INSERT payment + UPDATE registration) |
| `GradeService` | `save_grade` [UPSERT với `ON CONFLICT DO UPDATE`] | Tự tính `tong_ket = 0.3*qt + 0.7*thi` |
| `NotificationService` | `send`, `get_for_student` (lọc theo lớp HV đăng ký) | |
| `StudentService` | `get_all()` | Có `string_agg(DISTINCT lop_id)` |
| `TeacherService` | `get_all`, `get_for_review` | Có `AVG(diem) FROM reviews` |
| `EmployeeService` | `get_all` | |
| `ReviewService` | `submit_review` [UPSERT theo (hv_id, gv_id, lop_id)] | |
| `StatsService` | `admin_overview`, `top_classes`, `recent_activity` (UNION), `employee_today` | Dashboard data |

---

## 9. Design Patterns áp dụng

| # | Pattern | Chỗ thể hiện |
|---|---|---|
| 1 | **Singleton** | `Database.__new__` trả về cùng 1 instance trong toàn app |
| 2 | **Factory Method** | `Entity.from_row(cls, row)` + `AuthService._build_user(row)` — tạo object phù hợp từ dữ liệu |
| 3 | **Abstract Base Class** | `Entity`, `User` — dùng `@abstractmethod` bắt lớp con override |
| 4 | **Context Manager** | `db.cursor()` với `@contextmanager` — tự commit/rollback |
| 5 | **Template Method** | `Entity.__repr__` gọi `_key()` — lớp con override `_key()` để tùy biến output |
| 6 | **Fallback Pattern** | `DB_AVAILABLE` — service thật → MOCK khi DB không sẵn sàng |

---

## 10. 5 quan hệ UML

| # | Quan hệ | Ví dụ trong dự án | Minh chứng |
|---|---|---|---|
| 1 | **Inheritance** (kế thừa) | `Student extends User`, `Klass extends Entity` | `user/student.py`, `klass.py` |
| 2 | **Association** (liên kết) | `Teacher ↔ Klass` qua `gv_id` | `schema.sql: classes.gv_id REFERENCES teachers` |
| 3 | **Aggregation** (tổng hợp) | `Course ◇ Klass` — lớp có thể tồn tại độc lập với môn | `ON DELETE RESTRICT` |
| 4 | **Composition** (cấu thành) | `Registration ◆ Payment` — xóa đăng ký là xóa thanh toán | `ON DELETE CASCADE` |
| 5 | **Dependency** (phụ thuộc) | `AuthService ┄→ Database`, `Service ┄→ User model` | `from backend.database.db import db` |

---

## 11. Các tính năng đặc biệt

### 11.1. Thanh toán offline (không tích hợp cổng online)
- Thiết kế cho trung tâm nhỏ — HV trả tiền tại quầy (tiền mặt / chuyển khoản / VNPay / Momo)
- NV chọn hình thức rồi confirm → hệ thống ghi payment + đổi status đăng ký
- In biên lai số `BLyyyyMMddHHmmss` ra file `.txt`

### 11.2. Tính điểm tự động
- Công thức: `tong_ket = 30% QT + 70% Thi`
- Xếp loại: A+ (≥9), A (≥8.5), B+ (≥8), B (≥7), C+ (≥6.5), C (≥5.5), D (≥4), F
- Lưu bằng UPSERT — sửa lại cũng được

### 11.3. Trigger bảo toàn dữ liệu
- Auto update sĩ số khi có đăng ký mới
- Tự động raise exception khi cố đăng ký vào lớp đã đầy
- Auto log audit trail cho mọi thao tác trên `registrations` và `payments`

### 11.4. Dialog chi tiết custom (không dùng QMessageBox mặc định)
- `show_detail_dialog()` — header navy với avatar tròn + body scrollable + footer bọc nút navy
- Áp dụng cho: Chi tiết HV/GV/NV/lớp/đăng ký

### 11.5. Export CSV chuẩn Excel
- Helper `export_table_csv()` ghi file `utf-8-sig` (Excel đọc tiếng Việt không lỗi)
- Dùng ở 5 trang: teacher students, emp reg list, emp classes, admin curr, admin audit

---

## 12. Hướng dẫn chạy

### 12.1. Có Docker (demo đầy đủ)

```bash
# 1. Khởi động PostgreSQL + pgAdmin
docker compose up -d postgres

# 2. Chờ DB ready (~5 giây, kiểm tra bằng pgAdmin tại localhost:5050)

# 3. Chạy app
cd frontend
python main.py
# → [DB] Ket noi PostgreSQL OK - dung du lieu that
```

### 12.2. Không có Docker (fallback MOCK)

```bash
cd frontend
python main.py
# → [DB] Khong ket noi duoc - fallback MOCK data
```

App vẫn chạy bình thường với dữ liệu mock tương đương.

### 12.3. Requirements
```
PyQt5==5.15.10
psycopg2-binary==2.9.9
python-dotenv==1.0.1
```

### 12.4. Biến môi trường (file `.env` hoặc set sẵn)
```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=eaut_db
POSTGRES_USER=eaut_admin
POSTGRES_PASSWORD=eaut_password
```

---

## 13. Cấu trúc dự án

```
BaiTapLonPy/
├── backend/
│   ├── database/
│   │   ├── db.py              ← Database Singleton + cursor context manager
│   │   ├── schema.sql         ← 18 bảng, 3 view, 4 trigger
│   │   └── seed.sql           ← Data mẫu (~150 rows across tables)
│   ├── models/                ← 19 class domain (2 abstract + 17 concrete)
│   │   ├── entity.py
│   │   ├── user/              (package 5 file)
│   │   └── [13 file entity]
│   ├── services/              ← 10 service class
│   └── utils/
│       └── hash_util.py       ← SHA-256
├── frontend/
│   ├── main.py                ← ~3800 dòng, chứa App + 5 Window + 50+ handler
│   ├── theme_helper.py        ← Load QSS + setup icons
│   ├── ui/                    ← 28 file .ui (QtDesigner)
│   ├── styles/
│   │   └── eaut_theme.qss     ← Theme EAUT (navy, gold, green)
│   └── resources/
│       ├── icons/             ← Feather icons PNG
│       └── bg_*.png, logo.png
├── docs/
│   ├── mo-ta-he-thong.md      ← File này
│   ├── mo-ta-chuc-nang.md     ← Mô tả chức năng cũ (giữ làm tham khảo)
│   ├── class_diagram/         ← Class diagram Mermaid
│   ├── erd/                   ← ERD (PNG + Mermaid)
│   └── mockups/               ← Ảnh mockup UI
├── docker-compose.yml         ← PostgreSQL 16 + pgAdmin
└── requirements.txt
```

---

## 14. Giới hạn hiện tại

- **Xuất PDF** ở trang xem điểm HV: mới hiện popup "đang phát triển", chưa gen PDF thật (có thể làm sau bằng `reportlab`)
- **Xuất Excel**: dùng CSV (`utf-8-sig`) — Excel mở được nhưng là `.csv` chứ không phải `.xlsx`
- **Lịch học/dạy** trong UI hiện parse chuỗi `classes.lich = "T3, T5 (7:00-9:30)"` chứ chưa query từ bảng `schedules` (dù bảng đã có data mẫu)
- **Admin Thêm lớp/HV/GV/NV** mới chỉ update UI + MOCK list, chưa INSERT xuống DB thật (cần thêm method `create_user` cho các service)
- **Filter Audit theo ngày** chỉ hiểu "Hôm nay", chưa hỗ trợ "7 ngày qua" / "30 ngày qua"
- **Không có thanh toán online** — cố tình theo thiết kế (trung tâm thu tại quầy)

---

## 15. Hướng phát triển tiếp

1. Hoàn thiện integration: `Admin Thêm X` → gọi service DB thật
2. Tích hợp `reportlab` để xuất PDF bảng điểm
3. Dùng `openpyxl` để xuất `.xlsx` thay vì `.csv`
4. Query lịch học/dạy từ bảng `schedules` thay vì parse chuỗi
5. Thêm trang điểm danh (attendance) cho GV
6. Thêm biểu đồ cho trang thống kê (dùng `matplotlib` trong Qt widget)
7. Chuyển mật khẩu về hash SHA-256 hoàn toàn (bỏ plain text)
8. Thêm reset password qua email (dùng `smtplib`)

---

*Tài liệu được cập nhật tự động khi có thay đổi lớn. Mọi góp ý liên hệ nhóm phát triển.*
