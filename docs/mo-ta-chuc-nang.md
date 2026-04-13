# Mô tả chức năng - Hệ thống Đăng ký Khóa học

## 1. Tổng quan

Ứng dụng hỗ trợ sinh viên đăng ký khóa học trực tuyến, đồng thời cung cấp công cụ quản lý cho admin (phòng đào tạo). Hệ thống gồm 2 phần chính: giao diện sinh viên và giao diện quản trị.

---

## 2. Phân quyền người dùng

| Vai trò | Mô tả |
|---------|-------|
| Sinh viên | Đăng nhập, xem và đăng ký khóa học, xem lịch học, cập nhật thông tin cá nhân |
| Admin | Quản lý khóa học, quản lý sinh viên, quản lý học kỳ, xem thống kê đăng ký |

---

## 3. Chức năng chi tiết

### 3.1. Đăng nhập / Đăng xuất

- Sinh viên đăng nhập bằng mã sinh viên + mật khẩu
- Admin đăng nhập bằng tài khoản riêng
- Phân quyền tự động sau khi đăng nhập (chuyển sang giao diện tương ứng)
- Hỗ trợ đổi mật khẩu

### 3.2. Chức năng phía Sinh viên

**a) Xem danh sách khóa học**
- Hiển thị các khóa học đang mở trong học kỳ hiện tại
- Thông tin gồm: mã khóa học, tên, số tín chỉ, giảng viên, lịch học, số chỗ còn lại
- Tìm kiếm theo tên hoặc mã khóa học
- Lọc theo số tín chỉ, theo khoa

**b) Đăng ký khóa học**
- Chọn khóa học từ danh sách và xác nhận đăng ký
- Kiểm tra trùng lịch trước khi cho đăng ký
- Kiểm tra số chỗ còn lại (nếu hết chỗ thì báo đầy)
- Giới hạn số tín chỉ tối đa mỗi học kỳ

**c) Hủy đăng ký**
- Xem danh sách khóa học đã đăng ký
- Chọn khóa học cần hủy và xác nhận
- Cập nhật lại số chỗ trống của khóa học đó

**d) Xem lịch học**
- Hiển thị lịch học theo tuần dựa trên các khóa học đã đăng ký
- Đánh dấu trùng lịch nếu có

**e) Xem điểm**
- Xem bảng điểm các học kỳ trước
- Hiển thị: mã khóa học, tên khóa học, số tín chỉ, điểm

**f) Thông tin cá nhân**
- Xem thông tin: họ tên, mã sv, lớp, khoa, email, sđt
- Chỉnh sửa một số thông tin (email, sđt, mật khẩu)

### 3.3. Chức năng phía Admin

**a) Quản lý khóa học**
- Thêm khóa học mới (tên, mã, số tín chỉ, giảng viên, lịch học, số chỗ tối đa)
- Sửa thông tin khóa học
- Xóa khóa học (chỉ xóa khi chưa có ai đăng ký)
- Xem danh sách sinh viên đã đăng ký trong từng khóa học

**b) Quản lý sinh viên**
- Xem danh sách sinh viên
- Tìm kiếm sinh viên theo mã sv hoặc tên
- Xem chi tiết thông tin và các khóa học đã đăng ký của sinh viên
- Thêm / xóa tài khoản sinh viên

**c) Quản lý học kỳ**
- Tạo học kỳ mới
- Mở / đóng đăng ký cho từng học kỳ
- Gán khóa học vào học kỳ

**d) Thống kê**
- Số lượng sinh viên đăng ký theo từng khóa học
- Khóa học nào đầy nhất / trống nhất
- Thống kê theo khoa, theo lớp

---

## 4. Ràng buộc nghiệp vụ

- Mỗi sinh viên có giới hạn tín chỉ tối đa trong 1 học kỳ (vd: 25 tín chỉ)
- Không cho đăng ký khóa học bị trùng lịch
- Không cho đăng ký khi hết chỗ
- Chỉ được hủy đăng ký trong thời gian cho phép
- Admin không thể xóa khóa học đã có sinh viên đăng ký

---

## 5. Công nghệ

| Thành phần | Công nghệ |
|------------|-----------|
| Frontend | PyQt5 + Qt Designer |
| Backend | Flask (REST API) |
| Database | MySQL |
| Giao tiếp | HTTP request (frontend gọi API backend) |
