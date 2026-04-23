-- Seed data mock cho EAUT - chay sau schema.sql
-- 18 bang: users, students, teachers, employees, admins, courses, semesters,
--   classes, registrations, payments, grades, notifications, reviews,
--   curriculum, audit_logs, schedules, exam_schedules, attendance

-- tat audit trigger khi seed (tranh log noise)
ALTER TABLE registrations DISABLE TRIGGER trg_audit_registrations;
ALTER TABLE payments       DISABLE TRIGGER trg_audit_payments;


-- ==========================================================
-- USERS (22 nguoi)
-- ==========================================================
INSERT INTO users (id, username, password, role, full_name, email, sdt) VALUES
  (1, 'admin',    'passadmin', 'admin',    'Quan Tri Vien',        'admin@eaut.edu.vn',    '0901111111'),
  (2, 'teacher',  'passtea',   'teacher',  'Nguyen Duc Thien',     'thien@eaut.edu.vn',    '0901234567'),
  (3, 'employee', 'passemp',   'employee', 'Tran Thu Huong',       'huongtt@eaut.edu.vn',  '0987654321'),
  (4, 'user',     'passuser',  'student',  'Dao Viet Quang Huy',   'quanghuy@sv.eaut.edu.vn', '0912345678'),
  (5, 'gv_lec',   'passtea',   'teacher',  'Le Trung Thuc',        'thuc@eaut.edu.vn',     '0901234568'),
  (6, 'gv_nta',   'passtea',   'teacher',  'Ngo Thao Anh',         'anh@eaut.edu.vn',      '0901234569'),
  (7, 'gv_ltc',   'passtea',   'teacher',  'Le Thi C',             'lec@eaut.edu.vn',      '0901234570'),
  (8, 'gv_pvk',   'passtea',   'teacher',  'Pham Van K',           'pvk@eaut.edu.vn',      '0901234571'),
  (9, 'gv_pvd',   'passtea',   'teacher',  'Pham Van D',           'pvd@eaut.edu.vn',      '0901234572'),
  (10,'gv_hmt',   'passtea',   'teacher',  'Hoang Minh Tuan',      'hmt@eaut.edu.vn',      '0901234573'),
  (11,'gv_nte',   'passtea',   'teacher',  'Nguyen Thi E',         'nte@eaut.edu.vn',      '0901234574'),
  (12,'gv_lvm',   'passtea',   'teacher',  'Le Van M',             'lvm@eaut.edu.vn',      '0901234575'),
  (13,'hv002',    'passuser',  'student',  'Tran Thi Bich',        'bich@sv.eaut.edu.vn',  '0923456789'),
  (14,'hv003',    'passuser',  'student',  'Le Van Cuong',         'cuong@sv.eaut.edu.vn', '0934567890'),
  (15,'hv010',    'passuser',  'student',  'Pham Thi Dung',        'dung@sv.eaut.edu.vn',  '0945678901'),
  (16,'hv015',    'passuser',  'student',  'Hoang Van Em',         'em@sv.eaut.edu.vn',    '0956789012'),
  (17,'hv020',    'passuser',  'student',  'Vu Thi Phuong',        'phuong@sv.eaut.edu.vn','0967890123'),
  (18,'hv025',    'passuser',  'student',  'Nguyen Thanh Giang',   'giang@sv.eaut.edu.vn', '0978901234'),
  (19,'hv030',    'passuser',  'student',  'Bui Thi Hong',         'hong@sv.eaut.edu.vn',  '0989012345'),
  (20,'nv002',    'passemp',   'employee', 'Le Minh Duc',          'ducm@eaut.edu.vn',     '0987654322'),
  (21,'nv003',    'passemp',   'employee', 'Pham Quynh Anh',       'anhpq@eaut.edu.vn',    '0987654323'),
  (22,'nv004',    'passemp',   'employee', 'Nguyen Hoai Linh',     'linh@eaut.edu.vn',     '0987654324');

SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));


-- ===== ADMINS / TEACHERS / EMPLOYEES / STUDENTS =====
INSERT INTO admins (user_id, ma_admin) VALUES (1, 'AD001');

