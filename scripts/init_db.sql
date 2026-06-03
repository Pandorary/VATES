-- Vates 数据库初始化 DDL
-- 开发模式使用 SQLite，此为参照用 PostgreSQL DDL

CREATE TABLE IF NOT EXISTS stocks (
    code VARCHAR(10) PRIMARY KEY,
    name VARCHAR(20),
    industry VARCHAR(50),
    list_date DATE
);

CREATE TABLE IF NOT EXISTS daily_quotes (
    code VARCHAR(10),
    trade_date DATE,
    open NUMERIC(10,3),
    high NUMERIC(10,3),
    low NUMERIC(10,3),
    close NUMERIC(10,3),
    volume BIGINT,
    amount NUMERIC(16,2),
    change_pct NUMERIC(6,2),
    turnover_rate NUMERIC(6,2),
    PRIMARY KEY (code, trade_date)
);

CREATE TABLE IF NOT EXISTS money_flow (
    code VARCHAR(10),
    trade_date DATE,
    main_net_inflow NUMERIC(14,2),
    super_large_net NUMERIC(14,2),
    PRIMARY KEY (code, trade_date)
);

CREATE TABLE IF NOT EXISTS limit_up_records (
    code VARCHAR(10),
    trade_date DATE,
    is_continuous INT,
    board_height INT,
    broken_rate NUMERIC(6,2),
    PRIMARY KEY (code, trade_date)
);

CREATE TABLE IF NOT EXISTS market_sentiment (
    trade_date DATE PRIMARY KEY,
    max_board_height INT,
    promotion_rate NUMERIC(6,4),
    bomb_rate NUMERIC(6,4),
    yesterday_limit_up_avg_return NUMERIC(6,2),
    market_status VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS market_config (
    id SERIAL PRIMARY KEY,
    param_name VARCHAR(50) UNIQUE NOT NULL,
    param_value NUMERIC NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO market_config (param_name, param_value, description) VALUES
    ('MAX_BOARD_ICE', 3, '最高连板低于此值可能为冰点'),
    ('BOMB_RATE_RETREAT', 0.4, '炸板率高于此值为退潮'),
    ('PROMOTION_HIGH', 0.4, '晋级率高于此值可能为高潮'),
    ('AVG_RETURN_HIGH', 1.0, '昨涨停今日均收高于此值高潮信号'),
    ('PROMOTION_WARM', 0.25, '晋级率高于此值回暖信号'),
    ('AVG_RETURN_WARM', 0, '昨涨停今日均收高于此值回暖信号'),
    ('MAX_BOARD_HIGH', 5, '最高连板大于等于此值高潮信号')
ON CONFLICT (param_name) DO NOTHING;

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    openid VARCHAR(100) UNIQUE,
    email VARCHAR(120) UNIQUE,
    nickname VARCHAR(50),
    avatar_url TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    agreed_disclaimer BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS user_watchlist (
    user_id INT REFERENCES users(id),
    code VARCHAR(10),
    added_at TIMESTAMP DEFAULT NOW(),
    in_observe_pool BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (user_id, code)
);

CREATE TABLE IF NOT EXISTS ai_prompts (
    id VARCHAR(36) PRIMARY KEY,
    scene VARCHAR(50) DEFAULT '',
    role VARCHAR(50) DEFAULT '',
    role_name VARCHAR(100) DEFAULT '',
    module VARCHAR(50) DEFAULT '',
    skill VARCHAR(50) DEFAULT '',
    skill_name VARCHAR(200) DEFAULT '',
    skill_summary VARCHAR(50) DEFAULT '',
    skill_detail TEXT DEFAULT '',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(50) DEFAULT '',
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by VARCHAR(50) DEFAULT '',
    is_deleted BOOLEAN DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_ai_prompts_scene ON ai_prompts(scene);

CREATE TABLE IF NOT EXISTS ai_call_logs (
    id VARCHAR(36) PRIMARY KEY,
    template_id VARCHAR(36) DEFAULT '',
    scene VARCHAR(50) DEFAULT '',
    input_summary VARCHAR(200) DEFAULT '',
    output_summary VARCHAR(200) DEFAULT '',
    confidence_label VARCHAR(10) DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS holdings (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL DEFAULT 1,
    code VARCHAR(10) NOT NULL,
    name VARCHAR(50) DEFAULT '',
    cost_price NUMERIC(10,3) NOT NULL DEFAULT 0,
    shares INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_holdings_user ON holdings(user_id);

CREATE TABLE IF NOT EXISTS prediction_records (
    id VARCHAR(36) PRIMARY KEY,
    user_id INT NOT NULL DEFAULT 1,
    type VARCHAR(10) NOT NULL,
    code VARCHAR(10) DEFAULT '',
    name VARCHAR(50) NOT NULL,
    horizon VARCHAR(20) DEFAULT '',
    prediction_content TEXT DEFAULT '',
    confidence_label VARCHAR(10) DEFAULT '',
    status VARCHAR(20) DEFAULT 'tracking',
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_prediction_user ON prediction_records(user_id);
CREATE INDEX IF NOT EXISTS idx_prediction_type ON prediction_records(type);

CREATE TABLE IF NOT EXISTS data_snapshots (
    id VARCHAR(36) PRIMARY KEY,
    prediction_id VARCHAR(36) NOT NULL,
    structured_data TEXT DEFAULT '{}',
    source_urls TEXT DEFAULT '[]',
    fetch_timestamp TIMESTAMP DEFAULT NOW(),
    confidence_label VARCHAR(10) DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_snapshot_pred ON data_snapshots(prediction_id);

CREATE TABLE IF NOT EXISTS review_records (
    id VARCHAR(36) PRIMARY KEY,
    prediction_id VARCHAR(36) NOT NULL,
    review_type VARCHAR(20) NOT NULL,
    accuracy_rating VARCHAR(20) DEFAULT '',
    deviation_reason VARCHAR(20) DEFAULT '',
    review_content TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_review_pred ON review_records(prediction_id);
