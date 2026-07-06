-- ─────────────────────────────────────────────────────────────
-- Migration: Add Gemini AI result columns to labourers table
-- Run this ONCE on existing databases.
-- ─────────────────────────────────────────────────────────────

ALTER TABLE labourers
    ADD COLUMN IF NOT EXISTS ai_auth_notes TEXT NULL AFTER face_encoding,
    ADD COLUMN IF NOT EXISTS ai_val_notes  TEXT NULL AFTER ai_auth_notes;