INSERT INTO teachers (user_id, ma_gv, hoc_vi, khoa, chuyen_nganh, tham_nien) VALUES
  (2,  'GV001', 'Tien si',     'CNTT', 'Cong nghe thong tin', 10),
  (5,  'GV002', 'Thac si',     'CNTT', 'Ky thuat phan mem',   6),
  (6,  'GV003', 'Tien si',     'CNTT', 'Tri tue nhan tao',    8),
  (7,  'GV004', 'Thac si',     'CNTT', 'Co so du lieu',       7),
  (8,  'GV005', 'Thac si',     'CNTT', 'He thong thong tin',  5),
  (9,  'GV006', 'Thac si',     'CNTT', 'Mang may tinh',       6),
  (10, 'GV007', 'Tien si',     'CNTT', 'Tri tue nhan tao',    9),
  (11, 'GV008', 'Pho giao su', 'Toan', 'Toan roi rac',        15),
  (12, 'GV009', 'Tien si',     'Toan', 'Toan ung dung',       12);

INSERT INTO employees (user_id, ma_nv, chuc_vu, phong_ban, ngay_vao_lam) VALUES
  (3,  'NV001', 'Nhan vien dang ky',   'Phong dao tao', '2022-03-15'),
  (20, 'NV002', 'Nhan vien thu ngan',  'Phong tai chinh','2023-01-10'),
  (21, 'NV003', 'Nhan vien dang ky',   'Phong dao tao', '2023-06-01'),
  (22, 'NV004', 'Quan ly',             'Phong dao tao', '2021-09-20');

INSERT INTO students (user_id, msv, ngaysinh, gioitinh, diachi) VALUES
  (4,  'HV2024001', '2004-03-15', 'Nam', 'Da Nang'),
  (13, 'HV2024002', '2003-06-20', 'Nu',  'Ha Noi'),
  (14, 'HV2024003', '2004-11-08', 'Nam', 'Hai Phong'),
  (15, 'HV2024010', '2003-07-25', 'Nu',  'Quang Ninh'),
  (16, 'HV2024015', '2004-12-12', 'Nam', 'Nam Dinh'),
  (17, 'HV2024020', '2003-04-30', 'Nu',  'Thanh Hoa'),
  (18, 'HV2024025', '2004-09-05', 'Nam', 'Ninh Binh'),
  (19, 'HV2024030', '2003-02-18', 'Nu',  'Thai Binh');


-- ==========================================================
-- SEMESTERS (4 hoc ky - MOI)
-- ==========================================================
INSERT INTO semesters (id, ten, nam_hoc, bat_dau, ket_thuc, trang_thai) VALUES
  ('HK2-2526', 'Hoc ky 2', '2025-2026', '2026-01-01', '2026-06-30', 'open'),
  ('HK1-2526', 'Hoc ky 1', '2025-2026', '2025-08-01', '2025-12-31', 'closed'),
  ('HK2-2425', 'Hoc ky 2', '2024-2025', '2025-01-01', '2025-06-30', 'closed'),
  ('HK1-2425', 'Hoc ky 1', '2024-2025', '2024-08-01', '2024-12-31', 'closed');


-- ===== COURSES =====
INSERT INTO courses (ma_mon, ten_mon, mo_ta) VALUES
  ('IT001', 'Lap trinh Python',    'Khoa hoc Python co ban den nang cao'),
  ('IT002', 'Co so du lieu',       'SQL, thiet ke database'),
  ('IT003', 'Mang may tinh',       'TCP/IP, routing, cau hinh mang'),
  ('IT004', 'Tri tue nhan tao',    'Machine learning, deep learning'),
  ('IT005', 'Phat trien web',      'HTML, CSS, JavaScript, React'),
  ('IT006', 'He dieu hanh',        'Linux, Windows, quan ly process'),
  ('MA001', 'Toan roi rac',        'Logic, tap hop, do thi, to hop'),
  ('MA002', 'Xac suat thong ke',   'Thong ke ung dung'),
  ('EN001', 'Tieng Anh chuyen nganh', 'Tieng Anh IT trinh do B1');


