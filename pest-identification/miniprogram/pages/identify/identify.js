// pages/identify/identify.js
const app = getApp();

Page({
  data: {
    imagePath: '',
    identifying: false,
    result: null,
    searchKeyword: '',
    searchResults: [],
  },

  takePhoto() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['camera'],
      sizeType: ['compressed'],
      success: (res) => {
        this.setData({
          imagePath: res.tempFiles[0].tempFilePath,
          result: null,
        });
      },
    });
  },

  chooseFromAlbum() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album'],
      sizeType: ['compressed'],
      success: (res) => {
        this.setData({
          imagePath: res.tempFiles[0].tempFilePath,
          result: null,
        });
      },
    });
  },

  retake() {
    this.setData({ imagePath: '', result: null, identifying: false });
  },

  async identify() {
    if (!this.data.imagePath || this.data.identifying) return;

    this.setData({ identifying: true });

    try {
      const res = await app.uploadImage(this.data.imagePath);

      if (res.result) {
        this.setData({
          result: {
            ...res.result,
            pestId: res.pestDetail?.id,
          },
          identifying: false,
        });
      } else {
        wx.showToast({ title: '识别失败，请重试', icon: 'none' });
        this.setData({ identifying: false });
      }
    } catch (err) {
      console.error('识别失败:', err);
      wx.showToast({ title: '网络错误，请重试', icon: 'none' });
      this.setData({ identifying: false });
    }
  },

  goDetail() {
    const id = this.data.result?.pestId;
    if (id) {
      wx.navigateTo({ url: `/pages/detail/detail?id=${id}` });
    }
  },

  onSearchInput(e) {
    this.setData({ searchKeyword: e.detail.value });
  },

  async doSearch() {
    const keyword = this.data.searchKeyword.trim();
    if (!keyword) {
      wx.showToast({ title: '请输入关键词', icon: 'none' });
      return;
    }

    try {
      const res = await app.request({
        url: `/pest/search/${encodeURIComponent(keyword)}`,
        method: 'GET',
      });
      this.setData({ searchResults: res.list || [] });
    } catch (err) {
      wx.showToast({ title: '搜索失败', icon: 'none' });
    }
  },

  goSearchDetail(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: `/pages/detail/detail?id=${id}` });
  },
});
