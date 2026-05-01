classDiagram
    direction TB

    class UngDung {
        -QApplication ung_dung
        -QWidget cua_so_chinh
        -QWidget cua_so_dang_nhap
        +hien_dang_nhap()
        +_dong_bo_tu_nguoi_dung(u)
        +chay()
    }

    class CuaSoDangNhap {
        <<QWidget from login.ui>>
        +txtTenDangNhap QLineEdit
        +txtMatKhau QLineEdit
        +btnDangNhap QPushButton
        +khi_dang_nhap()
    }

    class CuaSoHocVien {
        <<HocVien - 7 trang>>
        -QStackedWidget ngan_xep
        -list~Widget~ cac_trang
        +_khi_chuyen_trang(index)
        +_dien_diem_so()
        +_dien_danh_gia()
        +_mo_hop_danh_gia(gv)
        +_doi_mat_khau()
    }

    class CuaSoGiangVien {
        <<GiangVien - 7 trang>>
        +_dien_lop_gv()
        +_dien_hv_gv()
        +_dien_diem_gv()
        +_luu_diem_gv()
        +_gv_gui_thong_bao()
        +_gv_hop_thoai_diem(bang, hang)
    }

    class CuaSoNhanVien {
        <<NhanVien - 6 trang>>
        -set _da_dong_tien
        +_nv_dang_ky()
        +_nv_xac_nhan_tt(bang)
        +_nv_hien_bien_lai()
        +_nv_tra_cuu_hv()
    }

    class CuaSoQuanTri {
        <<QuanTriVien - 10 trang>>
        +_qt_them_mon()
        +_qt_them_lop()
        +_qt_them_nguoi_dung(vai_tro, ...)
        +_qt_them_hoc_ky()
        +_qt_them_chuong_trinh()
        +_qt_bat_tat_hoc_ky()
        +_qt_loc_*()
    }

    UngDung *-- CuaSoDangNhap : composition
    UngDung *-- CuaSoHocVien : composition
    UngDung *-- CuaSoGiangVien : composition
    UngDung *-- CuaSoNhanVien : composition
    UngDung *-- CuaSoQuanTri : composition

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