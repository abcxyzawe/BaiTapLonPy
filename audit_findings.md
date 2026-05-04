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
- [x] Bind Ctrl+1..Ctrl+9 = switch sidebar tab idx 0..8 cho 4 windows (HV/GV/NV/Adm). Power user navigate nhanh không cần chuột
- [x] About dialog (F1) update: fetch backend version + tables + connections từ /health/db; thêm bảng phím tắt đầy đủ (F5/F1/Ctrl+1..9/Esc); dialog 480×460
- [x] **BUG FIX nghiêm trọng**: `classes.siso_hien_tai` không sync với `registrations` (12/12 lớp drift, vd siso=35 nhưng actual=4). Tạo DB trigger AFTER INSERT/UPDATE/DELETE registrations → tự update siso_hien_tai từ COUNT real. Backfill 12 rows hiện tại + thêm vào schema.sql cho fresh setup. Verified live trigger works
- [x] Format VND trong `recent_activity` SQL: `2200000` → `2.200.000 đ` qua TO_CHAR + REPLACE (PostgreSQL không có '.' separator builtin). Activity feed admin/NV nhìn đẹp + nhất quán với fmt_vnd helper FE
- [x] Refresh MOCK_CLASSES cache sau khi NV register/cancel registration → siso_hien_tai trong UI sync với DB (đã được trigger update). Trước cache giữ value cũ → user thấy số sai dù DB đúng
- [x] Bỏ field "Sĩ số hiện tại" khỏi dialog Admin add class (siso_hien_tai luôn = 0 lúc tạo, trigger DB tự update khi có register). Tránh confusing UX "tôi vừa set 5 sao giờ thành 1?"
- [x] Dialog Admin EDIT class: làm `txt_siso` readonly + style xám + tooltip + KHÔNG gửi siso_hien_tai trong update API. Validation message rõ "Hiện đang có X HV, không thể đặt sĩ số tối đa < X"
- [x] Tighter `is_valid_phone_vn`: phải bắt đầu '0' (10 số) hoặc '+84/84' (11 số). Reject '1234567890' (trước đây chấp nhận). Update msg lỗi 3 chỗ rõ format yêu cầu
- [x] Apply `fmt_relative_date` cho GV notice list (sent_data) — trước fmt_date '%d/%m/%Y %H:%M', giờ "Vừa xong"/"5 phút trước" tương tự HV/Adm. Tổng 5 chỗ đã apply helper
- [x] Audit log table: user/role NULL (DB trigger logs) hiện "Hệ thống/Tự động" thay vì "—" → user phân biệt user-actions vs system-actions
- [x] Audit log description: thêm dấu tiếng Việt + map tên bảng → label thân thiện ('registrations'→'đăng ký khoá học', 'payments'→'thanh toán', 'grades'→'điểm', 'attendance'→'điểm danh'). Apply live + schema.sql cho fresh setup
- [x] Audit log action code → label tiếng Việt: `action_map` translate raw codes ('create_registrations'/'delete_payments'/...) → 'Tạo đăng ký'/'Hoàn tiền'/... cho hiển thị FE. Update `action_colors` map đầy đủ 11 labels (xanh/cam/đỏ phù hợp ngữ nghĩa). Trước user thấy raw "create_registrations" giờ thấy "Tạo đăng ký" nhìn dễ hiểu
- [x] Thêm nút Export CSV cho trang GV nhập điểm (header bar 90×32 ⬇ CSV bên cạnh Sync CC). GV xuất bảng điểm hiện tại (theo lớp đang chọn) ra file `diem_<ma_lop>.csv` qua helper `export_table_csv` đã có. Hoàn thiện coverage export: trước có Adm curriculum / Adm audit / Adm students / NV registrations / GV students, giờ thêm GV grades. Vẫn dùng utf-8-sig để Excel mở tiếng Việt OK
- [x] Helper `time_greeting()` — lời chào theo giờ (5-11h sáng, 11-13h trưa, 13-18h chiều, 18-22h tối, 22-5h khuya). Apply 4 windows: HV "Chào buổi sáng, {ten}" / GV "Chào buổi sáng, TS. {ten}" (dùng hoc_vi prefix nếu có, fallback "Thầy/Cô" thay vì giả định "thầy") / NV "Chào buổi sáng · Hôm nay: {date}" / Adm "Tổng quan · Chào buổi sáng". UX cá nhân hơn so với generic "Xin chào"
- [x] Helper `avatar_style(initials)` — sinh QSS background+color từ hash(initials), 8 màu pastel. Apply 4 sidebar avatar (HV/GV/NV/Adm) thay hardcode `COLORS["active_bg"]` đồng nhất. Mỗi user có màu cố định, đăng nhập multi-account dễ phân biệt avatar (DH=orange / LT=teal / UP=gold / AD=red)
- [x] Login Caps Lock warning: lblCapsWarn `⚠ Caps Lock đang bật` dưới txtPassword (màu cam). Detect qua Win32 `GetKeyState(0x14)` (Windows) + fallback `event.text().isupper() != shift_held`. EventFilter trên pw_field auto show/hide khi keypress + focus in/out
- [x] Helper `make_status_badge(text)` + `_status_normalize()` (NFD strip dấu) — pill widget có background màu phù hợp ngữ nghĩa. Map 19 trạng thái tiếng Việt + tiếng Anh: thanh toán (xanh/cam/đỏ), lớp/HK (open/closed/full/upcoming), điểm danh (present/late/absent/excused). Apply NV tblRegistrations cột trạng thái (giữ item text cho filter, thêm cellWidget badge). Trước chỉ có foreground color, giờ có pill background nhìn rõ ràng hơn
- [x] Apply `make_status_badge` cho HV tblCourses cột Trạng thái (Đã thanh toán / Hoàn thành / Chờ thanh toán) → đồng nhất visual với NV reg page. Bỏ logic phân tích substring 'thanh toán'/'chờ' inline (helper handle đầy đủ qua _STATUS_BADGE_MAP)
- [x] Extend `_STATUS_BADGE_MAP` thêm 8 keys (dang mo, sap toi, dang hoc, cho tt, da pass, pass, chua hoc, fail/rot) — coverage curriculum + GV student progress. Apply badge cho Adm tblSemesters cột 5 (Đang mở/Đã đóng/Sắp tới — pill xanh/xám/xanh dương) + GV tblTeacherStudents cột 5 (Đang học/Chờ TT — xanh dương/cam). Verified all 25 status texts match to colored badge, không còn rơi grey fallback
- [x] Đồng bộ Học phí input trong Admin EDIT class dialog: QLineEdit raw → QSpinBox với `setGroupSeparatorShown(True)` + suffix ` đ`, range 0-100M, step 100k. Trước user nhập "2500000" raw, giờ thấy "2.500.000 đ" tự động format giống Add class. UX nhất quán + giảm rủi ro typo số tiền
- [x] Xếp loại badge (8 grades A+/A/B+/B/C+/C/D/F) thêm vào `_STATUS_BADGE_MAP` với gradient màu — A+ xanh đậm, A xanh, B+ xanh dương đậm, B xanh dương, C+ vàng đậm, C vàng, D đỏ nhạt, F đỏ. Apply HV tblGrades cột 6 + GV tblTeacherGrades cột 7. Bỏ dict `grade_colors` duplicate ở 2 chỗ (helper handle). Thêm `removeCellWidget` cleanup ở GV grades render trước khi gán mới (tránh leak cell widget khi switch lớp)
- [x] NV register duplicate check message: trước hiện raw English "trạng thái: pending_payment" → giờ map sang tiếng Việt "Trạng thái hiện tại: Chờ thanh toán" + format multi-line + giải thích "mỗi học viên chỉ đăng ký 1 lần / lớp". UX rõ ràng hơn cho NV không cần biết status code DB
- [x] NV register check class-full trước khi POST: nếu siso_hien_tai >= siso_max → block + msg "Lớp X đã đủ sĩ số tối đa (Y/Z)". Bonus: cboClassEmp dropdown hiển thị suffix "⚠ ĐÃ ĐẦY" cho lớp full → NV thấy ngay không cần click vào. Helper `_fmt_cls_entry` reuse cho cả _fill_emp_register lẫn _emp_filter_classes
- [x] Highlight cột "Hôm nay" trong HV+GV schedule header: prefix `● ` + foreground navy + bold font. Khác cột giữ default xám. Apply cả `_load_student_schedule_week` lẫn `_load_teacher_schedule_week`. UX user nhìn calendar dễ định vị hôm nay khi nav qua nhiều tuần


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
