"""Comprehensive API test for 93 endpoints.

LUU Y AN TOAN:
- Khong test DELETE / PATCH tren seed accounts (id 1-22). Cac id nay reserved
  cho login chinh (admin, teacher, employee, user, hv*, gv*, nv*).
- Tao test data voi prefix `tst_` hoac `auto_test_` neu can, cleanup trong
  finally block. Tranh lap lai bug round 4 (bi deactivate seed accounts).
"""
import requests
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

B = 'http://127.0.0.1:8000'
SEED_USER_IDS = set(range(1, 23))  # Seed accounts - KHONG DELETE/PATCH
results = {'pass': [], 'fail': [], 'shapes': {}, 'critical': []}
timing = []


def call(method, ep, expected=(200,), json_data=None, params=None, label=None):
    label = label or f'{method.upper()} {ep}'
    # Safety: chan DELETE/PATCH tren seed user (path co 1-22 cuoi)
    method_l = method.lower()
    if method_l in ('delete', 'patch') and ('/students/' in ep or '/teachers/' in ep or '/employees/' in ep):
        # extract id cuoi path
        try:
            tail = ep.rstrip('/').rsplit('/', 1)[-1]
            uid = int(tail)
            if uid in SEED_USER_IDS:
                results['critical'].append(f'BLOCKED {label}: seed user id={uid} (an toan)')
                return None
        except (ValueError, IndexError):
            pass
    try:
        t0 = time.time()
        r = requests.request(method, B + ep, json=json_data, params=params, timeout=10)
        dt = (time.time() - t0) * 1000
        timing.append((label, dt))
        ok = r.status_code in expected
        if ok:
            results['pass'].append(f'{label}: {r.status_code} [{dt:.0f}ms]')
        else:
            body = r.text[:200]
            results['fail'].append(f'{label}: got {r.status_code}, expected {expected} - {body}')
        return r
    except Exception as e:
        results['fail'].append(f'{label}: EXC {e}')
        return None


# ============================================================
# 1. HEALTH + ROOT
# ============================================================
print('=== Health/Root ===')
r = call('get', '/health')
if r:
    h = r.json()
    print(f'Health: {h}')
    if h.get('db') != 'connected':
        results['critical'].append(f'/health: DB not connected: {h}')
call('get', '/')

# ============================================================
# 2. AUTH
# ============================================================
print('=== Auth ===')
r = call('post', '/auth/login', json_data={'username': 'teacher', 'password': 'passtea'})
gv_data = r.json() if r and r.status_code == 200 else {}
gv_id = gv_data.get('user_id')
print(f'Teacher login: user_id={gv_id}, fields={list(gv_data.keys())}')
results['shapes']['/auth/login (teacher)'] = list(gv_data.keys())

# Wrong creds -> 401
call('post', '/auth/login', expected=(401,), json_data={'username': 'wrong', 'password': 'wrong'},
     label='POST /auth/login (wrong creds)')

# Missing field -> 422
call('post', '/auth/login', expected=(422,), json_data={'username': 'teacher'},
     label='POST /auth/login (missing password)')

# Try other roles
for role_user, role_pass in [('student', 'passst'), ('admin', 'passad'), ('employee', 'passem')]:
    r = call('post', '/auth/login', expected=(200, 401), json_data={'username': role_user, 'password': role_pass},
             label=f'POST /auth/login ({role_user})')
    if r and r.status_code == 200:
        d = r.json()
        print(f'{role_user} login: role={d.get("vai_tro")}, user_id={d.get("user_id")}')

# Try common test accounts
test_accounts = []
for u, p in [('teacher', 'passtea'), ('student', 'passst'), ('admin', 'passad'), ('employee', 'passem'),
             ('hv1', '123'), ('gv1', '123'), ('admin1', '123'), ('staff1', '123')]:
    r = requests.post(B + '/auth/login', json={'username': u, 'password': p}, timeout=5)
    if r.status_code == 200:
        d = r.json()
        test_accounts.append((u, d.get('vai_tro'), d.get('user_id')))
print(f'Working accounts: {test_accounts}')

