// pages/encyclopedia/encyclopedia.js
const app = getApp();

Page({
  data: {
    keyword: '',
    crops: [],
    activeCrop: 0,
    activeType: '',
    pestList: [],
    page: 1,
    hasMore: true,
    loading: false,
    focus: false,
  },

  onLoad(options) {
    if (options.crop_id) {
      this.setData({ activeCrop: parseInt(options.crop_id) });
    }
    if (options.focus) {
      this.setData({ focus: true });
    }
    this.loadCrops();
    this.loadPests();
  },

  async loadCrops() {
    try {
      const res = await app.request({ url: '/crop' });
      this.setData({ crops: res.list || [] });
    } catch (err) {
      console.error('加载作物失败:', err);
    }
  },

  async loadPests(append = false) {
    if (this.data.loading) return;
    this.setData({ loading: true });

    try {
      const params = {
        page: this.data.page,
        pageSize: 20,
      };
      if (this.data.activeCrop) params.crop_id = this.data.activeCrop;
      if (this.data.activeType) params.type = this.data.activeType;
      if (this.data.keyword) params.keyword = this.data.keyword;

      const res = await app.request({ url: '/pest', data: params });
      const list = res.list || [];

      this.setData({
        pestList: append ? [...this.data.pestList, ...list] : list,
        hasMore: list.length >= 20,
        loading: false,
      });
    } catch (err) {
      console.error('加载病虫害失败:', err);
      this.setData({ loading: false });
    }
  },

  onSearchInput(e) {
    this.setData({ keyword: e.detail.value });
  },

  doSearch() {
    this.setData({ page: 1 });
    this.loadPests();
  },

  filterCrop(e) {
    const id = parseInt(e.currentTarget.dataset.id);
    this.setData({ activeCrop: id, page: 1 });
    this.loadPests();
  },

  filterType(e) {
    const type = e.currentTarget.dataset.type;
    this.setData({ activeType: type, page: 1 });
    this.loadPests();
  },

  loadMore() {
    this.setData({ page: this.data.page + 1 });
    this.loadPests(true);
  },

  goDetail(e) {
    const { id } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/detail/detail?id=${id}` });
  },
});