-- ==========================================================
-- CLASSES (co semester_id)
-- ==========================================================
INSERT INTO classes (ma_lop, ma_mon, gv_id, semester_id, lich, phong, siso_max, siso_hien_tai, gia, trang_thai, ngay_bat_dau, ngay_ket_thuc, so_buoi) VALUES
  ('IT001-A', 'IT001', 2,  'HK2-2526', 'T3, T5 (7:00-9:30)',    'P.A301', 40, 35, 2500000, 'open',   '2026-02-10', '2026-05-28', 24),
  ('IT001-B', 'IT001', 5,  'HK2-2526', 'T4, T6 (13:00-15:30)',  'P.B205', 40, 28, 1800000, 'open',   '2026-02-11', '2026-05-29', 24),
  ('IT001-C', 'IT001', 6,  'HK2-2526', 'T2, T7 (15:40-18:10)',  'P.C102', 35, 35, 2000000, 'full',   '2026-02-09', '2026-05-30', 24),
  ('IT002-A', 'IT002', 7,  'HK2-2526', 'T5 (7:00-9:30)',        'P.A202', 40, 35, 2200000, 'open',   '2026-02-12', '2026-05-28', 16),
  ('IT002-B', 'IT002', 8,  'HK2-2526', 'T3 (13:00-15:30)',      'P.B108', 40, 22, 1800000, 'open',   '2026-02-10', '2026-05-26', 16),
  ('IT003-A', 'IT003', 9,  'HK2-2526', 'T6 (7:00-9:30)',        'P.A105', 30, 18, 2000000, 'open',   '2026-02-13', '2026-05-29', 16),
  ('IT004-A', 'IT004', 2,  'HK2-2526', 'T4 (13:00-15:30)',      'P.A301', 40, 28, 2800000, 'open',   '2026-02-11', '2026-05-27', 20),
  ('IT004-B', 'IT004', 10, 'HK2-2526', 'T5 (13:00-15:30)',      'P.B301', 35, 20, 2200000, 'open',   '2026-02-12', '2026-05-28', 20),
  ('MA001-A', 'MA001', 11, 'HK2-2526', 'T2 (9:30-12:00)',       'P.A203', 40, 30, 1500000, 'open',   '2026-02-09', '2026-05-25', 15),
  ('MA001-B', 'MA001', 12, 'HK2-2526', 'T4 (9:30-12:00)',       'P.B204', 40, 25, 1200000, 'open',   '2026-02-11', '2026-05-27', 15),
  -- lop cua HK1-2526 (da ket thuc)
  ('IT001-P1', 'IT001', 2, 'HK1-2526', 'T3, T5 (7:00-9:30)',    'P.A301', 40, 40, 2500000, 'closed', '2025-09-01', '2025-12-20', 24),
  ('MA001-P1', 'MA001', 11,'HK1-2526', 'T2 (9:30-12:00)',       'P.A203', 40, 38, 1500000, 'closed', '2025-09-02', '2025-12-15', 15);


-- ==========================================================
-- REGISTRATIONS
-- ==========================================================
-- tat trigger siso + audit khi seed
ALTER TABLE registrations DISABLE TRIGGER trg_reg_siso;
ALTER TABLE registrations DISABLE TRIGGER trg_check_class_full;

INSERT INTO registrations (id, hv_id, lop_id, nv_xu_ly, ngay_dk, trang_thai) VALUES
  (1, 4,  'IT001-A', 3, '2026-04-10 08:30:00', 'paid'),
  (2, 4,  'IT004-A', 3, '2026-04-18 10:15:00', 'pending_payment'),
  (3, 13, 'IT001-A', 3, '2026-04-11 09:00:00', 'paid'),
  (4, 13, 'IT002-A', 20,'2026-04-18 10:30:00', 'pending_payment'),
  (5, 14, 'IT001-B', 3, '2026-04-12 14:00:00', 'paid'),
  (6, 14, 'IT004-B', 3, '2026-04-16 11:00:00', 'pending_payment'),
  (7, 15, 'IT001-A', 21,'2026-04-13 09:30:00', 'paid'),
  (8, 15, 'MA001-A', 21,'2026-04-17 16:00:00', 'paid'),
  (9, 16, 'IT001-A', 3, '2026-04-14 10:00:00', 'paid'),
  (10,17, 'IT004-A', 20,'2026-04-15 13:00:00', 'paid'),
  (11,18, 'IT001-B', 3, '2026-04-17 09:00:00', 'paid'),
  (12,19, 'IT001-C', 3, '2026-04-16 14:30:00', 'paid'),
  -- dang ky cho lop HK1-2526 (da hoan thanh)
  (13, 4, 'IT001-P1', 3, '2025-08-25 10:00:00', 'completed'),
  (14,13, 'IT001-P1', 3, '2025-08-26 09:30:00', 'completed'),
  (15,14, 'MA001-P1', 3, '2025-08-25 14:00:00', 'completed');

