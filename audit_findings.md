# Audit findings - rolling todo list (overnight loop)

Cron 5m loop tối nay sẽ pick 1-2 items từ list này, fix, commit + push.
Item đã xong: gạch ngang. Item mới: thêm vào "TIM THEM".

## Priority 1 — Bug / inconsistency

- [x] Cot "TC" trong tblAdminCourses → "Số buổi"
- [x] Cot "TC" trong tblCurriculum → "Số buổi"
- [x] tblCurriculum: "Mã HP" → "Mã KH", "Tên học phần" → "Tên khóa học", "Học kỳ" → "Đợt"
- [x] Admin curriculum cboHocKy: bỏ hardcode HK1..HK8, load unique hoc_ky_de_nghi từ DB; UI default "Tất cả đợt"
- [x] Admin stats: cot "TB khóa học/SV" → "Điểm TB lớp", "Tổng TC đăng ký" → "Doanh thu (đ)" + format số có dấu chấm
- [x] admin_stats.ui: cboStatSemester bỏ 2 hardcode HK1/HK2 (đã load dynamic ở code)
- [x] admin_stats.ui tblDept: "Số SV" → "Số HV"
- [x] admin_dashboard.ui line 226: lblStat4 hardcode "HK2" → "—" + code lookup tên đẹp từ SemesterService.get(id)
- [x] admin_dashboard.ui: "Học kỳ hiện tại" → "Đợt hiện tại"
- [x] admin_semester.ui: bỏ hardcode lblCurrentSem + lblSemStatus, code load từ SemesterService.get_current(); cập nhật label "Học kỳ" → "Đợt"
- [x] teacher_dashboard.ui line 34: load dynamic từ SemesterService.get_current() (giống HV)
- [x] teacher_review.ui line 36-37: cboSemesterReview bỏ hardcode HK1/HK2, để 1 item "Tất cả khóa học"
- [x] notifications.ui card 1-6: clear 18 mock strings (Title/Date/Content) → text generic placeholder

## Priority 2 — UX improvements

- [x] Dashboard HV: dynamic banner "Lịch học hôm nay" giữa 3 cards và bảng; show buổi sớm nhất + count nếu nhiều; placeholder "Hôm nay không có lịch học" khi rỗng; tableFrame auto-shift; cleanup banner cũ chống accumulation
- [x] Dashboard HV: stat icons 20→24px (đẹp hơn không vỡ layout); default mock 5/15/10 → "—"
- [x] Dashboard GV: đã có `tblToday` + filter theo gv_id + "Hôm nay không có buổi dạy" placeholder (existing)
- [x] Dashboard Adm: tblTopCourses cot % thay bằng QProgressBar widget (visual chart, màu đỏ/cam/xanh theo pct)
- [x] Notifications: badge đỏ (count) overlay btnNotice sidebar HV; auto-hide khi user click vào trang Notifications
- [x] Search bar: setClearButtonEnabled(True) trong widen_search → tự có nút X cho mọi search
- [x] Login screen: remember username vào ~/.eaut_last_user, auto-fill + focus password lần sau

## Priority 3 — Robustness

- [x] Backend: /health/db endpoint trả `connected/ping_ms/version/public_tables/active_connections`
- [x] Frontend api_error_msg: phân biệt ConnectionError/Timeout/HTTPError/422 Pydantic; map status code → tiếng Việt
- [x] Audit logs filter date: parse ngày từ cell text theo nhiều format → so với today; "Hôm nay/7 ngày qua/30 ngày qua" hoạt động thật
- [x] DB connection: auto-retry 1 lần khi conn closed (handle PG restart/network blip); reset _conn nếu lost mid-query
- [x] Logout: confirm dialog "Bạn có chắc muốn đăng xuất?" cho cả 4 windows (HV/Adm/GV/NV)

## TIM THEM (cron iterations append vào đây)

### Round 17-18 — currency format helper

