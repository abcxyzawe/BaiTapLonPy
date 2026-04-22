-- Seed data mock cho EAUT - chay sau schema.sql
-- password tat ca deu la sha256 cua cac chuoi: passuser, passadmin, passtea, passemp

-- ===== USERS =====
-- password = passuser -> sha256: 6f2f62d5b2a3c3f3c8e4c4b2a7e1f8d5c6e3f2a1b9d7c5e8f0a3b6d9c2e5f8a1
-- Nhung cho don gian, minh seed plain text truoc, se hash sau qua Python
INSERT INTO users (id, username, password, role, full_name, email, sdt) VALUES
  (1, 'admin',    'passadmin', 'admin',    'Quan Tri Vien',        'admin@eaut.edu.vn',    '0901111111'),
  (2, 'teacher',  'passtea',   'teacher',  'Nguyen Duc Thien',     'thien@eaut.edu.vn',    '0901234567'),
  (3, 'employee', 'passemp',   'employee', 'Tran Thu Huong',       'huongtt@eaut.edu.vn',  '0987654321'),
  (4, 'user',     'passuser',  'student',  'Dao Viet Quang Huy',   'quanghuy@sv.eaut.edu.vn', '0912345678'),
  -- giang vien them
  (5, 'gv_lec',   'passtea',   'teacher',  'Le Trung Thuc',        'thuc@eaut.edu.vn',     '0901234568'),
  (6, 'gv_nta',   'passtea',   'teacher',  'Ngo Thao Anh',         'anh@eaut.edu.vn',      '0901234569'),
  (7, 'gv_ltc',   'passtea',   'teacher',  'Le Thi C',             'lec@eaut.edu.vn',      '0901234570'),
  (8, 'gv_pvk',   'passtea',   'teacher',  'Pham Van K',           'pvk@eaut.edu.vn',      '0901234571'),
  (9, 'gv_pvd',   'passtea',   'teacher',  'Pham Van D',           'pvd@eaut.edu.vn',      '0901234572'),
  (10,'gv_hmt',   'passtea',   'teacher',  'Hoang Minh Tuan',      'hmt@eaut.edu.vn',      '0901234573'),
  (11,'gv_nte',   'passtea',   'teacher',  'Nguyen Thi E',         'nte@eaut.edu.vn',      '0901234574'),
  (12,'gv_lvm',   'passtea',   'teacher',  'Le Van M',             'lvm@eaut.edu.vn',      '0901234575'),
  -- hoc vien them
  (13,'hv002', 'passuser', 'student', 'Tran Thi Bich',       'bich@sv.eaut.edu.vn',    '0923456789'),
  (14,'hv003', 'passuser', 'student', 'Le Van Cuong',        'cuong@sv.eaut.edu.vn',   '0934567890'),
  (15,'hv010', 'passuser', 'student', 'Pham Thi Dung',       'dung@sv.eaut.edu.vn',    '0945678901'),
  (16,'hv015', 'passuser', 'student', 'Hoang Van Em',        'em@sv.eaut.edu.vn',      '0956789012'),
  (17,'hv020', 'passuser', 'student', 'Vu Thi Phuong',       'phuong@sv.eaut.edu.vn',  '0967890123'),
  (18,'hv025', 'passuser', 'student', 'Nguyen Thanh Giang',  'giang@sv.eaut.edu.vn',   '0978901234'),
  (19,'hv030', 'passuser', 'student', 'Bui Thi Hong',        'hong@sv.eaut.edu.vn',    '0989012345'),
  -- nhan vien them
  (20,'nv002', 'passemp', 'employee', 'Le Minh Duc',         'ducm@eaut.edu.vn',       '0987654322'),
  (21,'nv003', 'passemp', 'employee', 'Pham Quynh Anh',      'anhpq@eaut.edu.vn',      '0987654323'),
  (22,'nv004', 'passemp', 'employee', 'Nguyen Hoai Linh',    'linh@eaut.edu.vn',       '0987654324');

-- reset sequence vi da insert id thu cong
SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));


-- ===== ADMINS =====
INSERT INTO admins (user_id, ma_admin) VALUES
  (1, 'AD001');


-- ===== TEACHERS =====
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


