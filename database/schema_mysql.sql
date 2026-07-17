-- ================================================================
-- 文件名: schema_mysql.sql
-- 功能说明: 多巴胺行情终端 MySQL 完整建表脚本
--          含用户系统、自选股、持仓、交易、配置等全部表结构
--          含索引、字段注释、初始化测试数据
-- 使用方式: 在 HeidiSQL / Navicat 中连接 MySQL 后执行此脚本
-- HeidiSQL 连接信息:
--   主机: 127.0.0.1
--   端口: 3306
--   用户: root
--   密码: 你的MySQL密码
--   数据库: investment_app
-- 字符集:   utf8mb4 (支持中文和 Emoji 等四字节字符)
-- ================================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS `investment_app`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE `investment_app`;

-- ==================== 用户表 ====================
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
    `id`              INT AUTO_INCREMENT PRIMARY KEY COMMENT '用户ID',
    `username`        VARCHAR(50)  NOT NULL UNIQUE COMMENT '用户名（登录用）',
    `password_hash`   VARCHAR(255) NOT NULL COMMENT '密码哈希值（werkzeug sha256）',
    `email`           VARCHAR(100) DEFAULT '' COMMENT '邮箱',
    `role`            VARCHAR(20)  DEFAULT 'user' COMMENT '角色(admin/user)',
    `is_active`       TINYINT(1)   DEFAULT 1 COMMENT '账号是否启用(0禁用/1启用)',
    `last_login`      DATETIME     DEFAULT NULL COMMENT '最后登录时间',
    `last_ip`         VARCHAR(45)  DEFAULT '' COMMENT '最后登录IP',
    `created_at`      DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
    `updated_at`      DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_username` (`username`),
    INDEX `idx_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- ==================== 股票基础信息表 ====================