SELECT setval('registrations_id_seq', (SELECT MAX(id) FROM registrations));

ALTER TABLE registrations ENABLE TRIGGER trg_reg_siso;
ALTER TABLE registrations ENABLE TRIGGER trg_check_class_full;


-- ===== PAYMENTS (so_bien_lai moi) =====
INSERT INTO payments (reg_id, so_tien, hinh_thuc, ngay_thu, nv_thu, ghi_chu, so_bien_lai) VALUES
  (1,  2500000, 'Tien mat',    '2026-04-10 08:45:00', 3,  'Dong du',     'BL20260410084500'),
  (3,  2500000, 'Chuyen khoan','2026-04-11 09:15:00', 3,  NULL,          'BL20260411091500'),
  (5,  1800000, 'Tien mat',    '2026-04-12 14:15:00', 3,  NULL,          'BL20260412141500'),
  (7,  2500000, 'VNPay',       '2026-04-13 09:45:00', 21, NULL,          'BL20260413094500'),
  (8,  1500000, 'Chuyen khoan','2026-04-17 16:20:00', 21, NULL,          'BL20260417162000'),
  (9,  2500000, 'Tien mat',    '2026-04-14 10:30:00', 3,  NULL,          'BL20260414103000'),
  (10, 2800000, 'Momo',        '2026-04-15 13:20:00', 20, NULL,          'BL20260415132000'),
  (11, 1800000, 'Tien mat',    '2026-04-17 09:30:00', 3,  NULL,          'BL20260417093000'),
  (12, 2000000, 'Chuyen khoan','2026-04-16 15:00:00', 3,  NULL,          'BL20260416150000'),
  -- thanh toan cho lop da hoan thanh HK1-2526
  (13, 2500000, 'Tien mat',    '2025-08-25 10:30:00', 3,  'Da dong du',  'BL20250825103000'),
  (14, 2500000, 'Chuyen khoan','2025-08-26 10:00:00', 3,  NULL,          'BL20250826100000'),
  (15, 1500000, 'Tien mat',    '2025-08-25 14:20:00', 3,  NULL,          'BL20250825142000');


-- ===== GRADES =====
INSERT INTO grades (hv_id, lop_id, diem_qt, diem_thi, tong_ket, xep_loai, gv_nhap) VALUES
  (4,  'IT001-A', 8.5, 7.5, 7.8, 'B+', 2),
  (13, 'IT001-A', 9.0, 8.5, 8.7, 'A',  2),
  (14, 'IT001-B', 7.0, 6.5, 6.7, 'C+', 5),
  (15, 'IT001-A', 8.0, 7.5, 7.7, 'B',  2),
  (16, 'IT001-A', 9.5, 9.0, 9.2, 'A+', 2),
  -- diem cua HK1-2526 da co san
  (4,  'IT001-P1', 8.0, 8.5, 8.4, 'B+', 2),
  (13, 'IT001-P1', 9.5, 9.0, 9.2, 'A+', 2),
  (14, 'MA001-P1', 7.5, 7.0, 7.2, 'B',  11);


