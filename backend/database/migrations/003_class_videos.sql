-- Migration 003: tao bang class_videos (thu vien video bai giang cua lop)
-- Khi: 2026-05-11
-- Why: GV upload link YouTube/Drive/Vimeo de HV xem lai bai giang khi vang
-- buoi hoc, hoac on tap. Khong upload video file (tot storage) -> chi URL.
-- Apply: chay 1 lan tren DB hien tai.

CREATE TABLE IF NOT EXISTS class_videos (
    id          SERIAL PRIMARY KEY,
    lop_id      VARCHAR(30) NOT NULL REFERENCES classes(ma_lop) ON DELETE CASCADE,
    gv_id       INTEGER NOT NULL REFERENCES teachers(user_id) ON DELETE CASCADE,
    tieu_de     VARCHAR(200) NOT NULL,
    video_url   VARCHAR(500) NOT NULL,
    mo_ta       TEXT,
    buoi_so     INTEGER,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cv_lop ON class_videos(lop_id);
CREATE INDEX IF NOT EXISTS idx_cv_gv ON class_videos(gv_id);