-- ===== EMPLOYEES =====
INSERT INTO employees (user_id, ma_nv, chuc_vu, phong_ban, ngay_vao_lam) VALUES
  (3,  'NV001', 'Nhan vien dang ky',   'Phong dao tao', '2022-03-15'),
  (20, 'NV002', 'Nhan vien thu ngan',  'Phong tai chinh','2023-01-10'),
  (21, 'NV003', 'Nhan vien dang ky',   'Phong dao tao', '2023-06-01'),
  (22, 'NV004', 'Quan ly',             'Phong dao tao', '2021-09-20');


-- ===== STUDENTS =====
INSERT INTO students (user_id, msv, ngaysinh, gioitinh, diachi) VALUES
  (4,  'HV2024001', '2004-03-15', 'Nam', 'Da Nang'),
  (13, 'HV2024002', '2003-06-20', 'Nu',  'Ha Noi'),
  (14, 'HV2024003', '2004-11-08', 'Nam', 'Hai Phong'),
  (15, 'HV2024010', '2003-07-25', 'Nu',  'Quang Ninh'),
  (16, 'HV2024015', '2004-12-12', 'Nam', 'Nam Dinh'),
  (17, 'HV2024020', '2003-04-30', 'Nu',  'Thanh Hoa'),
  (18, 'HV2024025', '2004-09-05', 'Nam', 'Ninh Binh'),
  (19, 'HV2024030', '2003-02-18', 'Nu',  'Thai Binh');


-- ===== COURSES =====
INSERT INTO courses (ma_mon, ten_mon, mo_ta) VALUES
  ('IT001', 'Lap trinh Python',   'Khoa hoc Python co ban den nang cao'),
  ('IT002', 'Co so du lieu',      'SQL, thiet ke database'),
  ('IT003', 'Mang may tinh',      'TCP/IP, routing, cau hinh mang'),
  ('IT004', 'Tri tue nhan tao',   'Machine learning, deep learning'),
  ('MA001', 'Toan roi rac',       'Logic, tap hop, do thi, to hop');


-- ===== CLASSES =====
INSERT INTO classes (ma_lop, ma_mon, gv_id, lich, phong, siso_max, siso_hien_tai, gia, trang_thai) VALUES
  ('IT001-A', 'IT001', 2,  'T3, T5 (7:00-9:30)',    'P.A301', 40, 35, 2500000, 'open'),
  ('IT001-B', 'IT001', 5,  'T4, T6 (13:00-15:30)',  'P.B205', 40, 28, 1800000, 'open'),
  ('IT001-C', 'IT001', 6,  'T2, T7 (15:40-18:10)',  'P.C102', 35, 35, 2000000, 'full'),
  ('IT002-A', 'IT002', 7,  'T5 (7:00-9:30)',         'P.A202', 40, 35, 2200000, 'open'),
  ('IT002-B', 'IT002', 8,  'T3 (13:00-15:30)',       'P.B108', 40, 22, 1800000, 'open'),
  ('IT003-A', 'IT003', 9,  'T6 (7:00-9:30)',         'P.A105', 30, 18, 2000000, 'open'),
  ('IT004-A', 'IT004', 2,  'T4 (13:00-15:30)',       'P.A301', 40, 28, 2800000, 'open'),
  ('IT004-B', 'IT004', 10, 'T5 (13:00-15:30)',       'P.B301', 35, 20, 2200000, 'open'),
  ('MA001-A', 'MA001', 11, 'T2 (9:30-12:00)',        'P.A203', 40, 30, 1500000, 'open'),
  ('MA001-B', 'MA001', 12, 'T4 (9:30-12:00)',        'P.B204', 40, 25, 1200000, 'open');


-- ===== REGISTRATIONS va PAYMENTS =====
-- tat trigger auto-update siso truoc khi seed (tranh double count)
ALTER TABLE registrations DISABLE TRIGGER trg_reg_siso;

