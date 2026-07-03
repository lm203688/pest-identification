// pages/index/index.js
const app = getApp();

Page({
  data: {
    crops: [
      { id: 1, name: '水稻', icon: '🌾', pest_count: 12, bgColor: 'rgba(82,183,136,0.15)' },
      { id: 2, name: '小麦', icon: '🌿', pest_count: 9, bgColor: 'rgba(244,162,97,0.15)' },
      { id: 3, name: '玉米', icon: '🌽', pest_count: 9, bgColor: 'rgba(231,111,81,0.15)' },
      { id: 4, name: '番茄', icon: '🍅', pest_count: 8, bgColor: 'rgba(231,111,81,0.15)' },
      { id: 5, name: '黄瓜', icon: '🥒', pest_count: 6, bgColor: 'rgba(82,183,136,0.15)' },
      { id: 6, name: '柑橘', icon: '🍊', pest_count: 7, bgColor: 'rgba(244,162,97,0.15)' },
      { id: 7, name: '苹果', icon: '🍎', pest_count: 7, bgColor: 'rgba(231,111,81,0.15)' },
      { id: 8, name: '葡萄', icon: '🍇', pest_count: 7, bgColor: 'rgba(128,100,200,0.15)' },
      { id: 9, name: '棉花', icon: '☁️', pest_count: 5, bgColor: 'rgba(200,200,200,0.15)' },
      { id: 10, name: '大豆', icon: '🫘', pest_count: 6, bgColor: 'rgba(244,162,97,0.15)' },
      { id: 11, name: '白菜', icon: '🥬', pest_count: 5, bgColor: 'rgba(82,183,136,0.15)' },
      { id: 12, name: '辣椒', icon: '🌶️', pest_count: 6, bgColor: 'rgba(231,111,81,0.15)' },
    ],
    hotPests: [],
  },

  onLoad() {
    this.loadHotPests();
  },

  onPullDownRefresh() {
    this.loadHotPests();
    wx.stopPullDownRefresh();
  },

  async loadHotPests() {
    try {
      const res = await app.request({
        url: '/pest?pageSize=10',
      });
      this.setData({ hotPests: res.list || [] });
    } catch (err) {
      console.error('加载热门病虫害失败:', err);
    }
  },

  goIdentify() {
    wx.navigateTo({ url: '/pages/identify/identify' });
  },

  goSearch() {
    wx.navigateTo({ url: '/pages/encyclopedia/encyclopedia?focus=true' });
  },

  goCropPests(e) {
    const { id, name } = e.currentTarget.dataset;
    wx.navigateTo({
      url: `/pages/encyclopedia/encyclopedia?crop_id=${id}&crop_name=${name}`,
    });
  },

  goDetail(e) {
    const { id } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/detail/detail?id=${id}` });
  },

  goEncyclopedia() {
    wx.switchTab({ url: '/pages/encyclopedia/encyclopedia' });
  },
});