- [x] Helper `fmt_vnd(amount, suffix=' đ', empty_zero=False)` — chuẩn hoá format VND có dấu chấm ngăn nghìn
- [x] Apply 5 chỗ duplicate format currency (vòng 17): admin stats, tblAdmClasses, GV classes, NV detail, NV class dialog
- [x] Apply 7 chỗ duplicate còn lại (vòng 18): NV today revenue, NV register cbo (×3), NV class info dialog HTML, NV reglist gia, NV pending payment gia — main.py `:,}.replace` ngoài helper = 0

### Round 22-23 — generate thêm findings

- [x] F5 / Ctrl+R = refresh page hiện tại (helper `install_refresh_shortcut`) → bind cho cả 4 windows (HV/GV/NV/Adm). User không cần logout để reload data sau khi admin update DB.
- [x] Action button tooltips trong `make_action_cell`: 10 button text → tooltip tiếng Việt rõ ràng (Sửa, Xóa, Xem, Chi tiết, Đánh giá, Hủy, Mở/Đóng ĐK, Nhập điểm, Duyệt) — apply tự động cho mọi nút action ở 4 windows
- [x] About dialog (F1): logo + version + tech stack + đối tượng + danh sách phím tắt — bind F1 trong `install_refresh_shortcut` cho cả 4 windows
- [x] Login button auto-disable khi 1 trong 2 field (username/password) rỗng → ngăn click submit khi chưa nhập đủ
- [x] Helper `center_on_screen()` + apply cho Login window + 4 main windows sau login → không bị nhảy lên góc trái màn hình
- [x] Auto-focus first field + placeholder text trong 3 dialog admin add (course/student/user GV+NV) — UX gõ ngay không cần click
- [x] Connection status indicator (dot xanh/đỏ + text) ở sidebar 4 windows — periodic check `is_alive()` mỗi 30s qua QTimer, auto-cleanup khi window destroy
- [x] Dialog admin add course thêm field `Mô tả` (QTextEdit multi-line) thay vì hack format `'TC: X, GV: Y'` — phối hợp với tooltip vòng 19 user thấy mô tả thật khi hover
- [x] Dialog admin EDIT course: thêm field Mô tả (fetch từ API + pre-fill), Mã khóa giờ readonly (PK không cho sửa), focus vào Tên khóa
- [x] Receipt dialog: thêm nút 📋 Sao chép clipboard + extract `_emp_build_receipt_content` helper dùng chung cho Save/Copy. Visual feedback "✓ Đã sao chép" 1.5s rồi revert
- [x] Helper `fmt_relative_date()`: format ngày UX-friendly ("Vừa xong" / "5 phút trước" / "Hôm qua" / "3 ngày trước" / dd/mm/yyyy nếu >7 ngày). Apply notifications page HV — kèm tooltip hover hiện full timestamp
- [x] Apply `fmt_relative_date` cho 3 activity tables: Adm tblRecent + GV tblActivity + NV tblActivityEmp — UX friendly hơn raw timestamp
- [x] Auto-focus + scope rename "Học kỳ" → "Đợt" cho dialog `_admin_add_semester` (đồng bộ scope ngoại khoá), placeholder gợi ý format ngày, `_admin_add_class` thêm focus mã lớp
- [x] `_admin_add_curriculum` dialog: rename "Môn" → "Khoá học", "Học kỳ" → "Đợt"; cbo_dot editable load existing dots từ DB + cho admin nhập tự do (vd "Mùa hè 2026"); auto-focus combo
- [x] `_admin_edit_curriculum` dialog: đồng bộ scope (Khoá/Đợt/title), cbo_dot editable preserve giá trị cũ + load existing; auto-focus tên khoá. Tăng `hoc_ky_de_nghi` schema VARCHAR(10)→VARCHAR(30) + ALTER live DB column để hỗ trợ tên đợt dài (vd "Mua he 2026")
- [x] Append username + role vào window title sau login (cả 2 path AuthService + MOCK fallback) → giúp phân biệt khi user mở nhiều cửa sổ EAUT cùng lúc
- [x] Optimize `StatsService.admin_overview()`: 4 query riêng → 1 query với sub-select (giảm 4x round-trip DB). Latency ~3ms avg
- [x] Optimize `StatsService.employee_today()` 3 query → 1 + `StatsService.teacher_overview()` 3 query → 1 (giảm 6 round-trip DB tổng cộng). NV/GV dashboard load nhanh hơn


