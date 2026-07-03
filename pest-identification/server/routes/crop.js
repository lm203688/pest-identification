const express = require('express');
const router = express.Router();
const db = require('../config/db');

// 获取作物列表
router.get('/', async (req, res) => {
  try {
    const [rows] = await db.query(
      'SELECT * FROM crops ORDER BY sort_order ASC'
    );

    // 为每个作物附加病虫害数量
    for (const crop of rows) {
      const [[{ count }]] = await db.query(
        'SELECT COUNT(*) as count FROM pest_crop_relation WHERE crop_id = ?',
        [crop.id]
      );
      crop.pest_count = count;
    }

    res.json({ list: rows });
  } catch (err) {
    console.error('获取作物列表失败:', err);
    res.status(500).json({ error: '获取作物列表失败' });
  }
});

// 获取某作物的病虫害列表
router.get('/:id/pests', async (req, res) => {
  try {
    const { id } = req.params;
    const { type } = req.query;

    let sql = `
      SELECT pk.id, pk.name, pk.type, pk.summary, pk.image_count
      FROM pest_knowledge pk
      JOIN pest_crop_relation pcr ON pk.id = pcr.pest_id
      WHERE pcr.crop_id = ? AND pk.status = 1
    `;
    const params = [id];

    if (type) {
      sql += ' AND pk.type = ?';
      params.push(type);
    }

    sql += ' ORDER BY pk.view_count DESC';

    const [rows] = await db.query(sql, params);
    res.json({ list: rows, total: rows.length });
  } catch (err) {
    console.error('获取作物病虫害失败:', err);
    res.status(500).json({ error: '获取作物病虫害失败' });
  }
});

module.exports = router;
