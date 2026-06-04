-- =====================================================================
-- BKMS Term Project — Personalized Nutrition Advisor (NL2SQL)
-- Schema for the two reference tables.
--
-- Row data is bulk-loaded from Excel via load_data.py (not seeded here).
-- db.py also creates this same schema on DB() init, so this file is a
-- standalone reference / manual-setup path.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 영양성분DB — per-food nutrient content (per serving as given in the source)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS 영양성분DB (
    식품명   VARCHAR(50) PRIMARY KEY,
    에너지   FLOAT,   -- kcal
    단백질   FLOAT,   -- g
    지방     FLOAT,   -- g
    탄수화물 FLOAT,   -- g
    나트륨   FLOAT    -- mg
);

-- ---------------------------------------------------------------------
-- 영양소조건 — recommended daily intake by sex and age band
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS 영양소조건 (
    성별        VARCHAR(50),
    연령대_하한  INT,
    연령대_상한  INT,
    에너지      FLOAT,   -- kcal
    단백질      FLOAT,   -- g
    지방        FLOAT,   -- g
    탄수화물    FLOAT,   -- g
    나트륨      FLOAT,   -- mg
    -- one row per (성별, 연령대) band → prevents duplicate inserts
    PRIMARY KEY (성별, 연령대_하한, 연령대_상한)
);
