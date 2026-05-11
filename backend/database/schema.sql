-- EAUT - Trung tam dao tao ngoai khoa
-- Schema PostgreSQL (full) - chay boi docker-entrypoint-initdb.d
-- 17 bang + 2 view + 3 trigger

-- xoa truoc theo thu tu nguoc FK (cho phep chay lai)
DROP TABLE IF EXISTS attendance CASCADE;
DROP TABLE IF EXISTS exam_schedules CASCADE;
DROP TABLE IF EXISTS schedules CASCADE;
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS curriculum CASCADE;
DROP TABLE IF EXISTS reviews CASCADE;
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS grades CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS registrations CASCADE;
DROP TABLE IF EXISTS classes CASCADE;
DROP TABLE IF EXISTS semesters CASCADE;
DROP TABLE IF EXISTS courses CASCADE;
DROP TABLE IF EXISTS admins CASCADE;
DROP TABLE IF EXISTS employees CASCADE;
DROP TABLE IF EXISTS teachers CASCADE;
DROP TABLE IF EXISTS students CASCADE;
DROP TABLE IF EXISTS users CASCADE;


-- ==========================================================
-- 1. USERS (bang base cho 4 role)
-- ==========================================================
CREATE TABLE users (
    id          SERIAL PRIMARY KEY,
    username    VARCHAR(50) UNIQUE NOT NULL,
    password    VARCHAR(255) NOT NULL,
    role        VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'teacher', 'employee', 'student')),
    full_name   VARCHAR(100) NOT NULL,
    email       VARCHAR(100),
    sdt         VARCHAR(20),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active   BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_username ON users(username);


-- ==========================================================
-- 2. STUDENTS
-- ==========================================================
CREATE TABLE students (
    user_id     INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    msv         VARCHAR(20) UNIQUE NOT NULL,
    ngaysinh    DATE,
    gioitinh    VARCHAR(10),
    diachi      VARCHAR(200)
);


-- ==========================================================
-- 3. TEACHERS
-- ==========================================================
CREATE TABLE teachers (
    user_id         INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    ma_gv           VARCHAR(20) UNIQUE NOT NULL,
    hoc_vi          VARCHAR(30),
    khoa            VARCHAR(100),
    chuyen_nganh    VARCHAR(100),
    tham_nien       INTEGER DEFAULT 0
);


-- ==========================================================
-- 4. EMPLOYEES
-- ==========================================================
CREATE TABLE employees (
    user_id         INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    ma_nv           VARCHAR(20) UNIQUE NOT NULL,
    chuc_vu         VARCHAR(50),
    phong_ban       VARCHAR(50),
    ngay_vao_lam    DATE
);


-- ==========================================================
-- 5. ADMINS
-- ==========================================================
CREATE TABLE admins (
    user_id     INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    ma_admin    VARCHAR(20) UNIQUE NOT NULL
);


-- ==========================================================
-- 6. COURSES (mon hoc)
-- ==========================================================
CREATE TABLE courses (
    ma_mon      VARCHAR(20) PRIMARY KEY,
    ten_mon     VARCHAR(100) NOT NULL,
    mo_ta       TEXT
);


-- ==========================================================
-- 7. SEMESTERS (hoc ky) - MOI
-- ==========================================================
CREATE TABLE semesters (
    id          VARCHAR(20) PRIMARY KEY,            -- 'HK2-2526'
    ten         VARCHAR(50) NOT NULL,               -- 'Hoc ky 2'
    nam_hoc     VARCHAR(20) NOT NULL,               -- '2025-2026'
    bat_dau     DATE NOT NULL,
    ket_thuc    DATE NOT NULL,
    trang_thai  VARCHAR(20) DEFAULT 'closed'
                CHECK (trang_thai IN ('open', 'closed', 'upcoming')),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (bat_dau < ket_thuc)
);

CREATE INDEX idx_sem_status ON semesters(trang_thai);


