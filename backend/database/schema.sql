-- EAUT - Trung tam dao tao ngoai khoa
-- Schema PostgreSQL, tao boi docker-entrypoint-initdb.d

-- xoa truoc neu ton tai (cho phep chay lai)
DROP TABLE IF EXISTS reviews CASCADE;
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS grades CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS registrations CASCADE;
DROP TABLE IF EXISTS classes CASCADE;
DROP TABLE IF EXISTS courses CASCADE;
DROP TABLE IF EXISTS admins CASCADE;
DROP TABLE IF EXISTS employees CASCADE;
DROP TABLE IF EXISTS teachers CASCADE;
DROP TABLE IF EXISTS students CASCADE;
DROP TABLE IF EXISTS users CASCADE;


-- ===== USERS (bang base cho 4 role) =====
CREATE TABLE users (
    id          SERIAL PRIMARY KEY,
    username    VARCHAR(50) UNIQUE NOT NULL,
    password    VARCHAR(255) NOT NULL,           -- sha256 hash
    role        VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'teacher', 'employee', 'student')),
    full_name   VARCHAR(100) NOT NULL,
    email       VARCHAR(100),
    sdt         VARCHAR(20),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active   BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_username ON users(username);


-- ===== STUDENTS (hoc vien) =====
CREATE TABLE students (
    user_id     INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    msv         VARCHAR(20) UNIQUE NOT NULL,
    ngaysinh    DATE,
    gioitinh    VARCHAR(10),
    diachi      VARCHAR(200)
);


-- ===== TEACHERS (giang vien) =====
CREATE TABLE teachers (
    user_id         INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    ma_gv           VARCHAR(20) UNIQUE NOT NULL,
    hoc_vi          VARCHAR(30),                  -- Phó giáo sư / Tiến sĩ / Thạc sĩ
    khoa            VARCHAR(100),
    chuyen_nganh    VARCHAR(100),
    tham_nien       INTEGER DEFAULT 0              -- so nam kinh nghiem
);


-- ===== EMPLOYEES (nhan vien) =====
CREATE TABLE employees (
    user_id         INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    ma_nv           VARCHAR(20) UNIQUE NOT NULL,
    chuc_vu         VARCHAR(50),
    phong_ban       VARCHAR(50),
    ngay_vao_lam    DATE
);


-- ===== ADMINS =====
CREATE TABLE admins (
    user_id     INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    ma_admin    VARCHAR(20) UNIQUE NOT NULL
);


-- ===== COURSES (mon hoc) =====
CREATE TABLE courses (
    ma_mon      VARCHAR(20) PRIMARY KEY,
    ten_mon     VARCHAR(100) NOT NULL,
    mo_ta       TEXT
);


-- ===== CLASSES (lop cu the cua 1 mon, moi lop co gia va GV rieng) =====
CREATE TABLE classes (
    ma_lop          VARCHAR(30) PRIMARY KEY,
    ma_mon          VARCHAR(20) NOT NULL REFERENCES courses(ma_mon) ON DELETE RESTRICT,
    gv_id           INTEGER REFERENCES teachers(user_id) ON DELETE SET NULL,
    lich            VARCHAR(100),                 -- "T3, T5 (7:00-9:30)"
    phong           VARCHAR(20),
    siso_max        INTEGER DEFAULT 40,
    siso_hien_tai   INTEGER DEFAULT 0,
    gia             NUMERIC(12, 0) NOT NULL,      -- VND, khong co phan thap phan
    trang_thai      VARCHAR(20) DEFAULT 'open' CHECK (trang_thai IN ('open', 'full', 'closed'))
);

CREATE INDEX idx_classes_mon ON classes(ma_mon);
CREATE INDEX idx_classes_gv ON classes(gv_id);


-- ===== REGISTRATIONS (dang ky hoc vien vao lop) =====
CREATE TABLE registrations (
    id              SERIAL PRIMARY KEY,
    hv_id           INTEGER NOT NULL REFERENCES students(user_id) ON DELETE CASCADE,
    lop_id          VARCHAR(30) NOT NULL REFERENCES classes(ma_lop) ON DELETE RESTRICT,
    nv_xu_ly        INTEGER REFERENCES employees(user_id) ON DELETE SET NULL,
    ngay_dk         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    trang_thai      VARCHAR(30) DEFAULT 'pending_payment'
                    CHECK (trang_thai IN ('pending_payment', 'paid', 'cancelled', 'completed')),
    UNIQUE (hv_id, lop_id)                        -- 1 HV chi dang ky 1 lop 1 lan
);

