// app.js
App({
  globalData: {
    apiBase: 'https://150.158.119.19/pest-api', // 后端API地址
    userInfo: null,
  },

  onLaunch() {
    // 检查登录态
    const token = wx.getStorageSync('token');
    if (token) {
      this.globalData.token = token;
    }
  },

  // 封装请求
  request(options) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: this.globalData.apiBase + options.url,
        method: options.method || 'GET',
        data: options.data || {},
        header: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.globalData.token || ''}`,
          ...options.header,
        },
        success: (res) => {
          if (res.statusCode === 200) {
            resolve(res.data);
          } else {
            reject(res);
          }
        },
        fail: reject,
      });
    });
  },

  // 上传图片
  uploadImage(filePath) {
    return new Promise((resolve, reject) => {
      wx.uploadFile({
        url: this.globalData.apiBase + '/identify',
        filePath,
        name: 'image',
        header: {
          'Authorization': `Bearer ${this.globalData.token || ''}`,
        },
        success: (res) => {
          const data = JSON.parse(res.data);
          resolve(data);
        },
        fail: reject,
      });
    });
  },
});
