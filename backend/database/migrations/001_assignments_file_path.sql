-- Migration 001: them cot file_path cho assignments
-- Khi: 2026-05-09
-- Why: GV co the dinh kem file (anh/word/pdf) khi giao bai, thay vi chi text
-- Apply: chay 1 lan tren DB hien tai (DB moi se co cot nay tu schema.sql)

ALTER TABLE assignments
    ADD COLUMN IF NOT EXISTS file_path VARCHAR(500);

-- file_path luu duong dan relative tu backend/uploads/assignments/
-- vd: 'assignments/2026-05-09_HK2-2526_BaitapTuan3_abc.pdf'
-- Frontend mo file qua os.startfile() / QDesktopServices.openUrl()
