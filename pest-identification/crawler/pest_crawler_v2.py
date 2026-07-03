#!/usr/bin/env python3
"""
病虫害知识库爬虫 v2 - 多源爬取
数据源：搜狗百科 + 农业网站 + 搜索引擎聚合
"""

import json
import os
import re
import time
import random
import hashlib
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, urljoin, urlparse
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "data" / "knowledge"
DATA_DIR.mkdir(parents=True, exist_ok=True)

HEADERS_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
]

SESSION = requests.Session()


def get_headers():
    return {
        "User-Agent": random.choice(HEADERS_LIST),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://www.sogou.com/",
    }


def fetch_page(url, retries=3):
    """通用页面获取"""
    for i in range(retries):
        try:
            r = SESSION.get(url, headers=get_headers(), timeout=15, allow_redirects=True)
            r.encoding = r.apparent_encoding or "utf-8"
            if r.status_code == 200:
                return r.text
            elif r.status_code == 403:
                time.sleep(random.uniform(2, 5))
                continue
        except Exception as e:
            if i < retries - 1:
                time.sleep(random.uniform(1, 3))
    return None


# ============================================================
# 搜狗百科爬虫
# ============================================================

def sogou_baike_search(keyword):
    """搜狗百科搜索，返回词条URL"""
    url = f"https://baike.sogou.com/search?query={quote(keyword)}"
    html = fetch_page(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "lxml")
    # 搜索结果中的词条链接
    for a in soup.select("a[href*='/v']"):
        href = a.get("href", "")
        if href.startswith("/v") and ".htm" in href:
            return f"https://baike.sogou.com{href}"
    return None


def parse_sogou_baike(url, keyword):
    """解析搜狗百科词条页面"""
    html = fetch_page(url)
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
        "source_url": url,
        "crawl_time": datetime.now().isoformat(),
    }

    # 提取摘要
    summary_el = soup.select_one(".abstract, .lemma-summary, .summary-content")
    if summary_el:
        record["summary"] = summary_el.get_text(strip=True)

    # 提取正文段落
    content_el = soup.select_one(".lemma-content, .main-content, #contentBody")
    if not content_el:
        content_el = soup

    # 提取所有段落文本
    all_text = []
    for p in content_el.select("p, div.para"):
        text = p.get_text(strip=True)
        if len(text) > 10:
            all_text.append(text)

    full_text = "\n".join(all_text)
    record["raw_text"] = full_text

    # 按关键词提取结构化信息
    _extract_structured_info(record, full_text)

    return record


# ============================================================
# 搜索引擎聚合爬虫（通过搜狗搜索获取多个来源）
# ============================================================

def sogou_search_pest(keyword):
    """通过搜狗搜索获取病虫害信息，聚合多个来源"""
    query = f"{keyword} 症状 防治方法"
    url = f"https://www.sogou.com/web?query={quote(query)}"
    html = fetch_page(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "lxml")
    results = []

    # 提取搜索结果
    for item in soup.select(".vrwrap, .rb, .results .vrResult"):
        title_el = item.select_one("h3 a, .vr-title a")
        snippet_el = item.select_one(".space-txt, .str_info, .str-text-info")

        if title_el:
            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""

            # 过滤相关结果
            if any(kw in title for kw in ["病", "虫", "害", "防治", "症状", "农药", "植保"]):
                results.append({
                    "title": title,
                    "url": href,
                    "snippet": snippet,
                })

    return results[:5]  # 取前5个相关结果


def fetch_and_parse_result(url, keyword):
    """爬取搜索结果页面并提取病虫害信息"""
    html = fetch_page(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "lxml")

    # 提取所有段落文本
    all_text = []
    for p in soup.select("p, div.content, article p, .article-content p"):
        text = p.get_text(strip=True)
        if len(text) > 15:
            all_text.append(text)

    if not all_text:
        return None

    full_text = "\n".join(all_text)

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
        "source": urlparse(url).netloc,
        "source_url": url,
        "crawl_time": datetime.now().isoformat(),
        "raw_text": full_text[:3000],  # 限制长度
    }

    _extract_structured_info(record, full_text)
    return record


