classDiagram
    direction LR

    class CoSoDuLieu {
        <<Singleton>>
        -Connection _ket_noi
        -bool _da_ket_noi
        +__new__()$ CoSoDuLieu
        +ket_noi() Connection
        +dang_ket_noi() bool
        +con_tro() ContextManager
        +lay_tat_ca(sql, params) list
        +lay_mot(sql, params) dict
        +thuc_thi(sql, params) int
        +thuc_thi_tra_ve(sql, params) dict
    }

    class DichVuXacThuc {
        +dang_nhap(u, p)$ NguoiDung
        -_tao_nguoi_dung(row)$ NguoiDung
        +doi_mat_khau(id, mk)$
    }

    class DichVuMonHoc {
        +lay_tat_ca_mon()$ list
        +lay_tat_ca_lop()$ list
        +lay_lop_theo_gv(gv)$ list
        +lay_hv_theo_gv(gv)$ list
        +tao_mon(...)$
        +cap_nhat_mon(...)$
        +xoa_mon(ma)$
        +tao_lop(...)$
        +cap_nhat_lop(...)$
        +xoa_lop(ma_lop)$
        +lay_danh_sach_gv()$ list
    }

    class DichVuDangKy {
        +dang_ky_hv(hv, lop, nv)$ int
        +lay_tat_ca_dk()$ list
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
        +lay_da_gui_gv(gv)$ list
        +gui(...)$
        +lay_gan_day(limit)$ list
        +xoa(id)$
    }

    class DichVuHocVien {
        +lay_tat_ca()$ list
        +lay_theo_msv(msv)$ dict
        +tao(...)$ int
        +cap_nhat(id, ...)$
        +xoa(id)$
    }

    class DichVuGiangVien {
        +lay_tat_ca()$ list
        +lay_cho_danh_gia()$ list
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
        +hoat_dong_gan_day(limit)$ list
        +hom_nay_nv(nv)$ dict
        +tong_quan_gv(gv)$ dict
        +thong_ke_hoc_ky(hk)$ dict
    }

    class DichVuHocKy {
        +lay_tat_ca()$ list
        +lay_hien_tai()$ dict
        +tao(...)$
        +dat_trang_thai(id, tt)$
        +xoa(id)$
    }

    class DichVuChuongTrinh {
        +lay_tat_ca(nganh)$ list
        +tao(...)$ int
        +cap_nhat(id, ...)$
        +xoa(id)$
    }

    class DichVuLichHoc {
        +lay_theo_tuan(thu_hai)$ list
        +lay_cho_hv_tuan(hv, t2)$ list
        +lay_cho_gv_tuan(gv, t2)$ list
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