-- ===== NOTIFICATIONS =====
INSERT INTO notifications (tu_id, den_lop, tieu_de, noi_dung, loai, ngay_tao) VALUES
  (1, NULL,       'Lich khai giang thang 5',   'Trung tam khai giang cac lop khoa moi tu 05/05/2026.',   'info',    '2026-04-15 10:00:00'),
  (1, NULL,       'Nghi le 30/4 - 1/5',         'Trung tam nghi tu 30/4 den het 3/5/2026.',                'info',    '2026-04-05 09:00:00'),
  (2, 'IT001-A',  'Nghi hoc ngay 20/04',        'Thay ban hop nen tam nghi, hoc bu thu 7.',                'warning', '2026-04-17 15:00:00'),
  (2, 'IT004-A',  'Bai tap tuan 8',             'Nop bai tap truoc thu 6 tuan sau.',                       'info',    '2026-04-16 20:00:00'),
  (1, NULL,       'Uu dai 10% hoc phi',         'Giam 10% cho HV dang ky truoc 30/04/2026.',               'info',    '2026-03-28 08:00:00');


-- ===== REVIEWS =====
INSERT INTO reviews (hv_id, gv_id, lop_id, diem, nhan_xet) VALUES
  (13, 2,  'IT001-A', 5, 'Thay day rat nhiet tinh, de hieu'),
  (14, 5,  'IT001-B', 4, 'Thay on, bai tap hop ly'),
  (15, 2,  'IT001-A', 5, 'Rat tuyet voi'),
  (16, 2,  'IT001-A', 5, 'Thay gioi, giang de hieu'),
  (17, 2,  'IT004-A', 4, 'Bai hoc bo ich');


-- ==========================================================
-- CURRICULUM (khung chuong trinh dao tao CNTT) - MOI
-- ==========================================================
INSERT INTO curriculum (ma_mon, tin_chi, loai, hoc_ky_de_nghi, mon_tien_quyet, nganh) VALUES
  ('IT001', 3, 'Bat buoc', 'HK1', NULL,              'CNTT'),
  ('MA001', 3, 'Bat buoc', 'HK1', NULL,              'CNTT'),
  ('EN001', 3, 'Dai cuong','HK1', NULL,              'CNTT'),
  ('IT002', 3, 'Bat buoc', 'HK2', 'IT001',           'CNTT'),
  ('MA002', 3, 'Bat buoc', 'HK2', 'MA001',           'CNTT'),
  ('IT003', 3, 'Bat buoc', 'HK3', 'IT002',           'CNTT'),
  ('IT004', 3, 'Bat buoc', 'HK3', 'IT002, MA002',    'CNTT'),
  ('IT005', 3, 'Tu chon',  'HK4', 'IT002',           'CNTT'),
  ('IT006', 3, 'Bat buoc', 'HK4', 'IT003',           'CNTT'),
  -- cho nganh Toan
  ('MA001', 3, 'Bat buoc', 'HK1', NULL,              'Toan'),
  ('MA002', 3, 'Bat buoc', 'HK2', 'MA001',           'Toan'),
  ('EN001', 3, 'Dai cuong','HK1', NULL,              'Toan'),
  -- cho nganh Ngoai ngu
  ('EN001', 3, 'Bat buoc', 'HK1', NULL,              'Ngoai ngu'),
  ('MA001', 2, 'Dai cuong','HK2', NULL,              'Ngoai ngu');


