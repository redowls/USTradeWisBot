-- USTradeWisBot schema (SQL Server). summary.md §6.
-- Idempotent: safe to run repeatedly. Run against the USTradeWisBot database.
--   sqlcmd -S localhost,1433 -U sa -P '***' -C -d USTradeWisBot -i sql/schema.sql

SET NOCOUNT ON;

-- watchlist — the US stocks the bot may analyze
IF OBJECT_ID('dbo.watchlist', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.watchlist (
        symbol    VARCHAR(10)   NOT NULL PRIMARY KEY,
        name      NVARCHAR(100) NULL,
        is_active BIT           NOT NULL DEFAULT 1,
        added_at  DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME(),
        notes     NVARCHAR(255) NULL
    );
END;

-- trades — one row per buy->sell round trip
IF OBJECT_ID('dbo.trades', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.trades (
        trade_id          BIGINT IDENTITY(1,1) PRIMARY KEY,
        symbol            VARCHAR(10)   NOT NULL,
        side              VARCHAR(4)    NOT NULL DEFAULT 'BUY',
        qty               INT           NOT NULL,
        entry_price       DECIMAL(12,4) NOT NULL,
        entry_time        DATETIME2     NOT NULL,
        stop_price        DECIMAL(12,4) NOT NULL,
        take_profit_price DECIMAL(12,4) NOT NULL,
        exit_price        DECIMAL(12,4) NULL,
        exit_time         DATETIME2     NULL,
        realized_pl       DECIMAL(12,4) NULL,
        realized_pl_pct   DECIMAL(8,4)  NULL,
        status            VARCHAR(12)   NOT NULL DEFAULT 'OPEN',
        exit_reason       VARCHAR(20)   NULL,
        alpaca_order_id   VARCHAR(64)   NULL,
        CONSTRAINT FK_trades_watchlist FOREIGN KEY (symbol)
            REFERENCES dbo.watchlist(symbol)
    );
    CREATE INDEX IX_trades_status ON dbo.trades(status);
    CREATE INDEX IX_trades_symbol ON dbo.trades(symbol);
END;

-- signals — WHY each trade was taken (explainability)
IF OBJECT_ID('dbo.signals', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.signals (
        signal_id      BIGINT IDENTITY(1,1) PRIMARY KEY,
        trade_id       BIGINT        NULL,
        symbol         VARCHAR(10)   NOT NULL,
        ts             DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME(),
        signal_type    VARCHAR(10)   NULL,
        confidence     DECIMAL(5,2)  NULL,
        breakout_score DECIMAL(5,4)  NULL,
        ma_score       DECIMAL(5,4)  NULL,
        value_score    DECIMAL(5,4)  NULL,
        momentum_score DECIMAL(5,4)  NULL,
        regime_ok      BIT           NULL,
        broke_level    DECIMAL(12,4) NULL,
        CONSTRAINT FK_signals_trades FOREIGN KEY (trade_id)
            REFERENCES dbo.trades(trade_id)
    );
    CREATE INDEX IX_signals_symbol_ts ON dbo.signals(symbol, ts);
END;

-- daily_summary — per-day P&L recap
IF OBJECT_ID('dbo.daily_summary', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.daily_summary (
        trade_date      DATE          NOT NULL PRIMARY KEY,
        num_buys        INT           NOT NULL DEFAULT 0,
        num_sells       INT           NOT NULL DEFAULT 0,
        wins            INT           NOT NULL DEFAULT 0,
        losses          INT           NOT NULL DEFAULT 0,
        gross_pl        DECIMAL(14,4) NULL,
        realized_pl_pct DECIMAL(8,4)  NULL,
        equity_open     DECIMAL(14,4) NULL,
        equity_close    DECIMAL(14,4) NULL,
        symbols_traded  NVARCHAR(255) NULL
    );
END;

PRINT 'USTradeWisBot schema ready.';
