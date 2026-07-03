// pages/detail/detail.js
const app = getApp();

Page({
  data: {
    pest: null,
    crops: [],
  },

  onLoad(options) {
    if (options.id) {
      this.loadDetail(options.id);
    }
  },

  async loadDetail(id) {
    wx.showLoading({ title: '加载中...' });
    try {
      const res = await app.request({ url: `/pest/${id}` });
      this.setData({ pest: res, crops: res.crops || [] });
    } catch (err) {
      console.error('加载详情失败:', err);
      wx.showToast({ title: '加载失败', icon: 'none' });
    }
    wx.hideLoading();
  },

  goIdentify() {
    wx.navigateTo({ url: '/pages/identify/identify' });
  },

  onShareAppMessage() {
    return {
      title: `${this.data.pest?.name || '病虫害'}识别与防治`,
      path: `/pages/detail/detail?id=${this.data.pest?.id}`,
    };
  },
});
