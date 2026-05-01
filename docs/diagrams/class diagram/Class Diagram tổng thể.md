classDiagram
    direction TB

    %% ========== PRESENTATION LAYER ==========
    class UngDung {
        -QApplication ung_dung
        -QWidget cua_so_chinh
        -QWidget cua_so_dang_nhap
        +hien_dang_nhap()
        +chay()
    }
    class CuaSoDangNhap {
        <<QWidget>>
        +khi_dang_nhap()
    }
    class CuaSoHocVien {
        <<7 trang>>
        +_dien_diem_so()
        +_dien_danh_gia()
        +_doi_mat_khau()
    }
    class CuaSoGiangVien {
        <<7 trang>>
        +_dien_lop_gv()
        +_luu_diem_gv()
        +_gv_gui_thong_bao()
    }
    class CuaSoNhanVien {
        <<6 trang>>
        +_nv_dang_ky()
        +_nv_xac_nhan_tt()
        +_nv_tra_cuu_hv()
    }
    class CuaSoQuanTri {
        <<10 trang>>
        +_qt_them_mon()
        +_qt_them_lop()
        +_qt_them_nguoi_dung()
        +_qt_them_hoc_ky()
    }

    %% ========== SERVICE LAYER ==========
    class CoSoDuLieu {
        <<Singleton>>
        -Connection _ket_noi
        -bool _da_ket_noi
        +__new__()$ CoSoDuLieu
        +ket_noi() Connection
        +lay_tat_ca(sql, params) list
        +lay_mot(sql, params) dict
        +thuc_thi(sql, params) int
    }
    class DichVuXacThuc {
        +dang_nhap(u, p)$ NguoiDung
        +doi_mat_khau(id, mk)$
    }
    class DichVuMonHoc {
        +lay_tat_ca_mon()$ list
        +lay_tat_ca_lop()$ list
        +tao_mon(...)$
        +tao_lop(...)$
        +xoa_mon(ma)$
        +xoa_lop(ma)$
    }
    class DichVuDangKy {
        +dang_ky_hv(hv, lop, nv)$ int
        +lay_cho_dong_tien()$ list
        +xac_nhan_thanh_toan(...)$
        +huy_dang_ky(id)$
    }
    class DichVuDiem {
        +lay_diem_theo_hv(hv)$ list
        +lay_diem_theo_lop(lop)$ list
        +luu_diem(...)$
        +lay_gpa(hv)$ dict
    }
    class DichVuThongBao {
        +lay_tat_ca()$ list
        +lay_cho_hv(hv)$ list
        +gui(...)$
        +xoa(id)$
    }
    class DichVuHocVien {
        +lay_tat_ca()$ list
        +tao(...)$ int
        +cap_nhat(id, ...)$
        +xoa(id)$
    }
    class DichVuGiangVien {
        +lay_tat_ca()$ list
        +tao(...)$ int
        +cap_nhat(id, ...)$
        +xoa(id)$
    }
    class DichVuNhanVien {
        +lay_tat_ca()$ list
        +tao(...)$ int
        +cap_nhat(id, ...)$
        +xoa(id)$
    }
    class DichVuDanhGia {
        +gui_danh_gia(hv, gv, lop, diem)$
    }
    class DichVuThongKe {
        +tong_quan_admin()$ dict
        +top_lop(limit)$ list
        +tong_quan_gv(gv)$ dict
    }
    class DichVuHocKy {
        +lay_tat_ca()$ list
        +lay_hien_tai()$ dict
        +tao(...)$
        +xoa(id)$
    }
    class DichVuChuongTrinh {
        +lay_tat_ca(nganh)$ list
        +tao(...)$ int
        +xoa(id)$
    }
    class DichVuLichHoc {
        +lay_theo_tuan(thu_hai)$ list
        +lay_hom_nay()$ list
        +tao(...)$
    }
    class DichVuLichThi {
        +lay_tat_ca(hk)$ list
        +lay_cho_hv(hv, hk)$ list
        +tao(...)$
    }
    class DichVuDiemDanh {
        +diem_danh(...)$
        +lay_theo_lich(id)$ list
        +ty_le_dd(hv, lop)$ float
    }
    class DichVuNhatKy {
        +lay_tat_ca(bo_loc)$ list
        +ghi(...)$
        +ghi_dang_nhap(uid, user, role)$
    }

    %% ========== DOMAIN LAYER ==========
    class ThucThe {
        <<abstract>>
        +lay_tu_dong(row)* ThucThe
        +thanh_tu_dien()* dict
        +__repr__() str
        #_khoa() str
    }
    class NguoiDung {
        <<abstract>>
        -int _id
        -str _ten_dang_nhap
        -str _vai_tro
        -str _ho_ten
        -str _email
        -str _sdt
        -bool _dang_hoat_dong
        +id() int
        +ho_ten() str
        +lay_vai_tro()* str
    }
    class HocVien {
        -str _msv
        -date _ngay_sinh
        -str _gioi_tinh
        -str _dia_chi
        +msv() str
        +lay_vai_tro() "Hoc vien"
    }
    class GiangVien {
        -str _ma_gv
        -str _hoc_vi
        -str _khoa
        -str _chuyen_nganh
        -int _tham_nien
        +ma_gv() str
        +lay_vai_tro() "Giang vien"
    }
    class NhanVien {
        -str _ma_nv
        -str _chuc_vu
        -str _phong_ban
        -date _ngay_vao_lam
        +ma_nv() str
        +lay_vai_tro() "Nhan vien"
    }
    class QuanTriVien {
        -str _ma_admin
        +ma_admin() str
        +lay_vai_tro() "Quan tri vien"
    }
    class MonHoc {
        -str _ma_mon
        -str _ten_mon
        -str _mo_ta
    }
    class HocKy {
        -str _id
        -str _ten
        -str _nam_hoc
        -date _bat_dau
        -date _ket_thuc
        -str _trang_thai
        +dang_mo() bool
        +so_ngay() int
    }
    class LopHoc {
        -str _ma_lop
        -str _ma_mon
        -int _gv_id
        -str _hoc_ky_id
        -int _si_so_max
        -int _si_so_hien_tai
        -int _gia
        -str _trang_thai
        +da_day() bool
        +cho_trong() int
        +dinh_dang_gia() str
    }
    class ChuongTrinh {
        -int _id
        -str _ma_mon
        -int _tin_chi
        -str _loai
        -str _mon_tien_quyet
        -str _nganh
        +co_tien_quyet() bool
    }
    class DangKy {
        -int _id
        -int _hv_id
        -str _lop_id
        -int _nv_xu_ly
        -str _trang_thai
        +da_dong_tien() bool
        +cho_xu_ly() bool
    }
    class ThanhToan {
        -int _id
        -int _dk_id
        -int _so_tien
        -str _hinh_thuc
        -int _nv_thu
        -str _so_bien_lai
        +dinh_dang_tien() str
    }
    class DiemSo {
        -int _hv_id
        -str _lop_id
        -float _diem_qt
        -float _diem_thi
        -float _tong_ket
        -str _xep_loai
        +dat_yeu_cau() bool
        +tinh_tong(qt, thi)$ float
        +tinh_xep_loai(diem)$ str
    }
    class ThongBao {
        -int _id
        -int _tu_id
        -str _den_lop
        -str _tieu_de
        -str _noi_dung
        -str _loai
        +khan_cap() bool
        +toan_truong() bool
    }
    class DanhGia {
        -int _id
        -int _hv_id
        -int _gv_id
        -str _lop_id
        -int _diem
        -str _nhan_xet
        +sao() str
    }
    class LichHoc {
        -int _id
        -str _lop_id
        -date _ngay
        -time _gio_bat_dau
        -time _gio_ket_thuc
        -int _buoi_so
        -str _trang_thai
        +da_qua() bool
        +hom_nay() bool
    }
    class LichThi {
        -int _id
        -str _lop_id
        -str _hoc_ky_id
        -date _ngay_thi
        -str _ca_thi
        -str _hinh_thuc
        +da_qua() bool
        +sap_den() bool
    }
    class DiemDanh {
        -int _id
        -int _lich_hoc_id
        -int _hv_id
        -str _trang_thai
        -time _gio_vao
        +co_mat() bool
        +di_muon() bool
    }
    class NhatKy {
        -int _id
        -int _nguoi_dung_id
        -str _ten_dang_nhap
        -str _hanh_dong
        -str _loai_doi_tuong
        -str _mo_ta
    }

    %% ========== PRESENTATION COMPOSITION ==========
    UngDung *-- CuaSoDangNhap
    UngDung *-- CuaSoHocVien
    UngDung *-- CuaSoGiangVien
    UngDung *-- CuaSoNhanVien
    UngDung *-- CuaSoQuanTri

    %% ========== PRESENTATION -> SERVICE ==========
    CuaSoDangNhap ..> DichVuXacThuc : su dung
    CuaSoHocVien ..> DichVuDiem : su dung
    CuaSoHocVien ..> DichVuDanhGia : su dung
    CuaSoGiangVien ..> DichVuMonHoc : su dung
    CuaSoGiangVien ..> DichVuDiem : su dung
    CuaSoNhanVien ..> DichVuDangKy : su dung
    CuaSoQuanTri ..> DichVuThongKe : su dung
    CuaSoQuanTri ..> DichVuMonHoc : su dung
    CuaSoQuanTri ..> DichVuHocKy : su dung
    CuaSoQuanTri ..> DichVuChuongTrinh : su dung

    %% ========== SERVICE -> DATABASE ==========
    DichVuXacThuc ..> CoSoDuLieu : su dung
    DichVuMonHoc ..> CoSoDuLieu : su dung
    DichVuDangKy ..> CoSoDuLieu : su dung
    DichVuDiem ..> CoSoDuLieu : su dung
    DichVuThongBao ..> CoSoDuLieu : su dung
    DichVuHocVien ..> CoSoDuLieu : su dung
    DichVuGiangVien ..> CoSoDuLieu : su dung
    DichVuNhanVien ..> CoSoDuLieu : su dung
    DichVuDanhGia ..> CoSoDuLieu : su dung
    DichVuThongKe ..> CoSoDuLieu : su dung
    DichVuHocKy ..> CoSoDuLieu : su dung
    DichVuChuongTrinh ..> CoSoDuLieu : su dung
    DichVuLichHoc ..> CoSoDuLieu : su dung
    DichVuLichThi ..> CoSoDuLieu : su dung
    DichVuDiemDanh ..> CoSoDuLieu : su dung
    DichVuNhatKy ..> CoSoDuLieu : su dung

    %% ========== SERVICE -> DOMAIN ==========
    DichVuXacThuc ..> NguoiDung : tao
    DichVuHocVien ..> HocVien : tao
    DichVuGiangVien ..> GiangVien : tao
    DichVuNhanVien ..> NhanVien : tao
    DichVuMonHoc ..> MonHoc : tao
    DichVuMonHoc ..> LopHoc : tao
    DichVuDangKy ..> DangKy : tao
    DichVuDangKy ..> ThanhToan : tao
    DichVuDiem ..> DiemSo : tao
    DichVuThongBao ..> ThongBao : tao
    DichVuDanhGia ..> DanhGia : tao
    DichVuHocKy ..> HocKy : tao
    DichVuChuongTrinh ..> ChuongTrinh : tao
    DichVuLichHoc ..> LichHoc : tao
    DichVuLichThi ..> LichThi : tao
    DichVuDiemDanh ..> DiemDanh : tao
    DichVuNhatKy ..> NhatKy : tao

    %% ========== DOMAIN INHERITANCE ==========
    NguoiDung <|-- HocVien
    NguoiDung <|-- GiangVien
    NguoiDung <|-- NhanVien
    NguoiDung <|-- QuanTriVien

    ThucThe <|-- MonHoc
    ThucThe <|-- HocKy
    ThucThe <|-- LopHoc
    ThucThe <|-- ChuongTrinh
    ThucThe <|-- DangKy
    ThucThe <|-- ThanhToan
    ThucThe <|-- DiemSo
    ThucThe <|-- ThongBao
    ThucThe <|-- DanhGia
    ThucThe <|-- LichHoc
    ThucThe <|-- LichThi
    ThucThe <|-- DiemDanh
    ThucThe <|-- NhatKy

    %% ========== DOMAIN RELATIONSHIPS ==========
    MonHoc "1" o-- "N" LopHoc          : tong hop
    MonHoc "1" o-- "N" ChuongTrinh     : co trong CT
    HocKy "1" o-- "N" LopHoc           : chua
    HocKy "1" -- "N" LichThi
    GiangVien "1" -- "N" LopHoc        : phu trach

    HocVien "1" -- "N" DangKy          : dang ky
    LopHoc "1" -- "N" DangKy           : duoc DK
    NhanVien "1" -- "N" DangKy         : xu ly

    DangKy "1" *-- "1..N" ThanhToan    : composition
    NhanVien "1" -- "N" ThanhToan      : thu tien

    HocVien "1" -- "N" DiemSo
    LopHoc "1" -- "N" DiemSo
    GiangVien "1" -- "N" DiemSo        : nhap

    HocVien "1" -- "N" DanhGia
    GiangVien "1" -- "N" DanhGia
    LopHoc "1" -- "N" DanhGia

    LopHoc "1" -- "N" LichHoc
    LopHoc "1" -- "N" LichThi

    LichHoc "1" -- "N" DiemDanh
    HocVien "1" -- "N" DiemDanh

    NguoiDung "1" -- "N" ThongBao      : gui
    LopHoc "1" -- "N" ThongBao         : nhan
    NguoiDung "1" -- "N" NhatKy        : tao