-- ==========================================================
-- 8. CLASSES (lop cu the cua 1 mon trong 1 hoc ky) - CO semester_id MOI
-- ==========================================================
CREATE TABLE classes (
    ma_lop          VARCHAR(30) PRIMARY KEY,
    ma_mon          VARCHAR(20) NOT NULL REFERENCES courses(ma_mon) ON DELETE RESTRICT,
    gv_id           INTEGER REFERENCES teachers(user_id) ON DELETE SET NULL,
    semester_id     VARCHAR(20) REFERENCES semesters(id) ON DELETE SET NULL,
    lich            VARCHAR(100),
    phong           VARCHAR(20),
    siso_max        INTEGER DEFAULT 40,
    siso_hien_tai   INTEGER DEFAULT 0,
    gia             NUMERIC(12, 0) NOT NULL,
    trang_thai      VARCHAR(20) DEFAULT 'open'
                    CHECK (trang_thai IN ('open', 'full', 'closed')),
    ngay_bat_dau    DATE,                            -- ngay khoa hoc bat dau thuc te
    ngay_ket_thuc   DATE,                            -- ngay du kien ket thuc
    so_buoi         INTEGER DEFAULT 24               -- tong so buoi hoc
);

CREATE INDEX idx_classes_mon ON classes(ma_mon);
CREATE INDEX idx_classes_gv ON classes(gv_id);
CREATE INDEX idx_classes_sem ON classes(semester_id);


-- ==========================================================
-- 9. REGISTRATIONS (dang ky vao lop)
-- ==========================================================
CREATE TABLE registrations (
    id              SERIAL PRIMARY KEY,
    hv_id           INTEGER NOT NULL REFERENCES students(user_id) ON DELETE CASCADE,
    lop_id          VARCHAR(30) NOT NULL REFERENCES classes(ma_lop) ON DELETE RESTRICT,
    nv_xu_ly        INTEGER REFERENCES employees(user_id) ON DELETE SET NULL,
    ngay_dk         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    trang_thai      VARCHAR(30) DEFAULT 'pending_payment'
                    CHECK (trang_thai IN ('pending_payment', 'paid', 'cancelled', 'completed')),
    UNIQUE (hv_id, lop_id)
);

CREATE INDEX idx_reg_hv ON registrations(hv_id);
CREATE INDEX idx_reg_lop ON registrations(lop_id);
CREATE INDEX idx_reg_status ON registrations(trang_thai);


-- ==========================================================
-- 10. PAYMENTS (thanh toan - do NV thu tai quay, KHONG co thanh toan online)
-- ==========================================================
CREATE TABLE payments (
    id          SERIAL PRIMARY KEY,
    reg_id      INTEGER NOT NULL REFERENCES registrations(id) ON DELETE CASCADE,
    so_tien     NUMERIC(12, 0) NOT NULL CHECK (so_tien >= 0),
    hinh_thuc   VARCHAR(30) NOT NULL,                -- 'Tien mat', 'Chuyen khoan', 'VNPay', 'Momo'
    ngay_thu    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    nv_thu      INTEGER REFERENCES employees(user_id) ON DELETE SET NULL,
    ghi_chu     TEXT,
    so_bien_lai VARCHAR(50) UNIQUE                    -- vd 'BL20260423103045'
);

CREATE INDEX idx_pay_reg ON payments(reg_id);
CREATE INDEX idx_pay_date ON payments(ngay_thu DESC);


-- ==========================================================
-- 11. GRADES (diem)
-- ==========================================================
CREATE TABLE grades (
    hv_id       INTEGER NOT NULL REFERENCES students(user_id) ON DELETE CASCADE,
    lop_id      VARCHAR(30) NOT NULL REFERENCES classes(ma_lop) ON DELETE CASCADE,
    diem_qt     NUMERIC(4, 2) CHECK (diem_qt >= 0 AND diem_qt <= 10),
    diem_thi    NUMERIC(4, 2) CHECK (diem_thi >= 0 AND diem_thi <= 10),
    tong_ket    NUMERIC(4, 2) CHECK (tong_ket >= 0 AND tong_ket <= 10),
    xep_loai    VARCHAR(5),
    gv_nhap     INTEGER REFERENCES teachers(user_id) ON DELETE SET NULL,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (hv_id, lop_id)
);


