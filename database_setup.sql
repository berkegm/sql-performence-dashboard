-- ============================================================
-- Mobile Game Analytics Database — SQLite Schema & Seed Data
-- ============================================================
-- Run via Python (see app.py / queries.py) or directly:
--   sqlite3 game_analytics.db < database_setup.sql
-- ============================================================

PRAGMA foreign_keys = ON;

-- ── Tables ────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    user_id         TEXT PRIMARY KEY,
    country         TEXT NOT NULL,
    device_type     TEXT NOT NULL CHECK (device_type IN ('ios', 'android')),
    registration_dt TEXT NOT NULL   -- ISO-8601 date string
);

CREATE TABLE IF NOT EXISTS levels (
    level_id    INTEGER PRIMARY KEY,
    level_name  TEXT    NOT NULL,
    difficulty  TEXT    NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard')),
    unlock_req  INTEGER NOT NULL DEFAULT 0  -- min level required to unlock
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT    NOT NULL REFERENCES users(user_id),
    amount_usd  REAL    NOT NULL CHECK (amount_usd > 0),
    payment_dt  TEXT    NOT NULL,   -- ISO-8601 date string
    level_id    INTEGER REFERENCES levels(level_id),
    product     TEXT    NOT NULL    -- e.g. 'extra_lives', 'hint_pack', 'no_ads'
);

-- ── Indexes ───────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_payments_user   ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_dt     ON payments(payment_dt);
CREATE INDEX IF NOT EXISTS idx_users_country   ON users(country);

-- ── Levels (1–50) ─────────────────────────────────────────────

INSERT OR IGNORE INTO levels VALUES
  (1,'Level 1','easy',0),(2,'Level 2','easy',0),(3,'Level 3','easy',0),
  (4,'Level 4','easy',0),(5,'Level 5','easy',0),(6,'Level 6','easy',0),
  (7,'Level 7','easy',0),(8,'Level 8','easy',0),(9,'Level 9','easy',0),
  (10,'Level 10','easy',0),(11,'Level 11','medium',10),(12,'Level 12','medium',10),
  (13,'Level 13','medium',10),(14,'Level 14','medium',10),(15,'Level 15','medium',10),
  (16,'Level 16','medium',10),(17,'Level 17','medium',10),(18,'Level 18','medium',10),
  (19,'Level 19','medium',10),(20,'Level 20','medium',10),(21,'Level 21','medium',20),
  (22,'Level 22','medium',20),(23,'Level 23','medium',20),(24,'Level 24','medium',20),
  (25,'Level 25','medium',20),(26,'Level 26','hard',25),(27,'Level 27','hard',25),
  (28,'Level 28','hard',25),(29,'Level 29','hard',25),(30,'Level 30','hard',25),
  (31,'Level 31','hard',30),(32,'Level 32','hard',30),(33,'Level 33','hard',30),
  (34,'Level 34','hard',30),(35,'Level 35','hard',30),(36,'Level 36','hard',35),
  (37,'Level 37','hard',35),(38,'Level 38','hard',35),(39,'Level 39','hard',35),
  (40,'Level 40','hard',35),(41,'Level 41','hard',40),(42,'Level 42','hard',40),
  (43,'Level 43','hard',40),(44,'Level 44','hard',40),(45,'Level 45','hard',40),
  (46,'Level 46','hard',45),(47,'Level 47','hard',45),(48,'Level 48','hard',45),
  (49,'Level 49','hard',45),(50,'Level 50','hard',45);
