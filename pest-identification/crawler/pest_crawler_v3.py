#!/usr/bin/env python3
"""
病虫害知识库爬虫 v3 - 快速版
只爬搜狗百科，不做搜索聚合，速度优先
"""

import json
import re
import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "data" / "knowledge"
DATA_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def fetch(url, timeout=10):
    try:
        r = SESSION.get(url, timeout=timeout, allow_redirects=True)
        r.encoding = r.apparent_encoding or "utf-8"
        return r.text if r.status_code == 200 else None
    except:
        return None


def extract_sogou_baike(keyword):
    """直接尝试搜狗百科词条"""
    # 搜狗百科URL格式: https://baike.sogou.com/v{数字}.htm
    # 先搜索获取词条URL
    search_url = f"https://baike.sogou.com/search?query={quote(keyword)}"
    html = fetch(search_url)
    if not html:
        return None

    soup = BeautifulSoup(html, "lxml")

    # 从搜索结果找词条链接
    baike_url = None
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/v" in href and ".htm" in href:
            if href.startswith("/"):
                baike_url = f"https://baike.sogou.com{href}"
            elif href.startswith("http"):
                baike_url = href
            break

    if not baike_url:
        return None

    # 获取词条内容
    html = fetch(baike_url)
    if not html:
        return None

    soup = BeautifulSoup(html, "lxml")

    record = {
        "name": keyword,
        "aliases": [],
        "host_crops": [],
        "type": "其他",
        "summary": "",
        "symptoms": "",
        "conditions": "",
        "prevention": "",
        "medicine": "",
        "source": "搜狗百科",
        "source_url": baike_url,
        "crawl_time": datetime.now().isoformat(),
    }

    # 提取所有文本段落
    paragraphs = []
    for p in soup.find_all(["p", "div"]):
        text = p.get_text(strip=True)
        if 15 < len(text) < 2000:
            paragraphs.append(text)

    full_text = "\n".join(paragraphs)
    record["raw_text"] = full_text[:3000]

    # 摘要（第一段较长的文字）
    for p in paragraphs[:3]:
        if len(p) > 30:
            record["summary"] = p[:200]
            break

    # 结构化提取
    _extract_info(record, full_text)

    return record


def _extract_info(record, text):
    """从文本中提取结构化信息"""
    name = record["name"]

    # 类型判断
    pest_kw = ["虫", "蛾", "蝶", "蝇", "蚜", "螨", "蝗", "螟", "虱", "蚁", "蚧",
               "蝉", "蝽", "金龟", "天牛", "食心虫", "夜蛾", "蛆", "蛴螬", "蝼蛄"]
    disease_kw = ["病", "霉", "腐", "枯", "萎", "锈", "斑", "疫", "瘿", "粉"]

    if any(kw in name for kw in pest_kw):
        record["type"] = "虫害"
    elif any(kw in name for kw in disease_kw):
        record["type"] = "病害"

    # 作物提取
    crops = ["水稻", "小麦", "玉米", "大豆", "花生", "棉花", "番茄", "黄瓜",
             "白菜", "辣椒", "茄子", "柑橘", "苹果", "梨", "葡萄", "桃",
             "荔枝", "芒果", "猕猴桃", "西瓜", "草莓", "茶", "甘蔗",
             "马铃薯", "甘薯", "油菜", "芝麻", "高粱", "谷子"]
    for c in crops:
        if c in text or c in name:
            record["host_crops"].append(c)
    record["host_crops"] = list(set(record["host_crops"]))

    # 按标题/关键词分段提取
    sections = re.split(r'(?=(?:症状|为害|发病|发生规律|防治|药剂|化学防治|农业防治))', text)

    for sec in sections:
        if re.match(r'症状|为害症状|发病症状|危害症状|为害特点', sec):
            content = re.sub(r'^症状[^：:]*[：:]?', '', sec).strip()[:500]
            if len(content) > 20:
                record["symptoms"] = content
        elif re.match(r'发病条件|发生规律|发生条件|流行规律|传播途径', sec):
            content = re.sub(r'^发病条件[^：:]*[：:]?', '', sec).strip()[:500]
            if len(content) > 20:
                record["conditions"] = content
        elif re.match(r'防治方法|防治措施|综合防治|防治技术', sec):
            content = re.sub(r'^防治方法[^：:]*[：:]?', '', sec).strip()[:800]
            if len(content) > 20:
                record["prevention"] = content
        elif re.match(r'药剂防治|化学防治|推荐用药', sec):
            content = re.sub(r'^药剂防治[^：:]*[：:]?', '', sec).strip()[:500]
            if len(content) > 10:
                record["medicine"] = content

    # 如果没有分段提取到，用全文匹配
    if not record["symptoms"]:
        m = re.search(r'(?:症状|为害)[^：:]*[：:](.{20,500}?)(?=(?:发病|防治|传播|发生规律)|$)', text, re.DOTALL)
        if m:
            record["symptoms"] = m.group(1).strip()

    if not record["prevention"]:
        m = re.search(r'(?:防治方法|防治措施|防治)[^：:]*[：:](.{20,800}?)(?=(?:备注|参考|相关)|$)', text, re.DOTALL)
        if m:
            record["prevention"] = m.group(1).strip()

    # 提取农药名称
    if not record["medicine"] and record["prevention"]:
        meds = re.findall(r'[\u4e00-\u9fff]{2,8}(?:灵|清|锌|酮|素|酯|磷|胺|脒|菊酯|霉素)', record["prevention"])
        if meds:
            record["medicine"] = "、".join(list(set(meds))[:8])


