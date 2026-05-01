# Class Diagram — Hệ thống quản lý trung tâm ngoại khóa EAUT

> Entity hierarchy: 1 abstract base + 13 entity concrete + đầy đủ quan hệ
> Render: GitHub markdown, VS Code Mermaid Preview, [mermaid.live](https://mermaid.live)

---

## Sơ đồ lớp (Entity hierarchy)

```mermaid
classDiagram
    direction TB

    %% ========== ABSTRACT BASE ==========
    class Entity {
        <<abstract>>
        +from_row(row)* Entity
        +to_dict()* dict
        +__repr__() str
        #_key() str
    }

    %% ========== ACADEMIC ==========
    class Course {
        -str _ma_mon
        -str _ten_mon
        -str _mo_ta
        +ma_mon() str
        +ten_mon() str
    }

    class Semester {
        -str _id
        -str _ten
        -str _nam_hoc
        -date _bat_dau
        -date _ket_thuc
        -str _trang_thai
        +is_open() bool
        +duration_days() int
    }

    class Klass {
        -str _ma_lop
        -str _ma_mon
        -int _gv_id
        -str _semester_id
        -int _siso_max
        -int _siso_hien_tai
        -int _gia
        -str _trang_thai
        +is_full() bool
        +available_slots() int
        +fill_percent() int
        +format_price() str
    }

    class Curriculum {
        -int _id
        -str _ma_mon
        -int _tin_chi
        -str _loai
        -str _hoc_ky_de_nghi
        -str _mon_tien_quyet
        -str _nganh
        +has_prerequisite() bool
        +get_prerequisites() list
    }

    %% ========== TRANSACTION ==========
    class Registration {
        -int _id
        -int _hv_id
        -str _lop_id
        -int _nv_xu_ly
        -datetime _ngay_dk
        -str _trang_thai
        +is_paid() bool
        +is_pending() bool
        +is_cancelled() bool
    }

    class Payment {
        -int _id
        -int _reg_id
        -int _so_tien
        -str _hinh_thuc
        -datetime _ngay_thu
        -int _nv_thu
        -str _so_bien_lai
        +format_amount() str
    }

    class Grade {
        -int _hv_id
        -str _lop_id
        -float _diem_qt
        -float _diem_thi
        -float _tong_ket
        -str _xep_loai
        +is_passing() bool
        +compute_total(qt, thi)$ float
        +compute_letter(score)$ str
        +recompute() void
    }

    %% ========== COMMUNICATION ==========
    class Notification {
        -int _id
        -int _tu_id
        -str _den_lop
        -str _tieu_de
        -str _noi_dung
        -str _loai
        -datetime _ngay_tao
        +is_urgent() bool
        +is_broadcast() bool
    }

    class Review {
        -int _id
        -int _hv_id
        -int _gv_id
        -str _lop_id
        -int _diem
        -str _nhan_xet
        +stars() str
    }

    %% ========== SCHEDULING ==========
    class Schedule {
        -int _id
        -str _lop_id
        -date _ngay
        -int _thu
        -time _gio_bat_dau
        -time _gio_ket_thuc
        -int _buoi_so
        -str _trang_thai
        +is_past() bool
        +is_today() bool
        +duration_minutes() int
    }

    class ExamSchedule {
        -int _id
        -str _lop_id
        -str _semester_id
        -date _ngay_thi
        -str _ca_thi
        -str _hinh_thuc
        -int _so_cau
        -int _thoi_gian_phut
        +is_past() bool
        +is_upcoming() bool
    }

    class Attendance {
        -int _id
        -int _schedule_id
        -int _hv_id
        -str _trang_thai
        -time _gio_vao
        -int _recorded_by
        +is_present() bool
        +is_late() bool
        +is_absent() bool
    }

    class AuditLog {
        -int _id
        -int _user_id
        -str _username
        -str _action
        -str _target_type
        -str _target_id
        -str _description
    }

    %% ========== INHERITANCE từ Entity ==========
    Entity <|-- Course
    Entity <|-- Semester
    Entity <|-- Klass
    Entity <|-- Curriculum
    Entity <|-- Registration
    Entity <|-- Payment
    Entity <|-- Grade
    Entity <|-- Notification
    Entity <|-- Review
    Entity <|-- Schedule
    Entity <|-- ExamSchedule
    Entity <|-- Attendance
    Entity <|-- AuditLog

    %% ========== QUAN HỆ giữa các entity ==========
    Course "1" o-- "N" Klass        : aggregation
    Course "1" o-- "N" Curriculum   : có trong CT
    Semester "1" o-- "N" Klass      : chứa
    Semester "1" -- "N" ExamSchedule

    Klass "1" -- "N" Registration   : được đăng ký
    Klass "1" -- "N" Grade
    Klass "1" -- "N" Schedule
    Klass "1" -- "N" ExamSchedule
    Klass "1" -- "N" Review
    Klass "1" -- "N" Notification

    Registration "1" *-- "1..N" Payment : composition

    Schedule "1" -- "N" Attendance
```

---

## Ký hiệu Mermaid

| Ký hiệu | Ý nghĩa |
|---|---|
| `<\|--` | **Inheritance** — kế thừa |
| `*--` | **Composition** — phần tử con chết khi cha chết |
| `o--` | **Aggregation** — con tồn tại độc lập |
| `--` | **Association** — liên kết thường |
| `<<abstract>>` | Lớp trừu tượng |
| `+` / `-` / `#` | public / private / protected |
| `*` cuối method | abstract (phải override) |
| `$` cuối method | static / classmethod |

---

## 5 quan hệ UML thể hiện

| # | Quan hệ | Ví dụ trong sơ đồ |
|---|---|---|
| 1 | **Inheritance** | 13 entity kế thừa `Entity` (abstract base) |
| 2 | **Association** | `Klass ↔ Registration`, `Klass ↔ Grade` |
| 3 | **Aggregation** | `Course ◇ Klass` — môn có lớp, lớp tồn tại độc lập |
| 4 | **Composition** | `Registration ◆ Payment` — xóa ĐK = xóa thanh toán |
| 5 | **Dependency** | (thể hiện ở Service Layer, không vẽ ở đây) |

## Design Patterns

| Pattern | Áp dụng |
|---|---|
| **Abstract Base Class** | `Entity` với `@abstractmethod from_row(), to_dict()` |
| **Factory Method** | `Entity.from_row(cls, row)` — mỗi subclass tự build từ dict |
| **Template Method** | `Entity.__repr__` gọi `_key()` (lớp con override) |

## Tổng số class

| Loại | Số lượng | Tên |
|---|---|---|
| Abstract base | 1 | `Entity` |
| Academic entity | 4 | `Course`, `Semester`, `Klass`, `Curriculum` |
| Transaction entity | 3 | `Registration`, `Payment`, `Grade` |
| Communication entity | 2 | `Notification`, `Review` |
| Scheduling entity | 3 | `Schedule`, `ExamSchedule`, `Attendance` |
| Logging entity | 1 | `AuditLog` |
| **TỔNG** | **14** | |

---

## Sơ đồ kiến trúc 3 lớp (3-tier dependency)

```mermaid
classDiagram
    direction TB

    class PresentationLayer {
        <<Frontend / PyQt5>>
        +LoginWindow
        +MainWindow (Student)
        +AdminWindow
        +TeacherWindow
        +EmployeeWindow
        +_GradeEditorDelegate
    }

    class ServiceLayer {
        <<Business Logic>>
        +AuthService
        +UserService
        +CourseService
        +SemesterService
        +CurriculumService
        +RegistrationService
        +GradeService
        +ScheduleService
        +ExamService
        +AttendanceService
        +NotificationService
        +AuditService
        +StatsService
    }

    class DomainLayer {
        <<Entity / Model>>
        +Entity «abstract»
        +Course
        +Semester
        +Klass
        +Curriculum
        +Registration
        +Payment
        +Grade
        +Notification
        +Review
        +Schedule
        +ExamSchedule
        +Attendance
        +AuditLog
    }

    PresentationLayer ..> ServiceLayer : depends on
    ServiceLayer ..> DomainLayer : depends on
```

### Quan hệ dependency giữa 3 layer

| Layer | Phụ thuộc | Lý do |
|-------|-----------|-------|
| **Presentation** | → Service | Window/Dialog gọi `AuthService.login()`, `RegistrationService.create()`, `GradeService.save_grade()`... Không truy cập DB trực tiếp |
| **Service** | → Domain | Service nhận `dict` từ DB rồi build `Entity` qua `Entity.from_row`, dùng business method (`Klass.is_full()`, `Grade.compute_total()`, `Curriculum.get_prerequisites()`) |
| **Domain** | (không phụ thuộc) | Entity là POPO thuần — không biết Service hay UI, dễ test + tái sử dụng |

> Tuân thủ **Dependency Rule** (Clean Architecture): mũi tên chỉ đi 1 chiều từ ngoài vào trong. Domain là core ổn định nhất, UI là lớp dễ thay đổi nhất.