# ============================================================
# 通用信息提取
# ============================================================

def _extract_structured_info(record, full_text):
    """从全文中提取结构化信息"""
    # 判断病害/虫害类型
    name = record["name"]
    pest_kw = ["虫", "蛾", "蝶", "蝇", "蚜", "螨", "蝗", "螟", "虱", "蚁", "蚧",
               "蝉", "蝽", "蚊", "金龟", "天牛", "象甲", "食心虫", "夜蛾", "蛆",
               "蛴螬", "蝼蛄", "地老虎", "蚯蚓", "蜗牛", "蛞蝓"]
    disease_kw = ["病", "霉", "腐", "枯", "萎", "锈", "斑", "疫", "瘿", "烂", "焦", "粉", "毒"]

    if any(kw in name for kw in pest_kw):
        record["type"] = "虫害"
    elif any(kw in name for kw in disease_kw):
        record["type"] = "病害"

    # 提取危害作物
    crop_names = ["水稻", "小麦", "玉米", "大豆", "花生", "棉花", "番茄", "黄瓜",
                  "白菜", "辣椒", "茄子", "柑橘", "苹果", "梨", "葡萄", "桃",
                  "荔枝", "芒果", "猕猴桃", "西瓜", "甜瓜", "草莓", "茶",
                  "甘蔗", "烟草", "马铃薯", "甘薯", "高粱", "谷子", "大麦",
                  "油菜", "芝麻", "向日葵", "亚麻", "大麻", "橡胶", "咖啡",
                  "香蕉", "菠萝", "椰子", "木瓜", "石榴", "枣", "柿子",
                  "樱桃", "蓝莓", "杨梅", "枇杷", "龙眼", "火龙果"]

    for crop in crop_names:
        if crop in full_text or crop in name:
            record["host_crops"].append(crop)
    record["host_crops"] = list(set(record["host_crops"]))

    # 提取症状描述
    symptom_patterns = [
        r"(?:症状|为害症状|发病症状|危害症状|表现)[：:](.*?)(?=(?:发病|防治|传播|发生|规律|病原|病因)|$)",
        r"(?:为害|危害|侵害)[特点征]?(.*?)(?=(?:防治|传播|发生|规律|病原)|$)",
    ]
    for pattern in symptom_patterns:
        m = re.search(pattern, full_text, re.DOTALL)
        if m:
            text = m.group(1).strip()[:500]
            if len(text) > 20:
                record["symptoms"] = text
                break

    # 提取发病条件/发生规律
    condition_patterns = [
        r"(?:发病条件|发生规律|发生条件|流行规律|传播途径)[：:](.*?)(?=(?:防治|症状|为害|病原)|$)",
    ]
    for pattern in condition_patterns:
        m = re.search(pattern, full_text, re.DOTALL)
        if m:
            text = m.group(1).strip()[:500]
            if len(text) > 20:
                record["conditions"] = text
                break

    # 提取防治方案
    prevention_patterns = [
        r"(?:防治方法|防治措施|防治技术|综合防治|如何防治|防治)[：:](.*?)(?=(?:备注|参考|注意|相关)|$)",
    ]
    for pattern in prevention_patterns:
        m = re.search(pattern, full_text, re.DOTALL)
        if m:
            text = m.group(1).strip()[:800]
            if len(text) > 20:
                record["prevention"] = text
                break

    # 提取用药信息
    medicine_patterns = [
        r"(?:药剂防治|化学防治|推荐用药|用药|喷施|喷洒)[：:](.*?)(?=(?:农业防治|物理防治|生物防治|备注|参考)|$)",
    ]
    for pattern in medicine_patterns:
        m = re.search(pattern, full_text, re.DOTALL)
        if m:
            text = m.group(1).strip()[:500]
            if len(text) > 10:
                record["medicine"] = text
                break

    # 如果没有单独提取到用药，从防治方案中提取
    if not record["medicine"] and record["prevention"]:
        _extract_medicine_from_prevention(record)

    # 如果没有提取到症状，用全文前200字作为摘要
    if not record["symptoms"] and not record["summary"]:
        record["summary"] = full_text[:200].strip()