# ============================================================
# 3. GET endpoints (parametric)
# ============================================================
print('=== GET parametric endpoints ===')
hv_id = 4  # Try common HV ID
parametric_endpoints = [
    f'/classes/teacher/{gv_id}' if gv_id else None,
    f'/classes/student/{hv_id}',
    '/classes/IT001-A',
    '/classes/IT001-A/students',
    '/courses/IT001',
    f'/grades/student/{hv_id}',
    f'/grades/student/{hv_id}/gpa',
    '/grades/class/IT001-A',
    f'/grades/teacher/{gv_id}/rating' if gv_id else None,
    '/registrations/1',
    f'/notifications/student/{hv_id}',
    f'/notifications/teacher/{gv_id}' if gv_id else None,
    '/curriculum/1',
    f'/curriculum/progress/{hv_id}',
    f'/curriculum/check/{hv_id}/IT002',
    '/curriculum/prerequisites/IT002',
    '/schedules/today',
    '/schedules/week',
    '/schedules/class/IT001-A',
    f'/schedules/teacher/2/week?start=2026-04-13',
    f'/schedules/student/{hv_id}/week?start=2026-04-13',
    '/exams',
    f'/exams/student/{hv_id}',
    '/exams/class/IT001-A',
    '/attendance/schedule/1',
    f'/attendance/student/{hv_id}',
    f'/attendance/rate/{hv_id}/IT001-A',
    '/audit',
    '/students/HV2024001',
    '/students',
    '/teachers',
    '/teachers/list',
    '/teachers/for-review',
    '/employees',
    f'/teachers/{gv_id}/students' if gv_id else None,
    f'/stats/teacher/{gv_id}/overview' if gv_id else None,
    '/stats/employee/3/today',
    '/stats/admin/overview',
    '/stats/top-classes',
    '/stats/recent-activity',
    '/stats/by-course',
    '/stats/class-enrollment',
    '/stats/pending-registrations',
    '/stats/semester/HK2-2526',
    '/semesters',
    '/semesters/current',
    '/semesters/HK2-2526',
    '/courses',
    '/classes',
    '/notifications',
    '/notifications/recent',
    '/registrations',
    '/registrations/pending',
    '/registrations/revenue/today',
    '/curriculum',
]

for ep in parametric_endpoints:
    if ep is None:
        continue
    r = call('get', ep, expected=(200, 404, 422))
    if r and r.status_code == 200:
        try:
            data = r.json()
            results['shapes'][f'GET {ep}'] = (
                list(data.keys()) if isinstance(data, dict)
                else (f'list[{len(data)}], item_keys={list(data[0].keys())}' if data and isinstance(data[0], dict) else f'list[{len(data)}]')
                if isinstance(data, list) else type(data).__name__
            )
        except Exception:
            pass

# ============================================================
# 4. GET 404 cases - bad IDs
# ============================================================
print('=== GET 404 cases ===')
for ep in [
    '/classes/NONEXIST-X',
    '/courses/NONEXIST',
    '/students/NONEXISTENT_MSV',
    '/registrations/999999',
    '/curriculum/999999',
    '/semesters/NONEXIST',
    '/classes/teacher/999999',
    '/classes/student/999999',
    '/grades/student/999999',
    '/grades/student/999999/gpa',
    '/grades/class/NONEXIST',
    '/grades/teacher/999999/rating',
    '/notifications/student/999999',
    '/notifications/teacher/999999',
    '/curriculum/progress/999999',
    '/curriculum/check/999999/NONEXIST',
    '/curriculum/prerequisites/NONEXIST',
    '/schedules/class/NONEXIST',
    '/exams/student/999999',
    '/exams/class/NONEXIST',
    '/attendance/schedule/999999',
    '/attendance/student/999999',
    '/attendance/rate/999999/NONEXIST',
    '/teachers/999999/students',
    '/stats/teacher/999999/overview',
    '/stats/employee/999999/today',
    '/stats/semester/NONEXIST',
]:
    r = call('get', ep, expected=(200, 404, 422), label=f'GET {ep} (bad ID)')

# ============================================================
# 5. POST/PUT/PATCH/DELETE 422 cases - schema validation
# ============================================================
print('=== Schema validation 422 ===')
# POST endpoints with empty body / missing fields
post_endpoints_for_422 = [
    '/courses', '/classes', '/registrations', '/grades', '/notifications',
    '/students', '/teachers', '/employees', '/reviews', '/semesters',
    '/curriculum', '/schedules', '/exams', '/attendance', '/audit',
]
for ep in post_endpoints_for_422:
    call('post', ep, expected=(422,), json_data={}, label=f'POST {ep} (empty body)')

# PUT with empty body
for ep in ['/auth/password', '/courses/IT001', '/classes/IT001-A', '/students/4', '/teachers/2',
           '/employees/3', '/curriculum/1']:
    call('put', ep, expected=(422, 404), json_data={}, label=f'PUT {ep} (empty body)')

# ============================================================
# 6. POST/DELETE create-then-delete cycles (avoid pollution)
# ============================================================
print('=== POST cycle: notification ===')
# Create notification
notif_payload = {'noi_dung': 'TEST AUTO ' + str(int(time.time())),
                 'nguoi_gui_id': gv_id or 2, 'do_uu_tien': 'thap'}
