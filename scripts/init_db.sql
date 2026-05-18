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

CREATE TABLE IF NOT EXISTS trade_patterns (
    pattern_id SERIAL PRIMARY KEY,
    pattern_name VARCHAR(50),
    conditions_json JSONB,
    risk_tips TEXT
);

CREATE TABLE IF NOT EXISTS pattern_signals (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10),
    trade_date DATE,
    pattern_id INT,
    matched_details JSONB
);

CREATE TABLE IF NOT EXISTS pattern_backtest_cache (
    pattern_id INT,
    lookback_days INT,
    sample_count INT,
    win_rate NUMERIC(5,2),
    avg_gain NUMERIC(10,2),
    avg_loss NUMERIC(10,2),
    avg_pnl_ratio NUMERIC(5,2),
    updated_at TIMESTAMP,
    PRIMARY KEY (pattern_id, lookback_days)
);

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
