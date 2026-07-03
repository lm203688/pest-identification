-- 病虫害知识库 MySQL 建表脚本

-- 作物表
CREATE TABLE IF NOT EXISTS crops (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE COMMENT '作物名称',
    category VARCHAR(20) COMMENT '分类：粮食/蔬菜/果树/经济作物',
    icon VARCHAR(255) COMMENT '图标URL',
    sort_order INT DEFAULT 0 COMMENT '排序',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='作物表';

-- 病虫害知识表
CREATE TABLE IF NOT EXISTS pest_knowledge (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '病虫害名称',
    aliases VARCHAR(500) COMMENT '别名，逗号分隔',
    type ENUM('病害', '虫害', '其他') NOT NULL DEFAULT '病害' COMMENT '类型',
    summary TEXT COMMENT '简介',
    symptoms TEXT COMMENT '症状描述',
    conditions TEXT COMMENT '发病条件/发生规律',
    prevention TEXT COMMENT '防治方案',
    medicine TEXT COMMENT '推荐用药',
    image_count INT DEFAULT 0 COMMENT '关联图片数量',
    view_count INT DEFAULT 0 COMMENT '浏览次数',
    source VARCHAR(100) COMMENT '数据来源',
    source_url VARCHAR(500) COMMENT '来源URL',
    status TINYINT DEFAULT 1 COMMENT '1启用 0禁用',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name),
    INDEX idx_type (type),
    FULLTEXT INDEX ft_search (name, aliases, summary, symptoms)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='病虫害知识表';

-- 病虫害-作物关联表
CREATE TABLE IF NOT EXISTS pest_crop_relation (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pest_id INT NOT NULL COMMENT '病虫害ID',
    crop_id INT NOT NULL COMMENT '作物ID',
    UNIQUE KEY uk_pest_crop (pest_id, crop_id),
    FOREIGN KEY (pest_id) REFERENCES pest_knowledge(id) ON DELETE CASCADE,
    FOREIGN KEY (crop_id) REFERENCES crops(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='病虫害-作物关联';

-- 病虫害图片表
CREATE TABLE IF NOT EXISTS pest_images (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pest_id INT NOT NULL COMMENT '病虫害ID',
    image_url VARCHAR(500) NOT NULL COMMENT '图片URL（COS）',
    local_path VARCHAR(500) COMMENT '本地路径',
    source VARCHAR(100) COMMENT '图片来源',
    is_verified TINYINT DEFAULT 0 COMMENT '是否已人工验证',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pest_id) REFERENCES pest_knowledge(id) ON DELETE CASCADE,
    INDEX idx_pest (pest_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='病虫害图片表';

-- 用户识别记录表
CREATE TABLE IF NOT EXISTS identification_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(100) COMMENT '用户ID（微信openid）',
    image_url VARCHAR(500) COMMENT '用户上传图片URL',
    result_pest_id INT COMMENT '识别结果-病虫害ID',
    result_name VARCHAR(100) COMMENT '识别结果-名称',
    confidence DECIMAL(5,2) COMMENT '置信度 0-100',
    is_correct TINYINT COMMENT '用户反馈是否正确',
    correct_pest_id INT COMMENT '用户纠正后的病虫害ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_pest (result_pest_id),
    INDEX idx_time (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='识别记录表';

-- 用户众包提交表
CREATE TABLE IF NOT EXISTS user_submissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL COMMENT '提交用户ID',
    pest_name VARCHAR(100) NOT NULL COMMENT '病虫害名称',
    crop_name VARCHAR(50) COMMENT '作物名称',
    image_urls TEXT COMMENT '图片URL列表，JSON数组',
    description TEXT COMMENT '用户描述',
    location VARCHAR(100) COMMENT '发现地点',
    status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending' COMMENT '审核状态',
    reviewed_by VARCHAR(100) COMMENT '审核人',
    reviewed_at TIMESTAMP NULL COMMENT '审核时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户众包提交';

-- 初始作物数据
INSERT IGNORE INTO crops (name, category, sort_order) VALUES
('水稻', '粮食', 1),
('小麦', '粮食', 2),
('玉米', '粮食', 3),
('大豆', '粮食', 4),
('花生', '粮食', 5),
('棉花', '经济作物', 6),
('番茄', '蔬菜', 7),
('黄瓜', '蔬菜', 8),
('白菜', '蔬菜', 9),
('辣椒', '蔬菜', 10),
('茄子', '蔬菜', 11),
('柑橘', '果树', 12),
('苹果', '果树', 13),
('梨', '果树', 14),
('葡萄', '果树', 15),
('桃', '果树', 16),
('荔枝', '果树', 17),
('芒果', '果树', 18);