-- ==========================================================
-- SCHEDULES (lich hoc buoi cu the - tuan nay va tuan sau) - MOI
-- ==========================================================
-- Tuan nay (17/04/2026 - thu 6) + 2 tuan toi
INSERT INTO schedules (lop_id, ngay, thu, gio_bat_dau, gio_ket_thuc, phong, buoi_so, noi_dung) VALUES
  -- IT001-A: T3, T5 (7:00-9:30)
  ('IT001-A', '2026-04-14', 3, '07:00', '09:30', 'P.A301', 12, 'Dictionary va Set trong Python'),
  ('IT001-A', '2026-04-16', 5, '07:00', '09:30', 'P.A301', 13, 'File I/O va Exception'),
  ('IT001-A', '2026-04-21', 3, '07:00', '09:30', 'P.A301', 14, 'OOP co ban - Class va Object'),
  ('IT001-A', '2026-04-23', 5, '07:00', '09:30', 'P.A301', 15, 'OOP nang cao - Inheritance'),
  ('IT001-A', '2026-04-28', 3, '07:00', '09:30', 'P.A301', 16, 'Modules va Packages'),
  -- IT001-B: T4, T6 (13:00-15:30)
  ('IT001-B', '2026-04-15', 4, '13:00', '15:30', 'P.B205', 12, 'Cau truc du lieu trong Python'),
  ('IT001-B', '2026-04-17', 6, '13:00', '15:30', 'P.B205', 13, 'File handling'),
  ('IT001-B', '2026-04-22', 4, '13:00', '15:30', 'P.B205', 14, 'OOP Foundations'),
  -- IT001-C: T2, T7 (15:40-18:10)
  ('IT001-C', '2026-04-20', 2, '15:40', '18:10', 'P.C102', 12, 'List comprehension'),
  ('IT001-C', '2026-04-25', 7, '15:40', '18:10', 'P.C102', 13, 'Error handling'),
  -- IT002-A: T5 (7:00-9:30)
  ('IT002-A', '2026-04-16', 5, '07:00', '09:30', 'P.A202', 8,  'Normalization 3NF'),
  ('IT002-A', '2026-04-23', 5, '07:00', '09:30', 'P.A202', 9,  'Stored Procedures'),
  -- IT003-A: T6 (7:00-9:30)
  ('IT003-A', '2026-04-17', 6, '07:00', '09:30', 'P.A105', 8,  'Subnetting'),
  ('IT003-A', '2026-04-24', 6, '07:00', '09:30', 'P.A105', 9,  'Routing protocols'),
  -- IT004-A: T4 (13:00-15:30)
  ('IT004-A', '2026-04-15', 4, '13:00', '15:30', 'P.A301', 7,  'Neural Networks basics'),
  ('IT004-A', '2026-04-22', 4, '13:00', '15:30', 'P.A301', 8,  'Backpropagation'),
  -- MA001-A: T2 (9:30-12:00)
  ('MA001-A', '2026-04-20', 2, '09:30', '12:00', 'P.A203', 10, 'Do thi va cay'),
  ('MA001-A', '2026-04-27', 2, '09:30', '12:00', 'P.A203', 11, 'Thuat toan do thi');


-- ==========================================================
-- EXAM_SCHEDULES (lich thi cuoi ky HK2-2526) - MOI
-- ==========================================================
INSERT INTO exam_schedules (lop_id, semester_id, ngay_thi, ca_thi, gio_bat_dau, gio_ket_thuc, phong, hinh_thuc, so_cau, thoi_gian_phut) VALUES
  ('IT001-A', 'HK2-2526', '2026-06-20', 'Ca 1 (07:30-09:00)', '07:30', '09:00', 'P.A301', 'Trac nghiem', 40, 90),
  ('IT001-B', 'HK2-2526', '2026-06-20', 'Ca 2 (09:30-11:00)', '09:30', '11:00', 'P.A301', 'Trac nghiem', 40, 90),
  ('IT001-C', 'HK2-2526', '2026-06-21', 'Ca 1 (07:30-09:00)', '07:30', '09:00', 'P.C102', 'Trac nghiem', 40, 90),
  ('IT002-A', 'HK2-2526', '2026-06-22', 'Ca 2 (09:30-11:00)', '09:30', '11:00', 'P.B205', 'Tu luan',     6,  120),
  ('IT002-B', 'HK2-2526', '2026-06-22', 'Ca 3 (13:30-15:00)', '13:30', '15:00', 'P.B205', 'Tu luan',     6,  120),
  ('IT003-A', 'HK2-2526', '2026-06-24', 'Ca 1 (07:30-09:00)', '07:30', '09:00', 'P.A105', 'Thuc hanh',   NULL, 120),
  ('IT004-A', 'HK2-2526', '2026-06-25', 'Ca 2 (09:30-11:00)', '09:30', '11:00', 'P.A301', 'Tu luan',     5,  120),
  ('IT004-B', 'HK2-2526', '2026-06-25', 'Ca 3 (13:30-15:00)', '13:30', '15:00', 'P.B301', 'Tu luan',     5,  120),
  ('MA001-A', 'HK2-2526', '2026-06-18', 'Ca 1 (07:30-09:00)', '07:30', '09:00', 'P.A203', 'Tu luan',     8,  120),
  ('MA001-B', 'HK2-2526', '2026-06-18', 'Ca 2 (09:30-11:00)', '09:30', '11:00', 'P.B204', 'Tu luan',     8,  120);


