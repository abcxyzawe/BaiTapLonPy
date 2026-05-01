erDiagram
    nguoi_dung {
        int id PK
        varchar username UK
        varchar password
        varchar role
        varchar full_name
        varchar email
        varchar sdt
        timestamp created_at
        boolean is_active
    }
    hoc_vien {
        int user_id PK
        varchar msv UK
        date ngaysinh
        varchar gioitinh
        varchar diachi
    }
    giao_vien {
        int user_id PK
        varchar ma_gv UK
        varchar hoc_vi
        varchar khoa
        varchar chuyen_nganh
        int tham_nien
    }
    nhan_vien {
        int user_id PK
        varchar ma_nv UK
        varchar chuc_vu
        varchar phong_ban
        date ngay_vao_lam
    }
    quan_tri_vien {
        int user_id PK
        varchar ma_admin UK
    }
    mon_hoc {
        varchar ma_mon PK
        varchar ten_mon
        text mo_ta
    }
    hoc_ky {
        varchar id PK
        varchar ten
        varchar nam_hoc
        date bat_dau
        date ket_thuc
        varchar trang_thai
    }
    chuong_trinh_hoc {
        int id PK
        varchar ma_mon FK
        int tin_chi
        varchar loai
        varchar hoc_ky_de_nghi
        varchar mon_tien_quyet
        varchar nganh
    }
    lop_hoc {
        varchar ma_lop PK
        varchar ma_mon FK
        int gv_id FK
        varchar semester_id FK
        varchar lich
        varchar phong
        int siso_max
        int siso_hien_tai
        numeric gia
        varchar trang_thai
        date ngay_bat_dau
        date ngay_ket_thuc
        int so_buoi
    }
    dang_ky {
        int id PK
        int hv_id FK
        varchar lop_id FK
        int nv_xu_ly FK
        timestamp ngay_dk
        varchar trang_thai
    }
    thanh_toan {
        int id PK
        int reg_id FK
        numeric so_tien
        varchar hinh_thuc
        timestamp ngay_thu
        int nv_thu FK
        varchar so_bien_lai UK
        text ghi_chu
    }
    bang_diem {
        int hv_id PK
        varchar lop_id PK
        numeric diem_qt
        numeric diem_thi
        numeric tong_ket
        varchar xep_loai
        int gv_nhap FK
        timestamp updated_at
    }
    lich_hoc {
        int id PK
        varchar lop_id FK
        date ngay
        int thu
        time gio_bat_dau
        time gio_ket_thuc
        varchar phong
        int buoi_so
        varchar noi_dung
        varchar trang_thai
    }
    lich_thi {
        int id PK
        varchar lop_id FK
        varchar semester_id FK
        date ngay_thi
        varchar ca_thi
        time gio_bat_dau
        time gio_ket_thuc
        varchar phong
        varchar hinh_thuc
        int so_cau
        int thoi_gian_phut
    }
    thong_bao {
        int id PK
        int tu_id FK
        varchar den_lop FK
        varchar tieu_de
        text noi_dung
        varchar loai
        timestamp ngay_tao
    }
    danh_gia {
        int id PK
        int hv_id FK
        int gv_id FK
        varchar lop_id FK
        int diem
        text nhan_xet
        timestamp ngay
    }
    diem_danh {
        bigint id PK
        int schedule_id FK
        int hv_id FK
        int recorded_by FK
        varchar trang_thai
        time gio_vao
        text ghi_chu
        timestamp recorded_at
    }
    nhat_ky_he_thong {
        bigint id PK
        int user_id FK
        varchar username
        varchar role
        varchar action
        varchar target_type
        varchar target_id
        text description
        varchar ip_address
        timestamp created_at
    }

    nguoi_dung ||--|| hoc_vien : "la"
    nguoi_dung ||--|| giao_vien : "la"
    nguoi_dung ||--|| nhan_vien : "la"
    nguoi_dung ||--|| quan_tri_vien : "la"
    mon_hoc ||--o{ lop_hoc : "co N lop"
    mon_hoc ||--o{ chuong_trinh_hoc : "trong CT"
    hoc_ky ||--o{ lop_hoc : "chua"
    hoc_ky ||--o{ lich_thi : "co lich thi"
    giao_vien ||--o{ lop_hoc : "phu trach"
    lop_hoc ||--o{ dang_ky : "duoc dang ky"
    lop_hoc ||--o{ bang_diem : "co diem"
    lop_hoc ||--o{ lich_hoc : "co buoi hoc"
    lop_hoc ||--o{ lich_thi : "co lich thi"
    lop_hoc ||--o{ danh_gia : "duoc review"
    lop_hoc ||--o{ thong_bao : "nhan"
    hoc_vien ||--o{ dang_ky : "dang ky"
    hoc_vien ||--o{ bang_diem : "co diem"
    hoc_vien ||--o{ danh_gia : "gui"
    hoc_vien ||--o{ diem_danh : "diem danh"
    giao_vien ||--o{ bang_diem : "nhap"
    giao_vien ||--o{ danh_gia : "duoc danh gia"
    nhan_vien ||--o{ dang_ky : "xu ly"
    nhan_vien ||--o{ thanh_toan : "thu tien"
    dang_ky ||--o{ thanh_toan : "thanh toan CASCADE"
    lich_hoc ||--o{ diem_danh : "co diem danh"
    nguoi_dung ||--o{ nhat_ky_he_thong : "tao log"
    nguoi_dung ||--o{ thong_bao : "gui"
    nguoi_dung ||--o{ diem_danh : "ghi nhan"