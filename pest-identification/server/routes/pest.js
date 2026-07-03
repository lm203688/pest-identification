const express = require('express');
const router = express.Router();
const db = require('../config/db');

// 获取病虫害列表（支持按作物筛选、搜索）
router.get('/', async (req, res) => {
  try {
    const { crop_id, type, keyword, page = 1, pageSize = 20 } = req.query;
    const offset = (page - 1) * pageSize;

    let sql = `
      SELECT pk.*, GROUP_CONCAT(c.name) as crop_names
      FROM pest_knowledge pk
      LEFT JOIN pest_crop_relation pcr ON pk.id = pcr.pest_id
      LEFT JOIN crops c ON pcr.crop_id = c.id
      WHERE pk.status = 1
    `;
    const params = [];

    if (crop_id) {
      sql += ` AND pcr.crop_id = ?`;
      params.push(crop_id);
    }
    if (type) {
      sql += ` AND pk.type = ?`;
      params.push(type);
    }
    if (keyword) {
      sql += ` AND (pk.name LIKE ? OR pk.aliases LIKE ? OR pk.summary LIKE ?)`;
      params.push(`%${keyword}%`, `%${keyword}%`, `%${keyword}%`);
    }

    sql += ` GROUP BY pk.id ORDER BY pk.view_count DESC LIMIT ? OFFSET ?`;
    params.push(parseInt(pageSize), parseInt(offset));

    const [rows] = await db.query(sql, params);

    // 获取总数
    let countSql = `SELECT COUNT(DISTINCT pk.id) as total FROM pest_knowledge pk LEFT JOIN pest_crop_relation pcr ON pk.id = pcr.pest_id WHERE pk.status = 1`;
    const countParams = [];
    if (crop_id) { countSql += ` AND pcr.crop_id = ?`; countParams.push(crop_id); }
    if (type) { countSql += ` AND pk.type = ?`; countParams.push(type); }
    if (keyword) { countSql += ` AND (pk.name LIKE ? OR pk.aliases LIKE ? OR pk.summary LIKE ?)`; countParams.push(`%${keyword}%`, `%${keyword}%`, `%${keyword}%`); }
    const [[{ total }]] = await db.query(countSql, countParams);

    res.json({
      list: rows,
      total,
      page: parseInt(page),
      pageSize: parseInt(pageSize),
    });
  } catch (err) {
    console.error('获取病虫害列表失败:', err);
    res.status(500).json({ error: '获取列表失败' });
  }
});

// 获取病虫害详情
router.get('/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const [[pest]] = await db.query('SELECT * FROM pest_knowledge WHERE id = ? AND status = 1', [id]);

    if (!pest) {
      return res.status(404).json({ error: '未找到该病虫害' });
    }

    // 获取关联作物
    const [crops] = await db.query(`
      SELECT c.* FROM crops c
      JOIN pest_crop_relation pcr ON c.id = pcr.crop_id
      WHERE pcr.pest_id = ?
    `, [id]);

    // 获取关联图片
    const [images] = await db.query(
      'SELECT * FROM pest_images WHERE pest_id = ? ORDER BY id DESC',
      [id]
    );

    // 更新浏览次数
    await db.query('UPDATE pest_knowledge SET view_count = view_count + 1 WHERE id = ?', [id]);

    res.json({ ...pest, crops, images });
  } catch (err) {
    console.error('获取病虫害详情失败:', err);
    res.status(500).json({ error: '获取详情失败' });
  }
});

// 搜索病虫害（全文搜索）
router.get('/search/:keyword', async (req, res) => {
  try {
    const { keyword } = req.params;
    const [rows] = await db.query(`
      SELECT id, name, aliases, type, summary
      FROM pest_knowledge
      WHERE status = 1 AND (
        name LIKE ? OR aliases LIKE ? OR summary LIKE ? OR symptoms LIKE ?
      )
      LIMIT 20
    `, [`%${keyword}%`, `%${keyword}%`, `%${keyword}%`, `%${keyword}%`]);

    res.json({ list: rows, total: rows.length });
  } catch (err) {
    console.error('搜索失败:', err);
    res.status(500).json({ error: '搜索失败' });
  }
});

module.exports = router;
