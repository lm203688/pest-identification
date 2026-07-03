const express = require('express');
const router = express.Router();
const multer = require('multer');
const axios = require('axios');
const FormData = require('form-data');
const db = require('../config/db');

// 图片上传配置
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 10 * 1024 * 1024 }, // 10MB
  fileFilter: (req, file, cb) => {
    if (file.mimetype.startsWith('image/')) {
      cb(null, true);
    } else {
      cb(new Error('只支持图片文件'));
    }
  },
});

// 拍照识别病虫害
router.post('/', upload.single('image'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: '请上传图片' });
    }

    const { user_id } = req.body;
    const imageBuffer = req.file.buffer;

    // 1. 先尝试自建模型识别（TODO: 后续接入）
    // 2. 调用Kindwise API识别
    let result = null;

    if (process.env.KINDWISE_API_KEY && process.env.KINDWISE_API_KEY !== 'your_api_key_here') {
      result = await identifyWithKindwise(imageBuffer);
    }

    // 3. 如果API不可用，用AI辅助识别
    if (!result) {
      result = await identifyWithAI(imageBuffer);
    }

    // 4. 从知识库匹配详细信息
    let pestDetail = null;
    if (result && result.name) {
      const [[match]] = await db.query(
        'SELECT * FROM pest_knowledge WHERE name LIKE ? OR aliases LIKE ? LIMIT 1',
        [`%${result.name}%`, `%${result.name}%`]
      );
      if (match) {
        pestDetail = match;
      }
    }

    // 5. 记录识别历史
    if (user_id) {
      await db.query(
        'INSERT INTO identification_records (user_id, image_url, result_pest_id, result_name, confidence) VALUES (?, ?, ?, ?, ?)',
        [user_id, '', pestDetail?.id || null, result?.name || '未知', result?.confidence || 0]
      );
    }

    res.json({
      success: true,
      identification: {
        name: result?.name || '未能识别',
        confidence: result?.confidence || 0,
        type: result?.type || pestDetail?.type || '未知',
      },
      detail: pestDetail ? {
        id: pestDetail.id,
        summary: pestDetail.summary,
        symptoms: pestDetail.symptoms,
        conditions: pestDetail.conditions,
        prevention: pestDetail.prevention,
        medicine: pestDetail.medicine,
      } : null,
    });
  } catch (err) {
    console.error('识别失败:', err);
    res.status(500).json({ error: '识别失败，请重试' });
  }
});

// Kindwise API识别
async function identifyWithKindwise(imageBuffer) {
  try {
    const form = new FormData();
    form.append('image', imageBuffer, {
      filename: 'image.jpg',
      contentType: 'image/jpeg',
    });

    const response = await axios.post(
      'https://crop.kindwise.com/api/v1/identification',
      form,
      {
        headers: {
          ...form.getHeaders(),
          'Api-Key': process.env.KINDWISE_API_KEY,
        },
        timeout: 30000,
      }
    );

    const suggestion = response.data?.suggestions?.[0];
    if (suggestion) {
      return {
        name: suggestion.name,
        confidence: Math.round(suggestion.probability * 100),
        type: suggestion.subject?.type || '未知',
      };
    }
    return null;
  } catch (err) {
    console.error('Kindwise API调用失败:', err.message);
    return null;
  }
}

// AI辅助识别（多策略：百度AI → 知识库匹配）
async function identifyWithAI(imageBuffer) {
  // 策略1: 百度AI植物病害识别（需配置API Key）
  if (process.env.BAIDU_API_KEY && process.env.BAIDU_SECRET_KEY) {
    const baiduResult = await identifyWithBaidu(imageBuffer);
    if (baiduResult) return baiduResult;
  }

  // 策略2: 返回提示用户手动描述症状
  return {
    name: '待识别',
    confidence: 0,
    type: '未知',
    suggestion: 'AI识别服务暂未配置，请尝试从百科中搜索',
  };
}

// 百度AI植物病害识别
async function identifyWithBaidu(imageBuffer) {
  try {
    // 1. 获取access_token
    const tokenRes = await axios.post(
      `https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id=${process.env.BAIDU_API_KEY}&client_secret=${process.env.BAIDU_SECRET_KEY}`,
      {},
      { timeout: 10000 }
    );
    const accessToken = tokenRes.data.access_token;
    if (!accessToken) return null;

    // 2. 调用植物病害识别API
    const base64Img = imageBuffer.toString('base64');
    const detectRes = await axios.post(
      `https://aip.baidubce.com/rpc/2.0/ai_custom/v1/detection/plant_disease?access_token=${accessToken}`,
      { image: base64Img },
      {
        headers: { 'Content-Type': 'application/json' },
        timeout: 30000,
      }
    );

    const results = detectRes.data?.results;
    if (results && results.length > 0) {
      const top = results[0];
      return {
        name: top.name || '未知病害',
        confidence: Math.round((top.score || 0) * 100),
        type: '病害',
        baiduRaw: results.slice(0, 3),
      };
    }
    return null;
  } catch (err) {
    console.error('百度AI识别失败:', err.message);
    return null;
  }
}

// 获取识别历史
router.get('/history', async (req, res) => {
  try {
    const { user_id, page = 1, pageSize = 20 } = req.query;
    if (!user_id) {
      return res.status(400).json({ error: '缺少user_id' });
    }

    const offset = (page - 1) * pageSize;
    const [rows] = await db.query(
      'SELECT * FROM identification_records WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?',
      [user_id, parseInt(pageSize), parseInt(offset)]
    );

    const [[{ total }]] = await db.query(
      'SELECT COUNT(*) as total FROM identification_records WHERE user_id = ?',
      [user_id]
    );

    res.json({ list: rows, total, page: parseInt(page), pageSize: parseInt(pageSize) });
  } catch (err) {
    console.error('获取历史失败:', err);
    res.status(500).json({ error: '获取历史失败' });
  }
});

// 用户反馈识别结果
router.post('/feedback', async (req, res) => {
  try {
    const { record_id, is_correct, correct_pest_id } = req.body;

    await db.query(
      'UPDATE identification_records SET is_correct = ?, correct_pest_id = ? WHERE id = ?',
      [is_correct ? 1 : 0, correct_pest_id || null, record_id]
    );

    res.json({ success: true });
  } catch (err) {
    console.error('反馈失败:', err);
    res.status(500).json({ error: '反馈失败' });
  }
});

module.exports = router;