# 病虫害关键词
PEST_KEYWORDS = {
    "水稻": ["稻瘟病", "水稻纹枯病", "水稻白叶枯病", "稻飞虱", "二化螟",
             "三化螟", "稻纵卷叶螟", "水稻条纹叶枯病", "水稻恶苗病", "稻蝗"],
    "小麦": ["小麦锈病", "小麦赤霉病", "小麦白粉病", "小麦蚜虫",
             "小麦吸浆虫", "小麦纹枯病", "小麦全蚀病", "麦蜘蛛"],
    "玉米": ["玉米大斑病", "玉米小斑病", "玉米螟", "玉米锈病",
             "玉米丝黑穗病", "草地贪夜蛾", "玉米粗缩病"],
    "蔬菜": ["番茄晚疫病", "番茄早疫病", "番茄灰霉病", "黄瓜霜霉病",
             "黄瓜白粉病", "白菜软腐病", "菜青虫", "小菜蛾",
             "蚜虫", "红蜘蛛", "白粉虱", "斜纹夜蛾"],
    "果树": ["柑橘黄龙病", "柑橘溃疡病", "柑橘红蜘蛛", "苹果腐烂病",
             "苹果褐斑病", "梨黑星病", "梨小食心虫", "葡萄霜霉病",
             "葡萄白腐病", "桃褐腐病", "荔枝蒂蛀虫", "芒果炭疽病"],
    "棉花": ["棉花枯萎病", "棉花黄萎病", "棉铃虫", "棉蚜", "棉花红蜘蛛"],
    "大豆": ["大豆花叶病毒病", "大豆根腐病", "大豆蚜虫", "大豆食心虫"],
    "花生": ["花生叶斑病", "花生根腐病", "花生青枯病", "蛴螬"],
}


def main():
    all_records = []
    total = sum(len(v) for v in PEST_KEYWORDS.values())
    count = 0

    for crop, pests in PEST_KEYWORDS.items():
        print(f"\n{'='*40}")
        print(f"[{crop}] 共 {len(pests)} 种")
        print(f"{'='*40}")

        for pest in pests:
            count += 1
            print(f"  [{count}/{total}] {pest}...", end=" ", flush=True)

            record = extract_sogou_baike(pest)

            if record:
                if crop not in record["host_crops"]:
                    record["host_crops"].append(crop)
                all_records.append(record)
                s = "✓" if record["symptoms"] else "✗"
                p = "✓" if record["prevention"] else "✗"
                m = "✓" if record["medicine"] else "✗"
                print(f"OK 症状:{s} 防治:{p} 用药:{m}")
            else:
                print("FAIL")

            time.sleep(random.uniform(0.5, 1.5))

    # 保存
    output = DATA_DIR / "pest_knowledge_raw.json"
    with open(output, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*40}")
    print(f"完成！共 {len(all_records)} 条")
    print(f"  症状: {sum(1 for r in all_records if r.get('symptoms'))}")
    print(f"  防治: {sum(1 for r in all_records if r.get('prevention'))}")
    print(f"  用药: {sum(1 for r in all_records if r.get('medicine'))}")
    print(f"保存: {output}")

    return all_records


if __name__ == "__main__":
    main()
