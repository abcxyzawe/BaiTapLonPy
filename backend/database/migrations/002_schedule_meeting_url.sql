-- Migration 002: them cot meeting_url cho schedules
-- Khi: 2026-05-11
-- Why: Tich hop tinh nang day online - GV co the flag 1 buoi day la online
-- bang cach paste link Zoom/Meet/Jitsi. HV thay nut 'Tham gia' tren card lich.
-- Apply: chay 1 lan tren DB hien tai.

ALTER TABLE schedules
    ADD COLUMN IF NOT EXISTS meeting_url VARCHAR(500);

-- Format: bat ky URL nao (zoom.us / meet.google.com / jit.si / teams.microsoft.com / ...)
-- NULL = buoi offline tai phong vat ly. Co URL = buoi online.
