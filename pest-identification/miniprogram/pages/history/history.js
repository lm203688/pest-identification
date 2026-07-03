// pages/history/history.js
const app = getApp();

Page({
  data: {
    records: [],
    loading: false,
  },

  onShow() {
    this.loadRecords();
  },

  async loadRecords() {
    this.setData({ loading: true });
    try {
      const res = await app.request({
        url: '/identify/history',
        data: { user_id: app.globalData.userInfo?.id || 'anonymous' },
      });
      this.setData({ records: res.list || [], loading: false });
    } catch (err) {
      console.error('加载记录失败:', err);
      this.setData({ loading: false });
    }
  },

  goDetail(e) {
    const { id } = e.currentTarget.dataset;
    if (id) {
      wx.navigateTo({ url: `/pages/detail/detail?id=${id}` });
    }
  },
});