### Round 18 — generate thêm findings

**P2 (UX nhỏ):**
- [x] Course `mo_ta` tooltip hover trong tblAdminCourses (HTML format `<b>{ten}</b><br>{mo_ta}`) — fetch field thêm vào data idx 7
- [~] Date picker default = today: code không có QDateEdit nào, không applicable
- [x] Schedule week nav debounce: disable cả 3 nút prev/next/today khi đang load API (HV + GV) → re-enable sau load xong qua try/finally
- [x] `_admin_add_user` (GV/NV) + `_admin_add_student`: pre-validate email/SDT format trước khi POST, thêm placeholder text gợi ý format đúng; HV thêm field email mới

**P3 (refactor):**
- [x] Helper `validate_password()` (min 6 ký tự + 1 chữ + 1 số + no space) → apply 3 dialog đổi password (HV/GV/NV) thay vì check len ad-hoc
- [ ] Centralized COLORS check: vài chỗ vẫn dùng hex hardcode thay vì COLORS["..."] — grep + replace
- [ ] Print statements: thay 97 print bằng logging — vẫn lớn, có thể split nhỏ theo module

### Round 12+ generated (scan codebase)

**P1 (cleanup/dead code):**
- [x] `_show_progress_dialog` (main.py:1982) — xóa 130 dòng dead code (đã bỏ nút từ vòng 3)
- [x] Login `lblError` auto-clear khi user gõ lại txtUsername/txtPassword (UX không bị error stale)
- [x] Re-add 12 _FK_MESSAGES entries (grades_hv_id, grades_gv_nhap, attendance_*, payments_*, notifications_*, schedules_lop_id, exam_schedules_*) + sửa registrations_nv_dk_fkey → registrations_nv_xu_ly_fkey

**P2 (UX):**
- [x] Login: nút 👁/🙈 toggle hiện/ẩn password (overlay góc phải txtPassword, dynamic không sửa .ui)
- [x] Helper `msg_confirm_delete()` icon ⚠ + nút "Xóa" màu đỏ + cảnh báo "KHÔNG THỂ HOÀN TÁC" + pre-check số item liên quan (lớp/khoá/HV)
- [x] Helper `set_table_empty_state()` chuẩn hoá empty state (italic gray text, span full width, height 50)
- [x] Refactor 4 chỗ empty state placeholder dùng `set_table_empty_state()` helper (HV dashboard, exam, GV today + activity)
- [x] Refactor 7 chỗ empty state còn lại (HV grades, HV review, Adm topCourses+dept+stats helper, NV pending, NV classes) — 0 còn duplicate
- [~] Dashboard GV welcome: đã có lblWelcome + lblSemester + tblToday tương đương HV banner — bỏ qua (đã đủ)

**P3 (robustness):**
- [ ] 97 `print(f'[...]` trong main.py — nên replace bằng `logging` module để tắt được dễ hơn
- [ ] Backend exception handlers: `print(f'[STATS] loi:')` raw — log + truyền request_id để debug
- [ ] `MOCK_USER['password']` lưu plain text trong Python dict — replace bằng `_session_user` chứa user object thật

**Image AI (sẵn key Grok):**
- [ ] Image gen (sau khi fix hết bug): dùng Grok image API tạo cover image cho khóa học, hoặc avatar mặc định cho user mới — KHÔNG phải text chat
