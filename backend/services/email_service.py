"""Email service - gui thong bao qua Gmail SMTP.

Co che:
- Background thread: send_bulk_async() spawn thread rieng, KHONG block API.
- Graceful fallback: neu chua config SMTP (SMTP_USER/SMTP_PASS rong) -> log
  warning va bo qua, KHONG raise (API van tra ve binh thuong).
- 1 SMTP connection cho ca batch -> nhanh hon mo connection moi email.

Config qua bien moi truong (.env hoac set truc tiep):
    SMTP_HOST       (default smtp.gmail.com)
    SMTP_PORT       (default 587)
    SMTP_USER       email Gmail dung de gui
    SMTP_PASS       App Password 16 ky tu (KHONG phai mat khau Gmail thuong)
    SMTP_FROM_NAME  ten hien thi nguoi gui (default 'Trung tam Ngoai khoa EAUT')
"""
import os
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr

# Load .env truoc khi doc os.getenv - phong truong hop module nay duoc import
# truoc db.py (db.py cung load_dotenv). load_dotenv idempotent nen goi lai OK.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from backend.database.db import db

SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASS = os.getenv('SMTP_PASS', '')
SMTP_FROM_NAME = os.getenv('SMTP_FROM_NAME', 'Trung tâm Ngoại khoá EAUT')

# Mau EAUT cho email template
_NAVY = '#002060'
_ORANGE = '#c05621'


def is_configured() -> bool:
    """True neu da set SMTP_USER + SMTP_PASS."""
    return bool(SMTP_USER and SMTP_PASS)


# ============ LOOKUP EMAIL NGUOI NHAN ============

def get_class_student_emails(lop_id: str):
    """[(email, full_name)] cua HV dang ky lop (status active, co email)."""
    if not lop_id:
        return []
    sql = """
        SELECT DISTINCT u.email, u.full_name
          FROM registrations r
          JOIN users u ON u.id = r.hv_id
         WHERE r.lop_id = %s
           AND r.trang_thai IN ('paid', 'pending_payment', 'completed')
           AND u.email IS NOT NULL AND u.email <> ''
           AND u.is_active = TRUE
    """
    try:
        return [(r['email'], r['full_name']) for r in db.fetch_all(sql, (lop_id,))]
    except Exception as e:
        print(f'[EMAIL] Loi lookup email lop {lop_id}: {e}')
        return []


def get_all_student_emails():
    """[(email, full_name)] cua TAT CA HV active co email - cho broadcast."""
    sql = """
        SELECT u.email, u.full_name
          FROM users u
          JOIN students s ON s.user_id = u.id
         WHERE u.email IS NOT NULL AND u.email <> ''
           AND u.is_active = TRUE
    """
    try:
        return [(r['email'], r['full_name']) for r in db.fetch_all(sql)]
    except Exception as e:
        print(f'[EMAIL] Loi lookup all student emails: {e}')
        return []


def get_one_student_email(hv_id: int):
    """[(email, full_name)] cua 1 HV - cho notification gui rieng."""
    try:
        row = db.fetch_one(
            "SELECT email, full_name FROM users WHERE id = %s AND is_active = TRUE",
            (hv_id,)
        )
        if row and row.get('email'):
            return [(row['email'], row['full_name'])]
    except Exception as e:
        print(f'[EMAIL] Loi lookup email HV {hv_id}: {e}')
    return []


# ============ EMAIL TEMPLATES (HTML) ============

def _wrap_html(title: str, body_inner: str) -> str:
    """Khung email chung - header navy EAUT + footer."""
    return f"""\
<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0; padding:0; background:#edf2f7; font-family:Arial,sans-serif;">
  <div style="max-width:600px; margin:0 auto; padding:20px;">
    <div style="background:{_NAVY}; padding:20px 24px; border-radius:8px 8px 0 0;">
      <div style="color:white; font-size:18px; font-weight:bold;">
        🎓 Trung tâm Ngoại khoá EAUT
      </div>
      <div style="color:rgba(255,255,255,0.75); font-size:12px; margin-top:2px;">
        {title}
      </div>
    </div>
    <div style="background:white; padding:24px; border-radius:0 0 8px 8px;
                border:1px solid #d2d6dc; border-top:none;">
      {body_inner}
    </div>
    <div style="text-align:center; color:#a0aec0; font-size:11px; padding:14px;">
      Email tự động từ hệ thống đăng ký khoá học EAUT.<br>
      Vui lòng không trả lời email này.
    </div>
  </div>
</body></html>"""


def render_assignment_email(tieu_de, mo_ta, han_nop, lop_id, ten_mon, ten_gv) -> str:
    """Template email cho bai tap moi."""
    han_str = str(han_nop) if han_nop else 'Không có hạn nộp'
    mo_ta_html = (mo_ta or '').replace('\n', '<br>') or '<i>(không có mô tả)</i>'
    inner = f"""\
      <div style="font-size:15px; font-weight:bold; color:{_ORANGE}; margin-bottom:4px;">
        📝 Bài tập mới
      </div>
      <div style="font-size:17px; font-weight:bold; color:#1a1a2e; margin-bottom:14px;">
        {tieu_de}
      </div>
      <table style="width:100%; font-size:13px; color:#4a5568; border-collapse:collapse;">
        <tr><td style="padding:5px 0; width:110px;"><b>Lớp:</b></td>
            <td>{lop_id} — {ten_mon or '—'}</td></tr>
        <tr><td style="padding:5px 0;"><b>Giảng viên:</b></td>
            <td>{ten_gv or '—'}</td></tr>
        <tr><td style="padding:5px 0; color:{_ORANGE};"><b>Hạn nộp:</b></td>
            <td style="color:{_ORANGE}; font-weight:bold;">{han_str}</td></tr>
      </table>
      <div style="margin-top:14px; padding:12px; background:#f7fafc;
                  border-left:3px solid {_NAVY}; border-radius:4px;
                  font-size:13px; color:#1a1a2e;">
        <b>Nội dung yêu cầu:</b><br>{mo_ta_html}
      </div>
      <div style="margin-top:16px; font-size:12px; color:#718096;">
        Đăng nhập ứng dụng EAUT → trang <b>Bài tập</b> để xem chi tiết và nộp bài.
      </div>"""
    return _wrap_html('Thông báo bài tập', inner)