CREATE INDEX idx_reg_hv ON registrations(hv_id);
CREATE INDEX idx_reg_lop ON registrations(lop_id);
CREATE INDEX idx_reg_status ON registrations(trang_thai);


-- ===== PAYMENTS (thanh toan) =====
CREATE TABLE payments (
    id          SERIAL PRIMARY KEY,
    reg_id      INTEGER NOT NULL REFERENCES registrations(id) ON DELETE CASCADE,
    so_tien     NUMERIC(12, 0) NOT NULL,
    hinh_thuc   VARCHAR(30) NOT NULL,             -- Tien mat / Chuyen khoan / VNPay / Momo
    ngay_thu    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    nv_thu      INTEGER REFERENCES employees(user_id) ON DELETE SET NULL,
    ghi_chu     TEXT
);

CREATE INDEX idx_pay_reg ON payments(reg_id);


-- ===== GRADES (diem) =====
CREATE TABLE grades (
    hv_id       INTEGER NOT NULL REFERENCES students(user_id) ON DELETE CASCADE,
    lop_id      VARCHAR(30) NOT NULL REFERENCES classes(ma_lop) ON DELETE CASCADE,
    diem_qt     NUMERIC(4, 2) CHECK (diem_qt >= 0 AND diem_qt <= 10),
    diem_thi    NUMERIC(4, 2) CHECK (diem_thi >= 0 AND diem_thi <= 10),
    tong_ket    NUMERIC(4, 2) CHECK (tong_ket >= 0 AND tong_ket <= 10),
    xep_loai    VARCHAR(5),                       -- A+ / A / B+ / B / C+ / C / D / F
    gv_nhap     INTEGER REFERENCES teachers(user_id) ON DELETE SET NULL,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (hv_id, lop_id)
);


-- ===== NOTIFICATIONS (thong bao tu admin hoac GV) =====
CREATE TABLE notifications (
    id          SERIAL PRIMARY KEY,
    tu_id       INTEGER REFERENCES users(id) ON DELETE SET NULL,
    den_lop     VARCHAR(30) REFERENCES classes(ma_lop) ON DELETE CASCADE,  -- NULL = gui tat ca
    tieu_de     VARCHAR(200) NOT NULL,
    noi_dung    TEXT NOT NULL,
    loai        VARCHAR(20) DEFAULT 'info' CHECK (loai IN ('info', 'warning', 'urgent')),
    ngay_tao    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notif_lop ON notifications(den_lop);
CREATE INDEX idx_notif_ngay ON notifications(ngay_tao DESC);


-- ===== REVIEWS (danh gia GV tu HV) =====
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


-- ===== VIEW: thong tin day du lop + GV + mon =====
CREATE OR REPLACE VIEW v_class_detail AS
SELECT
    c.ma_lop,
    c.ma_mon,
    co.ten_mon,
    c.gv_id,
    u.full_name AS ten_gv,
    c.lich,
    c.phong,
    c.siso_max,
    c.siso_hien_tai,
    c.gia,
    c.trang_thai
FROM classes c
LEFT JOIN courses co ON c.ma_mon = co.ma_mon
LEFT JOIN teachers t ON c.gv_id = t.user_id
LEFT JOIN users u ON t.user_id = u.id;


-- ===== TRIGGER: tu dong update siso khi co dang ky moi =====
CREATE OR REPLACE FUNCTION update_class_siso() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE classes SET siso_hien_tai = siso_hien_tai + 1 WHERE ma_lop = NEW.lop_id;
        -- check day
        UPDATE classes SET trang_thai = 'full'
         WHERE ma_lop = NEW.lop_id AND siso_hien_tai >= siso_max;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE classes SET siso_hien_tai = GREATEST(siso_hien_tai - 1, 0) WHERE ma_lop = OLD.lop_id;
        UPDATE classes SET trang_thai = 'open'
         WHERE ma_lop = OLD.lop_id AND siso_hien_tai < siso_max AND trang_thai = 'full';
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_reg_siso
AFTER INSERT OR DELETE ON registrations
FOR EACH ROW EXECUTE FUNCTION update_class_siso();