def _extract_medicine_from_prevention(record):
    """从防治方案中提取用药信息"""
    prevention = record.get("prevention", "")
    if not prevention:
        return

    # 常见农药名称模式
    medicine_keywords = [
        "多菌灵", "百菌清", "代森锰锌", "甲基硫菌灵", "三唑酮", "粉锈宁",
        "井冈霉素", "农用链霉素", "波尔多液", "石硫合剂", "吡虫啉", "啶虫脒",
        "阿维菌素", "氯氰菊酯", "高效氯氟氰菊酯", "毒死蜱", "辛硫磷",
        "敌敌畏", "乐果", "马拉硫磷", "溴氰菊酯", "氯虫苯甲酰胺",
        "甲维盐", "虫螨腈", "茚虫威", "氟虫脲", "噻虫嗪", "烯啶虫胺",
        "呋虫胺", "螺虫乙酯", "氟啶虫酰胺", "乙基多杀菌素",
        "苯醚甲环唑", "丙环唑", "戊唑醇", "己唑醇", "氟硅唑",
        "嘧菌酯", "醚菌酯", "吡唑醚菌酯", "肟菌酯", "氟菌唑",
        "咪鲜胺", "抑霉唑", "腐霉利", "异菌脲", "乙烯菌核利",
        "霜脲氰", "甲霜灵", "烯酰吗啉", "氟吗啉", "双炔酰菌胺",
        "噻菌铜", "噻森铜", "叶枯唑", "农用硫酸链霉素",
        "草甘膦", "百草枯", "草铵膦", "莠去津", "烟嘧磺隆",
    ]

    found = []
    for med in medicine_keywords:
        if med in prevention:
            # 提取包含该农药的句子
            sentences = prevention.split("。")
            for s in sentences:
                if med in s:
                    found.append(s.strip())
                    break

    if found:
        record["medicine"] = "。".join(found[:5])


# ============================================================
# 主流程
# ============================================================

PEST_KEYWORDS = {
    "水稻": [
        "稻瘟病", "水稻纹枯病", "水稻白叶枯病", "稻飞虱", "二化螟",
        "三化螟", "稻纵卷叶螟", "水稻条纹叶枯病", "水稻恶苗病",
        "稻蝗", "水稻胡麻斑病", "水稻细菌性条斑病", "稻粒黑粉病",
    ],
    "小麦": [
        "小麦锈病", "小麦赤霉病", "小麦白粉病", "小麦蚜虫",
        "小麦吸浆虫", "小麦纹枯病", "小麦全蚀病", "小麦根腐病",
        "麦蜘蛛", "小麦黑穗病",
    ],
    "玉米": [
        "玉米大斑病", "玉米小斑病", "玉米螟", "玉米锈病",
        "玉米丝黑穗病", "玉米蚜虫", "玉米褐斑病", "玉米茎腐病",
        "草地贪夜蛾", "玉米粗缩病",
    ],
    "蔬菜": [
        "番茄晚疫病", "番茄早疫病", "番茄灰霉病", "黄瓜霜霉病",
        "黄瓜白粉病", "白菜软腐病", "菜青虫", "小菜蛾",
        "蚜虫", "红蜘蛛", "白粉虱", "烟粉虱",
        "斜纹夜蛾", "甜菜夜蛾", "辣椒疫病", "茄子黄萎病",
        "蔬菜根结线虫病",
    ],
    "果树": [
        "柑橘黄龙病", "柑橘溃疡病", "柑橘红蜘蛛", "苹果腐烂病",
        "苹果褐斑病", "苹果斑点落叶病", "梨黑星病", "梨小食心虫",
        "葡萄霜霉病", "葡萄白腐病", "葡萄炭疽病", "桃褐腐病",
        "桃蚜", "荔枝蒂蛀虫", "芒果炭疽病", "猕猴桃溃疡病",
    ],
    "棉花": [
        "棉花枯萎病", "棉花黄萎病", "棉铃虫", "棉蚜",
        "棉花红蜘蛛", "棉花立枯病", "棉花炭疽病",
    ],
    "大豆": [
        "大豆花叶病毒病", "大豆根腐病", "大豆蚜虫",
        "大豆食心虫", "大豆灰斑病", "大豆霜霉病",
    ],
    "花生": [
        "花生叶斑病", "花生根腐病", "花生青枯病",
        "花生锈病", "花生蚜虫", "蛴螬",
    ],
}