-- HV 2024001 dang ky 2 lop (Python + AI)
INSERT INTO registrations (id, hv_id, lop_id, nv_xu_ly, ngay_dk, trang_thai) VALUES
  (1, 4,  'IT001-A', 3, '2026-04-10 08:30:00', 'paid'),
  (2, 4,  'IT004-A', 3, '2026-04-18 10:15:00', 'pending_payment'),
  -- cac HV khac
  (3, 13, 'IT001-A', 3, '2026-04-11 09:00:00', 'paid'),
  (4, 13, 'IT002-A', 20,'2026-04-18 10:30:00', 'pending_payment'),
  (5, 14, 'IT001-B', 3, '2026-04-12 14:00:00', 'paid'),
  (6, 14, 'IT004-B', 3, '2026-04-16 11:00:00', 'pending_payment'),
  (7, 15, 'IT001-A', 21,'2026-04-13 09:30:00', 'paid'),
  (8, 15, 'MA001-A', 21,'2026-04-17 16:00:00', 'paid'),
  (9, 16, 'IT001-A', 3, '2026-04-14 10:00:00', 'paid'),
  (10,17, 'IT004-A', 20,'2026-04-15 13:00:00', 'paid'),
  (11,18, 'IT001-B', 3, '2026-04-17 09:00:00', 'paid'),
  (12,19, 'IT001-C', 3, '2026-04-16 14:30:00', 'paid');

SELECT setval('registrations_id_seq', (SELECT MAX(id) FROM registrations));

-- bat lai trigger
ALTER TABLE registrations ENABLE TRIGGER trg_reg_siso;

-- payments cho cac registration da paid
INSERT INTO payments (reg_id, so_tien, hinh_thuc, ngay_thu, nv_thu, ghi_chu) VALUES
  (1,  2500000, 'Tien mat',    '2026-04-10 08:45:00', 3,  'Dong du'),
  (3,  2500000, 'Chuyen khoan','2026-04-11 09:15:00', 3,  NULL),
  (5,  1800000, 'Tien mat',    '2026-04-12 14:15:00', 3,  NULL),
  (7,  2500000, 'VNPay',       '2026-04-13 09:45:00', 21, NULL),
  (8,  1500000, 'Chuyen khoan','2026-04-17 16:20:00', 21, NULL),
  (9,  2500000, 'Tien mat',    '2026-04-14 10:30:00', 3,  NULL),
  (10, 2800000, 'Momo',        '2026-04-15 13:20:00', 20, NULL),
  (11, 1800000, 'Tien mat',    '2026-04-17 09:30:00', 3,  NULL),
  (12, 2000000, 'Chuyen khoan','2026-04-16 15:00:00', 3,  NULL);


-- ===== GRADES (mot so HV da co diem) =====
INSERT INTO grades (hv_id, lop_id, diem_qt, diem_thi, tong_ket, xep_loai, gv_nhap) VALUES
  (4,  'IT001-A', 8.5, 7.5, 7.8, 'B+', 2),
  (13, 'IT001-A', 9.0, 8.5, 8.7, 'A',  2),
  (14, 'IT001-B', 7.0, 6.5, 6.7, 'C+', 5),
  (15, 'IT001-A', 8.0, 7.5, 7.7, 'B',  2),
  (16, 'IT001-A', 9.5, 9.0, 9.2, 'A+', 2);


-- ===== NOTIFICATIONS =====
INSERT INTO notifications (tu_id, den_lop, tieu_de, noi_dung, loai, ngay_tao) VALUES
  (1, NULL,       'Lich khai giang thang 5', 'Trung tam khai giang cac lop khoa moi tu 05/05/2026.', 'info',    '2026-04-15 10:00:00'),
  (1, NULL,       'Nghi le 30/4 - 1/5',       'Trung tam nghi tu 30/4 den het 3/5/2026.',             'info',    '2026-04-05 09:00:00'),
  (2, 'IT001-A',  'Nghi hoc ngay 20/04',      'Thay ban hop nen tam nghi, hoc bu thu 7.',             'warning', '2026-04-17 15:00:00'),
  (2, 'IT004-A',  'Bai tap tuan 8',           'Nop bai tap truoc thu 6 tuan sau.',                    'info',    '2026-04-16 20:00:00'),
  (1, NULL,       'Uu dai 10% hoc phi',       'Giam 10% cho HV dang ky truoc 30/04/2026.',            'info',    '2026-03-28 08:00:00');


-- ===== REVIEWS (danh gia GV) =====
INSERT INTO reviews (hv_id, gv_id, lop_id, diem, nhan_xet) VALUES
  (13, 2,  'IT001-A', 5, 'Thay day rat nhiet tinh, de hieu'),
  (14, 5,  'IT001-B', 4, 'Thay on, bai tap hop ly'),
  (15, 2,  'IT001-A', 5, 'Rat tuyet voi'),
  (16, 2,  'IT001-A', 5, 'Thay gioi, giang de hieu'),
  (17, 2,  'IT004-A', 4, 'Bai hoc bo ich');
