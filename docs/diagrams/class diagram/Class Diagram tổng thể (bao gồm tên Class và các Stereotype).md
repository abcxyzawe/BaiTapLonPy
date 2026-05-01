classDiagram
    direction TB

    %% PRESENTATION
    class UngDung
    class CuaSoDangNhap { <<QWidget>> }
    class CuaSoHocVien   { <<7 trang>> }
    class CuaSoGiangVien { <<7 trang>> }
    class CuaSoNhanVien  { <<6 trang>> }
    class CuaSoQuanTri   { <<10 trang>> }

    %% SERVICE
    class CoSoDuLieu     { <<Singleton>> }
    class DichVuXacThuc
    class DichVuMonHoc
    class DichVuDangKy
    class DichVuDiem
    class DichVuThongBao
    class DichVuHocVien
    class DichVuGiangVien
    class DichVuNhanVien
    class DichVuDanhGia
    class DichVuThongKe
    class DichVuHocKy
    class DichVuChuongTrinh
    class DichVuLichHoc
    class DichVuLichThi
    class DichVuDiemDanh
    class DichVuNhatKy

    %% DOMAIN
    class ThucThe  { <<abstract>> }
    class NguoiDung { <<abstract>> }
    class HocVien
    class GiangVien
    class NhanVien
    class QuanTriVien
    class MonHoc
    class HocKy
    class LopHoc
    class ChuongTrinh
    class DangKy
    class ThanhToan
    class DiemSo
    class ThongBao
    class DanhGia
    class LichHoc
    class LichThi
    class DiemDanh
    class NhatKy

    %% Presentation composition
    UngDung *-- CuaSoDangNhap
    UngDung *-- CuaSoHocVien
    UngDung *-- CuaSoGiangVien
    UngDung *-- CuaSoNhanVien
    UngDung *-- CuaSoQuanTri

    %% Presentation -> Service
    CuaSoDangNhap  ..> DichVuXacThuc
    CuaSoHocVien   ..> DichVuDiem
    CuaSoHocVien   ..> DichVuDanhGia
    CuaSoGiangVien ..> DichVuMonHoc
    CuaSoGiangVien ..> DichVuDiem
    CuaSoNhanVien  ..> DichVuDangKy
    CuaSoQuanTri   ..> DichVuThongKe
    CuaSoQuanTri   ..> DichVuMonHoc
    CuaSoQuanTri   ..> DichVuHocKy
    CuaSoQuanTri   ..> DichVuChuongTrinh

    %% Service -> Database
    DichVuXacThuc    ..> CoSoDuLieu
    DichVuMonHoc     ..> CoSoDuLieu
    DichVuDangKy     ..> CoSoDuLieu
    DichVuDiem       ..> CoSoDuLieu
    DichVuThongBao   ..> CoSoDuLieu
    DichVuHocVien    ..> CoSoDuLieu
    DichVuGiangVien  ..> CoSoDuLieu
    DichVuNhanVien   ..> CoSoDuLieu
    DichVuDanhGia    ..> CoSoDuLieu
    DichVuThongKe    ..> CoSoDuLieu
    DichVuHocKy      ..> CoSoDuLieu
    DichVuChuongTrinh ..> CoSoDuLieu
    DichVuLichHoc    ..> CoSoDuLieu
    DichVuLichThi    ..> CoSoDuLieu
    DichVuDiemDanh   ..> CoSoDuLieu
    DichVuNhatKy     ..> CoSoDuLieu

    %% Service -> Domain
    DichVuXacThuc     ..> NguoiDung
    DichVuHocVien     ..> HocVien
    DichVuGiangVien   ..> GiangVien
    DichVuNhanVien    ..> NhanVien
    DichVuMonHoc      ..> MonHoc
    DichVuMonHoc      ..> LopHoc
    DichVuDangKy      ..> DangKy
    DichVuDangKy      ..> ThanhToan
    DichVuDiem        ..> DiemSo
    DichVuThongBao    ..> ThongBao
    DichVuDanhGia     ..> DanhGia
    DichVuHocKy       ..> HocKy
    DichVuChuongTrinh ..> ChuongTrinh
    DichVuLichHoc     ..> LichHoc
    DichVuLichThi     ..> LichThi
    DichVuDiemDanh    ..> DiemDanh
    DichVuNhatKy      ..> NhatKy

    %% Kế thừa
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

    %% Domain relationships
    MonHoc    "1" o-- "N" LopHoc      : tong hop
    MonHoc    "1" o-- "N" ChuongTrinh : co trong CT
    HocKy     "1" o-- "N" LopHoc      : chua
    HocKy     "1" --  "N" LichThi
    GiangVien "1" --  "N" LopHoc      : phu trach
    HocVien   "1" --  "N" DangKy      : dang ky
    LopHoc    "1" --  "N" DangKy      : duoc DK
    NhanVien  "1" --  "N" DangKy      : xu ly
    DangKy    "1" *-- "1..N" ThanhToan
    NhanVien  "1" --  "N" ThanhToan   : thu tien
    HocVien   "1" --  "N" DiemSo
    LopHoc    "1" --  "N" DiemSo
    GiangVien "1" --  "N" DiemSo      : nhap
    HocVien   "1" --  "N" DanhGia
    GiangVien "1" --  "N" DanhGia
    LopHoc    "1" --  "N" DanhGia
    LopHoc    "1" --  "N" LichHoc
    LopHoc    "1" --  "N" LichThi
    LichHoc   "1" --  "N" DiemDanh
    HocVien   "1" --  "N" DiemDanh
    NguoiDung "1" --  "N" ThongBao    : gui
    LopHoc    "1" --  "N" ThongBao    : nhan
    NguoiDung "1" --  "N" NhatKy      : tao