def crawl_all():
    """主爬取流程：搜狗百科 + 搜索聚合"""
    all_records = []
    total = sum(len(v) for v in PEST_KEYWORDS.values())
    count = 0

    for crop, pests in PEST_KEYWORDS.items():
        print(f"\n{'='*50}")
        print(f"开始爬取 [{crop}] 相关病虫害，共 {len(pests)} 种")
        print(f"{'='*50}")

        for pest in pests:
            count += 1
            print(f"  [{count}/{total}] 爬取: {pest}")

            # 策略1：先尝试搜狗百科
            record = None
            baike_url = sogou_baike_search(pest)
            if baike_url:
                print(f"    → 找到搜狗百科词条")
                record = parse_sogou_baike(baike_url, pest)
                time.sleep(random.uniform(0.5, 1.5))

            # 策略2：如果百科内容不够，用搜索聚合补充
            if not record or (not record["symptoms"] and not record["prevention"]):
                print(f"    → 百科内容不足，搜索聚合补充...")
                search_results = sogou_search_pest(pest)
                if search_results:
                    for sr in search_results[:2]:
                        try:
                            extra = fetch_and_parse_result(sr["url"], pest)
                            if extra:
                                # 合并信息
                                if not record:
                                    record = extra
                                else:
                                    if not record["symptoms"] and extra["symptoms"]:
                                        record["symptoms"] = extra["symptoms"]
                                    if not record["prevention"] and extra["prevention"]:
                                        record["prevention"] = extra["prevention"]
                                    if not record["medicine"] and extra["medicine"]:
                                        record["medicine"] = extra["medicine"]
                                    if not record["conditions"] and extra["conditions"]:
                                        record["conditions"] = extra["conditions"]
                                time.sleep(random.uniform(1, 2))
                        except Exception:
                            pass

            if record:
                # 确保作物标签
                if crop not in record["host_crops"]:
                    record["host_crops"].append(crop)
                all_records.append(record)
                has_sym = "✓" if record["symptoms"] else "✗"
                has_prev = "✓" if record["prevention"] else "✗"
                has_med = "✓" if record["medicine"] else "✗"
                print(f"    ✓ 成功 症状:{has_sym} 防治:{has_prev} 用药:{has_med}")
            else:
                print(f"    ✗ 未获取到数据")

            time.sleep(random.uniform(1, 3))

    # 保存结果
    output_file = DATA_DIR / "pest_knowledge_raw.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)

    # 统计
    print(f"\n{'='*50}")
    print(f"爬取完成！共获取 {len(all_records)} 条病虫害知识")
    print(f"保存至: {output_file}")
    print(f"  有症状描述: {sum(1 for r in all_records if r.get('symptoms'))}")
    print(f"  有防治方案: {sum(1 for r in all_records if r.get('prevention'))}")
    print(f"  有用药建议: {sum(1 for r in all_records if r.get('medicine'))}")
    print(f"{'='*50}")

    return all_records


if __name__ == "__main__":
    crawl_all()