-- ==========================================================
-- ATTENDANCE (diem danh - seed it) - MOI
-- ==========================================================
-- lay id cua buoi thu 12 lop IT001-A (schedule dau tien inserted)
INSERT INTO attendance (schedule_id, hv_id, trang_thai, gio_vao, recorded_by) VALUES
  (1, 4,  'present', '06:58', 2),
  (1, 13, 'present', '07:02', 2),
  (1, 15, 'present', '06:55', 2),
  (1, 16, 'late',    '07:15', 2),
  (1, 4,  'present', '06:58', 2) ON CONFLICT (schedule_id, hv_id) DO NOTHING;

-- buoi 13 IT001-A (schedule id=2)
INSERT INTO attendance (schedule_id, hv_id, trang_thai, gio_vao, recorded_by) VALUES
  (2, 4,  'present', '07:00', 2),
  (2, 13, 'absent',  NULL,    2),
  (2, 15, 'present', '06:59', 2),
  (2, 16, 'present', '07:05', 2) ON CONFLICT (schedule_id, hv_id) DO NOTHING;


-- ==========================================================
-- AUDIT_LOGS (vai log mau) - MOI
-- ==========================================================
INSERT INTO audit_logs (user_id, username, role, action, target_type, target_id, description, ip_address, created_at) VALUES
  (1,  'admin',    'admin',    'login',            NULL,            NULL,  'Admin dang nhap thanh cong',                       '192.168.1.10', '2026-04-17 08:12:34'),
  (1,  'admin',    'admin',    'open_semester',    'semesters',     'HK2-2526', 'Mo dang ky HK2-2526',                         '192.168.1.10', '2026-04-17 08:15:02'),
  (4,  'user',     'student',  'login',            NULL,            NULL,  'Hoc vien dang nhap thanh cong',                    '10.0.0.55',    '2026-04-17 08:30:11'),
  (4,  'user',     'student',  'create_registration','registrations','2',   'HV dang ky lop IT004-A',                           '10.0.0.55',    '2026-04-17 08:31:45'),
  (13, 'hv002',    'student',  'login',            NULL,            NULL,  'Hoc vien dang nhap thanh cong',                    '10.0.0.87',    '2026-04-17 08:45:30'),
  (13, 'hv002',    'student',  'create_registration','registrations','4',   'HV dang ky lop IT002-A',                           '10.0.0.87',    '2026-04-17 08:46:12'),
  (NULL,'hv003',   'student',  'login_failed',     NULL,            NULL,  'Dang nhap that bai (sai mat khau)',                '10.0.0.42',    '2026-04-17 09:00:05'),
  (NULL,'hv003',   'student',  'login_failed',     NULL,            NULL,  'Dang nhap that bai (sai mat khau)',                '10.0.0.42',    '2026-04-17 09:00:15'),
  (NULL,'hv003',   'student',  'account_locked',   'users',         '14',  'Khoa tai khoan 15 phut (3 lan sai mat khau)',      '10.0.0.42',    '2026-04-17 09:00:25'),
  (1,  'admin',    'admin',    'update_class',     'classes',       'IT001-A', 'Sua si so IT001-A tu 35 -> 40',                '192.168.1.10', '2026-04-17 09:15:30'),
  (3,  'employee', 'employee', 'create_payment',   'payments',      '7',   'Thu hoc phi VNPay 2.500.000d cho HV HV2024010',    '192.168.1.20', '2026-04-13 09:45:00'),
  (2,  'teacher',  'teacher',  'update_grade',     'grades',        NULL,  'Cap nhat diem lop IT001-A',                        '192.168.1.15', '2026-04-16 14:00:00');


-- ==========================================================
-- bat lai trigger audit sau khi seed xong
-- ==========================================================
ALTER TABLE registrations ENABLE TRIGGER trg_audit_registrations;
ALTER TABLE payments      ENABLE TRIGGER trg_audit_payments;