def render_grade_email(tieu_de, diem, diem_toi_da, nhan_xet, ten_mon) -> str:
    """Template email thong bao co diem bai tap moi cham."""
    nhan_xet_html = (nhan_xet or '').replace('\n', '<br>') or '<i>(Không có nhận xét)</i>'
    inner = f"""\
      <div style="font-size:15px; font-weight:bold; color:green; margin-bottom:4px;">
        ✅ Đã chấm bài tập
      </div>
      <div style="font-size:17px; font-weight:bold; color:#1a1a2e; margin-bottom:14px;">
        {tieu_de}
      </div>
      <table style="width:100%; font-size:13px; color:#4a5568; border-collapse:collapse;">
        <tr><td style="padding:5px 0; width:110px;"><b>Môn học:</b></td>
            <td>{ten_mon or '—'}</td></tr>
        <tr><td style="padding:5px 0; color:green;"><b>Điểm số:</b></td>
            <td style="color:green; font-weight:bold; font-size:15px;">{diem} / {diem_toi_da}</td></tr>
      </table>
      <div style="margin-top:14px; padding:12px; background:#f7fafc;
                  border-left:3px solid green; border-radius:4px;
                  font-size:13px; color:#1a1a2e;">
        <b>Lời nhận xét từ Giảng viên:</b><br>{nhan_xet_html}
      </div>
      <div style="margin-top:16px; font-size:12px; color:#718096;">
        Đăng nhập ứng dụng EAUT → trang <b>Bài tập</b> để xem chi tiết bài làm của bạn.
      </div>"""
    return _wrap_html('Thông báo kết quả bài tập', inner)


def render_notification_email(tieu_de, noi_dung, ten_nguoi_gui, vai_tro) -> str:
    """Template email cho thong bao tu GV/Admin."""
    role_vn = {'teacher': 'Giảng viên', 'admin': 'Quản trị viên',
               'employee': 'Nhân viên'}.get(vai_tro, vai_tro or 'Hệ thống')
    noi_dung_html = (noi_dung or '').replace('\n', '<br>')
    inner = f"""\
      <div style="font-size:15px; font-weight:bold; color:{_NAVY}; margin-bottom:4px;">
        🔔 Thông báo mới
      </div>
      <div style="font-size:17px; font-weight:bold; color:#1a1a2e; margin-bottom:6px;">
        {tieu_de}
      </div>
      <div style="font-size:12px; color:#718096; margin-bottom:14px;">
        Từ: <b>{ten_nguoi_gui}</b> ({role_vn})
      </div>
      <div style="padding:12px; background:#f7fafc;
                  border-left:3px solid {_NAVY}; border-radius:4px;
                  font-size:13px; color:#1a1a2e; line-height:1.5;">
        {noi_dung_html}
      </div>
      <div style="margin-top:16px; font-size:12px; color:#718096;">
        Đăng nhập ứng dụng EAUT → trang <b>Thông báo</b> để xem tất cả.
      </div>"""
    return _wrap_html('Thông báo từ trung tâm', inner)


# ============ GUI EMAIL ============

def _build_msg(to_email, to_name, subject, body_html):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = formataddr((SMTP_FROM_NAME, SMTP_USER))
    msg['To'] = formataddr((to_name or '', to_email))
    msg.attach(MIMEText(body_html, 'html', 'utf-8'))
    return msg


def _send_bulk_worker(recipients, subject, body_html):
    """Chay trong background thread - mo 1 SMTP connection gui ca batch.

    Note: print message KHONG dau (ASCII) - Windows console cp1252 khong
    encode duoc ky tu Unicode tieng Viet, se UnicodeEncodeError trong thread.
    """
    if not is_configured():
        print('[EMAIL] Chua cau hinh SMTP (SMTP_USER/SMTP_PASS) - bo qua gui email.')
        return
    if not recipients:
        return
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            ok = 0
            for email, name in recipients:
                try:
                    server.send_message(_build_msg(email, name, subject, body_html))
                    ok += 1
                except Exception as e:
                    print(f'[EMAIL] Loi gui toi {email}: {e}')
            print(f'[EMAIL] Da gui {ok}/{len(recipients)} email - subject: {subject!r}')
    except Exception as e:
        print(f'[EMAIL] Loi ket noi SMTP: {e}')


def send_bulk_async(recipients, subject, body_html):
    """Gui email cho danh sach recipients trong background thread.

    Args:
        recipients: list of (email, full_name)
        subject: tieu de email
        body_html: noi dung HTML

    Return ngay lap tuc - khong block caller. An toan goi tu API endpoint.
    """
    if not recipients:
        return
    t = threading.Thread(
        target=_send_bulk_worker,
        args=(list(recipients), subject, body_html),
        daemon=True,
    )
    t.start()
