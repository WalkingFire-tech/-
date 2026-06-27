-- 004_versioned_fact_store.sql
-- 事实库版本控制迁移
-- 支持知识版本追溯、覆盖机制、冲突解决

-- 主事实表（支持版本控制）
CREATE TABLE IF NOT EXISTS fact_assertions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object TEXT NOT NULL,
    question_hash TEXT NOT NULL,
    question TEXT,
    source TEXT NOT NULL,               -- 'seed', 'correction', 'learning', 'external', 'manual'
    confidence REAL DEFAULT 0.8,
    is_seed BOOLEAN DEFAULT 0,
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT 1,
    superseded_by INTEGER DEFAULT NULL, -- 被哪个新版本覆盖
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_fact_qhash_active ON fact_assertions(question_hash, is_active);
CREATE INDEX IF NOT EXISTS idx_fact_subject_predicate ON fact_assertions(subject, predicate);
CREATE INDEX IF NOT EXISTS idx_fact_superseded ON fact_assertions(superseded_by);
CREATE INDEX IF NOT EXISTS idx_fact_source ON fact_assertions(source);
CREATE INDEX IF NOT EXISTS idx_fact_version ON fact_assertions(version);

-- 验证记录表
CREATE TABLE IF NOT EXISTS injection_verifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assertion_id INTEGER REFERENCES fact_assertions(id),
    question TEXT NOT NULL,
    old_score REAL,
    new_score REAL,
    improvement REAL,
    status TEXT DEFAULT 'pending',     -- 'pending', 'verified', 'rejected'
    verified_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 决策链记录表
CREATE TABLE IF NOT EXISTS decision_chains (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    question TEXT,
    response TEXT,
    chain_data TEXT,                    -- JSON格式存储各层决策
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 纠错历史表
CREATE TABLE IF NOT EXISTS correction_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_hash TEXT NOT NULL,
    old_assertion_id INTEGER,
    new_assertion_id INTEGER,
    old_content TEXT,
    new_content TEXT,
    correction_source TEXT,
    confidence_before REAL,
    confidence_after REAL,
    corrected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 置信度衰减日志
CREATE TABLE IF NOT EXISTS confidence_decay_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assertion_id INTEGER NOT NULL,
    old_confidence REAL,
    new_confidence REAL,
    reason TEXT,
    decayed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);