DROP TABLE IF EXISTS `stock_basic`;
CREATE TABLE `stock_basic` (
    `id`              INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    `code`            VARCHAR(10)  NOT NULL UNIQUE COMMENT '股票代码，如 600519',
    `name`            VARCHAR(50)  NOT NULL COMMENT '股票名称',
    `market`          VARCHAR(10)  DEFAULT '' COMMENT '市场(SH=沪市/SZ=深市/BJ=北交所)',
    `industry`        VARCHAR(50)  DEFAULT '' COMMENT '所属行业',
    `list_date`       DATE         DEFAULT NULL COMMENT '上市日期',
    `is_deleted`      TINYINT(1)   DEFAULT 0 COMMENT '逻辑删除标识(0正常/1删除)',
    `created_at`      DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at`      DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_code` (`code`),
    INDEX `idx_market` (`market`),
    INDEX `idx_industry` (`industry`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票基础信息表';

-- ==================== 日线K线数据表 ====================
DROP TABLE IF EXISTS `stock_daily_kline`;
CREATE TABLE `stock_daily_kline` (
    `id`              BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    `stock_code`      VARCHAR(10)  NOT NULL COMMENT '股票代码',
    `trade_date`      DATE         NOT NULL COMMENT '交易日期',
    `open`            DECIMAL(10,3) NOT NULL COMMENT '开盘价',
    `close`           DECIMAL(10,3) NOT NULL COMMENT '收盘价',
    `high`            DECIMAL(10,3) NOT NULL COMMENT '最高价',
    `low`             DECIMAL(10,3) NOT NULL COMMENT '最低价',
    `volume`          BIGINT       DEFAULT 0 COMMENT '成交量(股)',
    `amount`          DECIMAL(18,2) DEFAULT 0 COMMENT '成交额(元)',
    `amplitude`       DECIMAL(8,2) DEFAULT 0 COMMENT '振幅(%)',
    `change_pct`      DECIMAL(8,2) DEFAULT 0 COMMENT '涨跌幅(%)',
    `turnover`        DECIMAL(8,2) DEFAULT 0 COMMENT '换手率(%)',
    `created_at`      DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE KEY `uk_code_date` (`stock_code`, `trade_date`),
    INDEX `idx_code` (`stock_code`),
    INDEX `idx_date` (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='日线K线数据表';

-- ==================== 分时数据表 ====================
DROP TABLE IF EXISTS `stock_minute_data`;
CREATE TABLE `stock_minute_data` (
    `id`              BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    `stock_code`      VARCHAR(10)  NOT NULL COMMENT '股票代码',
    `trade_time`      DATETIME     NOT NULL COMMENT '交易时间',
    `price`           DECIMAL(10,3) NOT NULL COMMENT '当前价',
    `volume`          BIGINT       DEFAULT 0 COMMENT '成交量(股)',
    `amount`          DECIMAL(18,2) DEFAULT 0 COMMENT '成交额(元)',
    `avg_price`       DECIMAL(10,3) DEFAULT 0 COMMENT '均价',
    `created_at`      DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX `idx_code_time` (`stock_code`, `trade_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='分时数据表';

-- ==================== 自选股表 ====================
DROP TABLE IF EXISTS `watchlist`;
CREATE TABLE `watchlist` (
    `id`              INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    `stock_code`      VARCHAR(10)  NOT NULL COMMENT '股票代码',
    `stock_name`      VARCHAR(50)  NOT NULL COMMENT '股票名称',
    `market`          VARCHAR(10)  DEFAULT '' COMMENT '市场',
    `add_price`       DECIMAL(10,3) DEFAULT 0 COMMENT '加入时价格',
    `note`            VARCHAR(200) DEFAULT '' COMMENT '备注',
    `sort_order`      INT          DEFAULT 0 COMMENT '排序权重(越大越靠前)',
    `is_deleted`      TINYINT(1)   DEFAULT 0 COMMENT '逻辑删除(0正常/1删除)',
    `created_at`      DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at`      DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_code` (`stock_code`),
    INDEX `idx_code` (`stock_code`),
    INDEX `idx_sort` (`sort_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='自选股表';

-- ==================== 持仓表 ====================
DROP TABLE IF EXISTS `portfolio`;
CREATE TABLE `portfolio` (
    `id`              INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    `stock_code`      VARCHAR(10)  NOT NULL COMMENT '股票代码',
    `stock_name`      VARCHAR(50)  NOT NULL COMMENT '股票名称',
    `market`          VARCHAR(10)  DEFAULT '' COMMENT '市场',
    `quantity`        INT          NOT NULL DEFAULT 0 COMMENT '持仓数量(股)',
    `avg_cost`        DECIMAL(10,4) NOT NULL DEFAULT 0 COMMENT '平均成本价',
    `total_cost`      DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '总成本(元)',
    `is_deleted`      TINYINT(1)   DEFAULT 0 COMMENT '逻辑删除',
    `created_at`      DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at`      DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_code` (`stock_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='持仓表';

-- ==================== 交易记录表 ====================
DROP TABLE IF EXISTS `transactions`;
CREATE TABLE `transactions` (
    `id`              BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    `stock_code`      VARCHAR(10)  NOT NULL COMMENT '股票代码',
    `stock_name`      VARCHAR(50)  NOT NULL COMMENT '股票名称',
    `trade_type`      VARCHAR(10)  NOT NULL COMMENT '交易类型(buy=买入/sell=卖出)',
    `quantity`        INT          NOT NULL COMMENT '交易数量(股)',
    `price`           DECIMAL(10,3) NOT NULL COMMENT '交易价格',
    `total_amount`    DECIMAL(18,2) NOT NULL COMMENT '交易总金额(元)',
    `fee`             DECIMAL(10,2) DEFAULT 0 COMMENT '手续费(元)',
    `created_at`      DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '交易时间',
    INDEX `idx_code` (`stock_code`),
    INDEX `idx_type` (`trade_type`),
    INDEX `idx_time` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='交易记录表';

-- ==================== 账户表 ====================
DROP TABLE IF EXISTS `account`;
CREATE TABLE `account` (
    `id`              INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    `balance`         DECIMAL(18,2) NOT NULL DEFAULT 1000000 COMMENT '可用资金(元)',
    `frozen`          DECIMAL(18,2) DEFAULT 0 COMMENT '冻结资金(元)',
    `initial_balance` DECIMAL(18,2) DEFAULT 1000000 COMMENT '初始资金(元)',
    `updated_at`      DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='账户表';

-- ==================== 用户配置表 ====================
DROP TABLE IF EXISTS `settings`;
CREATE TABLE `settings` (
    `id`              INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    `key`             VARCHAR(50)  NOT NULL UNIQUE COMMENT '配置键',
    `value`           TEXT         COMMENT '配置值',
    `updated_at`      DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户配置表';

-- ==================== 行情缓存表 ====================
DROP TABLE IF EXISTS `market_cache`;
CREATE TABLE `market_cache` (
    `id`              INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    `cache_key`       VARCHAR(100) NOT NULL UNIQUE COMMENT '缓存键',
    `cache_data`      LONGTEXT     COMMENT '缓存数据(JSON)',
    `expire_at`       DATETIME     COMMENT '过期时间',
    `created_at`      DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX `idx_key` (`cache_key`),
    INDEX `idx_expire` (`expire_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='行情缓存表';

-- ==================== 游资龙虎榜表 ====================
DROP TABLE IF EXISTS `dragon_tiger`;
CREATE TABLE `dragon_tiger` (
    `id`              BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    `stock_code`      VARCHAR(10)  NOT NULL COMMENT '股票代码',
    `stock_name`      VARCHAR(50)  NOT NULL COMMENT '股票名称',
    `trade_date`      DATE         NOT NULL COMMENT '上榜日期',
    `close_price`     DECIMAL(10,3) DEFAULT 0 COMMENT '收盘价',
    `change_pct`      DECIMAL(8,2) DEFAULT 0 COMMENT '涨跌幅(%)',
    `net_amount`      DECIMAL(18,2) DEFAULT 0 COMMENT '净买入额(元)',
    `buy_amount`      DECIMAL(18,2) DEFAULT 0 COMMENT '买入额(元)',
    `sell_amount`     DECIMAL(18,2) DEFAULT 0 COMMENT '卖出额(元)',
    `reason`          VARCHAR(200) DEFAULT '' COMMENT '上榜原因',
    `created_at`      DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX `idx_code` (`stock_code`),
    INDEX `idx_date` (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='游资龙虎榜表';

-- ================================================================
-- 初始化测试数据
-- ================================================================

-- 初始化账户
INSERT INTO `account` (`balance`, `frozen`, `initial_balance`) VALUES (1000000.00, 0, 1000000.00);

-- 初始化管理员账号: 运行 init_mysql.py 自动创建（含正确密码哈希）
-- 默认账号: admin / 密码: admin123

-- 初始化配置
INSERT INTO `settings` (`key`, `value`) VALUES
    ('theme', 'dopamine'),
    ('refresh_interval', '5'),
    ('chart_type', 'candlestick'),
    ('ma_periods', '5,10,20,60'),
    ('auto_refresh', 'true');

-- 初始化测试股票基础信息
INSERT INTO `stock_basic` (`code`, `name`, `market`, `industry`) VALUES
    ('600519', '贵州茅台', 'SH', '白酒'),
    ('000858', '五粮液', 'SZ', '白酒'),
    ('300750', '宁德时代', 'SZ', '电池'),
    ('601318', '中国平安', 'SH', '保险'),
    ('000333', '美的集团', 'SZ', '家电'),
    ('600036', '招商银行', 'SH', '银行'),
    ('002594', '比亚迪', 'SZ', '汽车'),
    ('600276', '恒瑞医药', 'SH', '医药'),
    ('000725', '京东方A', 'SZ', '面板'),
    ('601012', '隆基绿能', 'SH', '光伏');

-- 初始化测试自选股
INSERT INTO `watchlist` (`stock_code`, `stock_name`, `market`, `add_price`, `note`, `sort_order`) VALUES
    ('600519', '贵州茅台', 'SH', 1680.00, '白酒龙头', 100),
    ('300750', '宁德时代', 'SZ', 180.00, '新能源龙头', 90),
    ('002594', '比亚迪', 'SZ', 240.00, '新能源车', 80);

-- ================================================================
-- 建表完成
-- ================================================================
SELECT '投资分析应用 MySQL 数据库初始化完成！' AS message;