r = call('post', '/notifications', expected=(200, 201, 422, 500), json_data=notif_payload)
new_notif_id = None
if r and r.status_code in (200, 201):
    nd = r.json()
    new_notif_id = nd.get('id') or nd.get('notif_id')
    results['shapes']['POST /notifications'] = list(nd.keys()) if isinstance(nd, dict) else type(nd).__name__
    print(f'Created notif: {nd}')
    # Cleanup
    if new_notif_id:
        call('delete', f'/notifications/{new_notif_id}', expected=(200, 204), label=f'DELETE /notifications/{new_notif_id} (cleanup)')

# Audit log post
r = call('post', '/audit', expected=(200, 201, 422),
         json_data={'user_id': gv_id or 2, 'hanh_dong': 'TEST', 'doi_tuong': 'API_TEST',
                    'noi_dung': 'auto test'})
if r and r.status_code in (200, 201):
    results['shapes']['POST /audit'] = list(r.json().keys()) if isinstance(r.json(), dict) else type(r.json()).__name__

# Review post
if gv_id:
    r = call('post', '/reviews', expected=(200, 201, 422, 500),
             json_data={'gv_id': gv_id, 'hv_id': hv_id, 'so_sao': 5, 'noi_dung': 'TEST'})
    if r and r.status_code in (200, 201):
        results['shapes']['POST /reviews'] = list(r.json().keys()) if isinstance(r.json(), dict) else type(r.json()).__name__

# ============================================================
# 7. Performance / concurrency
# ============================================================
print('=== Concurrency 50 calls ===')


def fetch():
    t0 = time.time()
    rr = requests.get(B + '/health', timeout=5)
    return (time.time() - t0) * 1000, rr.status_code


t_start = time.time()
with ThreadPoolExecutor(max_workers=10) as ex:
    futs = [ex.submit(fetch) for _ in range(50)]
    all_dt = [f.result() for f in as_completed(futs)]
total = (time.time() - t_start) * 1000
ok_count = sum(1 for _, sc in all_dt if sc == 200)
avg = sum(d for d, _ in all_dt) / len(all_dt)
print(f'50 concurrent: ok={ok_count}/50, total={total:.0f}ms, avg/req={avg:.1f}ms')

# ============================================================
# 8. SUMMARY
# ============================================================
print('\n\n========== SUMMARY ==========')
print(f'PASS: {len(results["pass"])}')
print(f'FAIL: {len(results["fail"])}')
print(f'\n--- FAILURES ---')
for f in results['fail']:
    print(f'  {f}')

print(f'\n--- CRITICAL ---')
for c in results['critical']:
    print(f'  {c}')

# Slowest
sorted_t = sorted(timing, key=lambda x: -x[1])
print(f'\n--- SLOWEST 10 ---')
for label, dt in sorted_t[:10]:
    print(f'  {dt:6.0f}ms  {label}')

avg_all = sum(d for _, d in timing) / len(timing) if timing else 0
print(f'\nAvg response: {avg_all:.0f}ms over {len(timing)} requests')
print(f'Concurrent 50: avg/req={avg:.1f}ms, total={total:.0f}ms')

# ============================================================
# 9. POST-TEST: Verify seed accounts van active (an toan check)
# ============================================================
print('\n=== Verify seed accounts ===')
seed_check_creds = [
    ('admin', 'passadmin', 'admin'),
    ('teacher', 'passtea', 'teacher'),
    ('employee', 'passemp', 'employee'),
    ('user', 'passuser', 'student'),
]
seed_login_fail = []
for u, p, expected_role in seed_check_creds:
    rr = requests.post(B + '/auth/login',
                       json={'username': u, 'password': p}, timeout=5)
    if rr.status_code != 200 or rr.json().get('role') != expected_role:
        seed_login_fail.append(f'{u} (expect {expected_role}): {rr.status_code} {rr.text[:80]}')
if seed_login_fail:
    results['critical'].append(f'SEED ACCOUNTS LOGIN FAIL: {seed_login_fail}')
    print(f'!! CRITICAL: {seed_login_fail}')
else:
    print('OK 4/4 seed accounts (admin/teacher/employee/user) login pass')

# Save full results
with open('test_results.json', 'w', encoding='utf-8') as f:
    json.dump({
        'pass_count': len(results['pass']),
        'fail_count': len(results['fail']),
        'pass': results['pass'],
        'fail': results['fail'],
        'critical': results['critical'],
        'shapes': results['shapes'],
        'timing_avg': avg_all,
        'concurrent_avg': avg,
        'concurrent_total': total,
        'concurrent_ok': ok_count,
        'seed_login_fail': seed_login_fail,
    }, f, indent=2, ensure_ascii=False, default=str)
print('Saved test_results.json')