-- ==========================================================
-- 12. NOTIFICATIONS (thong bao)
-- ==========================================================
CREATE TABLE notifications (
    id          SERIAL PRIMARY KEY,
    tu_id       INTEGER REFERENCES users(id) ON DELETE SET NULL,
    den_lop     VARCHAR(30) REFERENCES classes(ma_lop) ON DELETE CASCADE,
    den_hv_id   INTEGER REFERENCES users(id) ON DELETE CASCADE,  -- gui rieng 1 HV
    tieu_de     VARCHAR(200) NOT NULL,
    noi_dung    TEXT NOT NULL,
    loai        VARCHAR(20) DEFAULT 'info'
                CHECK (loai IN ('info', 'warning', 'urgent')),
    ngay_tao    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notif_lop ON notifications(den_lop);
CREATE INDEX idx_notif_den_hv ON notifications(den_hv_id);
CREATE INDEX idx_notif_ngay ON notifications(ngay_tao DESC);


-- ==========================================================
-- 13. REVIEWS (HV danh gia GV)
-- ==========================================================
CREATE TABLE reviews (
    id          SERIAL PRIMARY KEY,
    hv_id       INTEGER NOT NULL REFERENCES students(user_id) ON DELETE CASCADE,
    gv_id       INTEGER NOT NULL REFERENCES teachers(user_id) ON DELETE CASCADE,
    lop_id      VARCHAR(30) REFERENCES classes(ma_lop) ON DELETE SET NULL,
    diem        INTEGER NOT NULL CHECK (diem BETWEEN 1 AND 5),
    nhan_xet    TEXT,
    ngay        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (hv_id, gv_id, lop_id)
);

CREATE INDEX idx_review_gv ON reviews(gv_id);


-- ==========================================================
-- 14. CURRICULUM (khung chuong trinh dao tao) - MOI
-- ==========================================================
CREATE TABLE curriculum (
    id              SERIAL PRIMARY KEY,
    ma_mon          VARCHAR(20) NOT NULL REFERENCES courses(ma_mon) ON DELETE CASCADE,
    tin_chi         INTEGER NOT NULL DEFAULT 3 CHECK (tin_chi > 0),
    loai            VARCHAR(20) NOT NULL
                    CHECK (loai IN ('Bat buoc', 'Tu chon', 'Dai cuong')),
    hoc_ky_de_nghi  VARCHAR(30),                        -- ten dot khoa hoc, vd 'HK1'/'Dot 1'/'Mua he 2026'
    mon_tien_quyet  VARCHAR(200),                        -- 'IT001, MA001' hoac ''
    nganh           VARCHAR(50) NOT NULL DEFAULT 'CNTT', -- 'CNTT', 'Toan', 'Ngoai ngu'
    ghi_chu         TEXT,
    UNIQUE (ma_mon, nganh)
);

CREATE INDEX idx_curr_nganh ON curriculum(nganh);
CREATE INDEX idx_curr_hk ON curriculum(hoc_ky_de_nghi);


-- ==========================================================
-- 15. AUDIT_LOGS (nhat ky he thong) - MOI
-- ==========================================================
CREATE TABLE audit_logs (
    id              BIGSERIAL PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id) ON DELETE SET NULL,
    username        VARCHAR(50),                         -- luu truc tiep phong user bi xoa
    role            VARCHAR(20),                         -- 'admin', 'teacher', 'employee', 'student'
    action          VARCHAR(50) NOT NULL,                -- 'login', 'register', 'payment', 'update_grade'...
    target_type     VARCHAR(30),                         -- 'users', 'registrations', 'grades'...
    target_id       VARCHAR(50),                         -- id cua ban ghi bi tac dong
    description     TEXT,
    ip_address      VARCHAR(45),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_date ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_target ON audit_logs(target_type, target_id);


-- ==========================================================
-- 16. SCHEDULES (lich hoc theo buoi cu the) - MOI
-- ==========================================================
CREATE TABLE schedules (
    id              SERIAL PRIMARY KEY,
    lop_id          VARCHAR(30) NOT NULL REFERENCES classes(ma_lop) ON DELETE CASCADE,
    ngay            DATE NOT NULL,
    thu             INTEGER CHECK (thu BETWEEN 2 AND 8),    -- T2-T8 (8=CN)
    gio_bat_dau     TIME NOT NULL,
    gio_ket_thuc    TIME NOT NULL,
    phong           VARCHAR(20),
    buoi_so         INTEGER,                                 -- buoi thu may trong khoa
    noi_dung        VARCHAR(200),                            -- chu de buoi hoc
    meeting_url     VARCHAR(500),                            -- link Zoom/Meet/Jitsi neu buoi day online
    trang_thai      VARCHAR(20) DEFAULT 'scheduled'
                    CHECK (trang_thai IN ('scheduled', 'completed', 'cancelled', 'postponed')),
    ghi_chu         TEXT,
    UNIQUE (lop_id, ngay, gio_bat_dau),
    CHECK (gio_bat_dau < gio_ket_thuc)
);

CREATE INDEX idx_schedule_lop ON schedules(lop_id);
CREATE INDEX idx_schedule_ngay ON schedules(ngay);
CREATE INDEX idx_schedule_status ON schedules(trang_thai);


-- ==========================================================
-- 17. EXAM_SCHEDULES (lich thi) - MOI
-- ==========================================================
CREATE TABLE exam_schedules (
    id              SERIAL PRIMARY KEY,
    lop_id          VARCHAR(30) NOT NULL REFERENCES classes(ma_lop) ON DELETE CASCADE,
    semester_id     VARCHAR(20) REFERENCES semesters(id) ON DELETE SET NULL,
    ngay_thi        DATE NOT NULL,
    ca_thi          VARCHAR(50),                          -- 'Ca 1 (07:30-09:00)'
    gio_bat_dau     TIME,
    gio_ket_thuc    TIME,
    phong           VARCHAR(20),
    hinh_thuc       VARCHAR(50) DEFAULT 'Tu luan',        -- 'Trac nghiem', 'Tu luan', 'Van dap', 'Thuc hanh'
    so_cau          INTEGER,
    thoi_gian_phut  INTEGER DEFAULT 90,
    ghi_chu         TEXT,
    UNIQUE (lop_id, ngay_thi, ca_thi)
);

CREATE INDEX idx_exam_lop ON exam_schedules(lop_id);
CREATE INDEX idx_exam_ngay ON exam_schedules(ngay_thi);
CREATE INDEX idx_exam_sem ON exam_schedules(semester_id);


-- ==========================================================
-- 18. ATTENDANCE (diem danh buoi hoc) - MOI
-- ==========================================================
CREATE TABLE attendance (
    id              BIGSERIAL PRIMARY KEY,
    schedule_id     INTEGER NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
    hv_id           INTEGER NOT NULL REFERENCES students(user_id) ON DELETE CASCADE,
    trang_thai      VARCHAR(20) DEFAULT 'present'
                    CHECK (trang_thai IN ('present', 'absent', 'late', 'excused')),
    gio_vao         TIME,
    ghi_chu         TEXT,
    recorded_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    recorded_by     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE (schedule_id, hv_id)
);

CREATE INDEX idx_att_schedule ON attendance(schedule_id);
CREATE INDEX idx_att_hv ON attendance(hv_id);
CREATE INDEX idx_att_status ON attendance(trang_thai);


-- ==========================================================
-- 19. ASSIGNMENTS (bai tap GV giao cho lop) - MOI
-- ==========================================================
CREATE TABLE assignments (
    id          SERIAL PRIMARY KEY,
    lop_id      VARCHAR(30) NOT NULL REFERENCES classes(ma_lop) ON DELETE CASCADE,
    gv_id       INTEGER NOT NULL REFERENCES teachers(user_id) ON DELETE CASCADE,
    tieu_de     VARCHAR(200) NOT NULL,
    mo_ta       TEXT,
    file_path   VARCHAR(500),   -- file dinh kem GV upload (anh/word/pdf...), relative tu backend/uploads/
    han_nop     TIMESTAMP,
    diem_toi_da NUMERIC(4, 2) DEFAULT 10 CHECK (diem_toi_da > 0 AND diem_toi_da <= 100),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_asg_lop ON assignments(lop_id);
CREATE INDEX idx_asg_gv ON assignments(gv_id);
CREATE INDEX idx_asg_han ON assignments(han_nop);


-- ==========================================================
-- 20. SUBMISSIONS (HV nop bai + GV cham) - MOI
-- ==========================================================
CREATE TABLE submissions (
    id              SERIAL PRIMARY KEY,
    assignment_id   INTEGER NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
    hv_id           INTEGER NOT NULL REFERENCES students(user_id) ON DELETE CASCADE,
    noi_dung        TEXT,        -- text bai lam HV nhap
    file_url        VARCHAR(500),  -- placeholder cho upload file sau
    nop_luc         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    diem            NUMERIC(4, 2),  -- GV cham
    nhan_xet        TEXT,        -- GV gop y
    cham_luc        TIMESTAMP,
    UNIQUE (assignment_id, hv_id)  -- moi HV nop 1 lan / bai (re-nop = update)
);

CREATE INDEX idx_sub_asg ON submissions(assignment_id);
CREATE INDEX idx_sub_hv ON submissions(hv_id);
CREATE INDEX idx_sub_diem ON submissions(diem);


-- ==========================================================
-- 21. CLASS_VIDEOS (thu vien video bai giang cua lop) - MOI
-- ==========================================================
-- GV upload link YouTube/Drive/Vimeo de HV xem lai bai giang.
-- Khong luu video file (storage tot kem) -> chi luu URL link.
CREATE TABLE class_videos (
    id          SERIAL PRIMARY KEY,
    lop_id      VARCHAR(30) NOT NULL REFERENCES classes(ma_lop) ON DELETE CASCADE,
    gv_id       INTEGER NOT NULL REFERENCES teachers(user_id) ON DELETE CASCADE,
    tieu_de     VARCHAR(200) NOT NULL,
    video_url   VARCHAR(500) NOT NULL,    -- YouTube/Drive/Vimeo/... share link
    mo_ta       TEXT,
    buoi_so     INTEGER,                  -- thuoc buoi nao trong khoa (optional)
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cv_lop ON class_videos(lop_id);
CREATE INDEX idx_cv_gv ON class_videos(gv_id);


-- ==========================================================
-- VIEWS
-- ==========================================================

-- v_class_detail: thong tin day du lop + GV + mon + ky hoc
CREATE OR REPLACE VIEW v_class_detail AS
SELECT
    c.ma_lop,
    c.ma_mon,
    co.ten_mon,
    c.gv_id,
    u.full_name AS ten_gv,
    t.hoc_vi,
    c.semester_id,
    s.ten AS ten_hk,
    s.nam_hoc,
    c.lich,
    c.phong,
    c.siso_max,
    c.siso_hien_tai,
    c.gia,
    c.trang_thai,
    c.ngay_bat_dau,
    c.ngay_ket_thuc,
    c.so_buoi
FROM classes c
LEFT JOIN courses co ON c.ma_mon = co.ma_mon
LEFT JOIN teachers t ON c.gv_id = t.user_id
LEFT JOIN users u ON t.user_id = u.id
LEFT JOIN semesters s ON c.semester_id = s.id;


-- v_student_grade_summary: tong hop diem + GPA cua HV
CREATE OR REPLACE VIEW v_student_grade_summary AS
SELECT
    s.user_id AS hv_id,
    s.msv,
    u.full_name,
    COUNT(g.lop_id) AS so_lop_hoc,
    ROUND(AVG(g.tong_ket)::numeric, 2) AS gpa,
    COUNT(CASE WHEN g.tong_ket >= 5 THEN 1 END) AS so_lop_dat,
    COUNT(CASE WHEN g.tong_ket < 5 THEN 1 END) AS so_lop_rot
FROM students s
JOIN users u ON u.id = s.user_id
LEFT JOIN grades g ON g.hv_id = s.user_id
GROUP BY s.user_id, s.msv, u.full_name;


-- v_today_schedule: lich hoc hom nay (cho HV va GV xem nhanh)
CREATE OR REPLACE VIEW v_today_schedule AS
SELECT
    sc.id AS schedule_id,
    sc.lop_id,
    co.ten_mon,
    u.full_name AS ten_gv,
    sc.ngay,
    sc.gio_bat_dau,
    sc.gio_ket_thuc,
    sc.phong,
    sc.buoi_so,
    sc.noi_dung,
    sc.trang_thai
FROM schedules sc
JOIN classes c ON c.ma_lop = sc.lop_id
LEFT JOIN courses co ON co.ma_mon = c.ma_mon
LEFT JOIN teachers t ON t.user_id = c.gv_id
LEFT JOIN users u ON u.id = t.user_id
WHERE sc.ngay = CURRENT_DATE
ORDER BY sc.gio_bat_dau;


-- ==========================================================
-- TRIGGERS
-- ==========================================================

-- Trigger 1 (definition cu): di chuyen logic vao trigger sync moi (line 535+)
-- Truoc co 2 ban CREATE OR REPLACE FUNCTION update_class_siso() khien ban
-- thu 2 override, va co 2 trigger cung goi 1 function -> moi reg INSERT/DELETE
-- chay UPDATE classes 2 lan (lang phi). Cong logic trang_thai=full/open vao
-- ham COUNT-based ben duoi de giu nguyen behavior.


-- Trigger 2: tu dong log audit khi co thao tac quan trong
-- Description text co dau tieng Viet + map ten bang -> ten Tieng Viet de user de doc
CREATE OR REPLACE FUNCTION log_audit_changes() RETURNS TRIGGER AS $$
DECLARE
    action_name VARCHAR(50);
    desc_text TEXT;
    table_label TEXT;
BEGIN
    -- Map table name -> friendly Vietnamese label
    table_label := CASE TG_TABLE_NAME
        WHEN 'registrations' THEN 'đăng ký khoá học'
        WHEN 'payments' THEN 'thanh toán'
        WHEN 'grades' THEN 'điểm'
        WHEN 'attendance' THEN 'điểm danh'
        ELSE TG_TABLE_NAME
    END;
    IF TG_OP = 'INSERT' THEN
        action_name := 'create_' || TG_TABLE_NAME;
        desc_text := 'Tạo mới ' || table_label;
    ELSIF TG_OP = 'UPDATE' THEN
        action_name := 'update_' || TG_TABLE_NAME;
        desc_text := 'Cập nhật ' || table_label;
    ELSIF TG_OP = 'DELETE' THEN
        action_name := 'delete_' || TG_TABLE_NAME;
        desc_text := 'Xoá ' || table_label;
    END IF;

    INSERT INTO audit_logs (action, target_type, target_id, description)
    VALUES (
        action_name,
        TG_TABLE_NAME,
        CASE
            WHEN TG_OP = 'DELETE' THEN COALESCE(OLD.id::text, 'unknown')
            ELSE COALESCE(NEW.id::text, 'unknown')
        END,
        desc_text
    );
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- gan trigger cho registrations va payments (nhung bang quan trong)
CREATE TRIGGER trg_audit_registrations
AFTER INSERT OR UPDATE OR DELETE ON registrations
FOR EACH ROW EXECUTE FUNCTION log_audit_changes();

CREATE TRIGGER trg_audit_payments
AFTER INSERT OR UPDATE OR DELETE ON payments
FOR EACH ROW EXECUTE FUNCTION log_audit_changes();


-- Trigger: tu dong sync classes.siso_hien_tai khi registrations thay doi
-- (truoc day siso static seed, drift voi actual paid count)
-- + Tu dong toggle trang_thai 'full' khi siso_hien_tai >= siso_max va 'open'
--   khi giam xuong (logic chuyen tu trigger cu trg_reg_siso da bi gop)
CREATE OR REPLACE FUNCTION update_class_siso() RETURNS TRIGGER AS $$
DECLARE
  target_lop VARCHAR(30);
  cur_siso INT;
  max_siso INT;
  cur_status VARCHAR(20);
BEGIN
  target_lop := COALESCE(NEW.lop_id, OLD.lop_id);
  IF target_lop IS NOT NULL THEN
    UPDATE classes SET siso_hien_tai = (
      SELECT COUNT(*) FROM registrations
       WHERE lop_id = target_lop
         AND trang_thai IN ('pending_payment', 'paid', 'completed')
    ) WHERE ma_lop = target_lop;
    -- Auto toggle trang_thai theo siso. Bo qua neu admin set 'closed' thu cong
    SELECT siso_hien_tai, siso_max, trang_thai
      INTO cur_siso, max_siso, cur_status
      FROM classes WHERE ma_lop = target_lop;
    IF cur_status != 'closed' THEN
      IF cur_siso >= max_siso AND cur_status = 'open' THEN
        UPDATE classes SET trang_thai = 'full' WHERE ma_lop = target_lop;
      ELSIF cur_siso < max_siso AND cur_status = 'full' THEN
        UPDATE classes SET trang_thai = 'open' WHERE ma_lop = target_lop;
      END IF;
    END IF;
  END IF;
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_class_siso
AFTER INSERT OR UPDATE OR DELETE ON registrations
FOR EACH ROW EXECUTE FUNCTION update_class_siso();


-- Trigger 3: check khong duoc dang ky vao lop da full
CREATE OR REPLACE FUNCTION check_class_not_full() RETURNS TRIGGER AS $$
DECLARE
    cur_siso INT;
    max_siso INT;
    cls_status VARCHAR(20);
BEGIN
    SELECT siso_hien_tai, siso_max, trang_thai
      INTO cur_siso, max_siso, cls_status
      FROM classes WHERE ma_lop = NEW.lop_id;

    IF cls_status = 'closed' THEN
        RAISE EXCEPTION 'Lop % da dong, khong the dang ky', NEW.lop_id;
    END IF;

    IF cur_siso >= max_siso THEN
        RAISE EXCEPTION 'Lop % da du siso (%/%)', NEW.lop_id, cur_siso, max_siso;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_class_full
BEFORE INSERT ON registrations
FOR EACH ROW EXECUTE FUNCTION check_class_not_full();
