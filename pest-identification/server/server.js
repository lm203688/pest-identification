const express = require('express');
const cors = require('cors');
const path = require('path');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3002;

// 中间件
app.use(cors());
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// 路由
const pestRoutes = require('./routes/pest');
const identifyRoutes = require('./routes/identify');
const cropRoutes = require('./routes/crop');

app.use('/api/pest', pestRoutes);
app.use('/api/identify', identifyRoutes);
app.use('/api/crop', cropRoutes);

// 健康检查
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', service: 'pest-identification', version: '1.0.0' });
});

// 错误处理
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ error: '服务器内部错误' });
});

app.listen(PORT, () => {
  console.log(`🐛 病虫害识别服务启动 http://localhost:${PORT}`);
});

module.exports = app;
