#!/usr/bin/env python3
"""
病虫害知识库爬虫 - 百度百科 + 农技网站
爬取内容：病虫害名称、别名、危害作物、症状、发病条件、防治方案、推荐用药
存储：JSON文件（后续导入MySQL）
"""

import json
import os
import re
import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, urljoin
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "knowledge"
DATA_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 12; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# ============================================================
# 第一部分：百度百科爬虫
# ============================================================

# 常见农作物病虫害关键词列表（按作物分类）
PEST_KEYWORDS = {
    "水稻": [
        "稻瘟病", "水稻纹枯病", "水稻白叶枯病", "稻飞虱", "二化螟",
        "三化螟", "稻纵卷叶螟", "水稻条纹叶枯病", "水稻恶苗病",
        "稻蝗", "稻苞虫", "水稻胡麻斑病", "水稻细菌性条斑病",
        "稻粒黑粉病", "水稻干尖线虫病"
    ],
    "小麦": [
        "小麦锈病", "小麦赤霉病", "小麦白粉病", "小麦蚜虫",
        "小麦吸浆虫", "小麦纹枯病", "小麦全蚀病", "小麦根腐病",
        "小麦叶枯病", "麦蜘蛛", "小麦黑穗病"
    ],
    "玉米": [
        "玉米大斑病", "玉米小斑病", "玉米螟", "玉米锈病",
        "玉米丝黑穗病", "玉米蚜虫", "玉米褐斑病", "玉米茎腐病",
        "草地贪夜蛾", "玉米穗虫", "玉米粗缩病"
    ],
    "蔬菜": [
        "番茄晚疫病", "番茄早疫病", "番茄灰霉病", "黄瓜霜霉病",
        "黄瓜白粉病", "白菜软腐病", "菜青虫", "小菜蛾",
        "蚜虫", "红蜘蛛", "白粉虱", "烟粉虱", "斜纹夜蛾",
        "甜菜夜蛾", "辣椒疫病", "茄子黄萎病", "豆角锈病",
        "大葱霜霉病", "芹菜斑枯病", "蔬菜根结线虫病"
    ],
    "果树": [
        "柑橘黄龙病", "柑橘溃疡病", "柑橘红蜘蛛", "苹果腐烂病",
        "苹果褐斑病", "苹果斑点落叶病", "梨黑星病", "梨小食心虫",
        "葡萄霜霉病", "葡萄白腐病", "葡萄炭疽病", "桃褐腐病",
        "桃蚜", "荔枝蒂蛀虫", "芒果炭疽病", "猕猴桃溃疡病"
    ],
    "棉花": [
        "棉花枯萎病", "棉花黄萎病", "棉铃虫", "棉蚜",
        "棉花红蜘蛛", "棉花立枯病", "棉花炭疽病"
    ],
    "大豆": [
        "大豆花叶病毒病", "大豆根腐病", "大豆蚜虫",
        "大豆食心虫", "大豆灰斑病", "大豆霜霉病"
    ],
    "花生": [
        "花生叶斑病", "花生根腐病", "花生青枯病",
        "花生锈病", "花生蚜虫", "蛴螬"
    ],
}


def fetch_baidu_baike(keyword: str) -> dict | None:
    """爬取百度百科单个词条"""
    try:
        # 搜索百科
        search_url = f"https://baike.baidu.com/item/{quote(keyword)}"
        resp = SESSION.get(search_url, timeout=15, allow_redirects=True)
        resp.encoding = "utf-8"

        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        # 检查是否是有效词条页
        content = soup.find("div", class_="main-content")
        if not content:
            content = soup.find("div", class_="J-lemma-content")
        if not content:
            return None

        result = {
            "name": keyword,
            "source": "百度百科",
            "source_url": search_url,
            "aliases": [],
            "summary": "",
            "symptoms": "",
            "conditions": "",
            "prevention": "",
            "medicine": "",
            "host_crops": [],
            "raw_text": "",
        }

        # 提取摘要
        summary_tag = soup.find("div", class_="lemma-summary")
        if summary_tag:
            result["summary"] = _clean_text(summary_tag.get_text())

        # 提取正文各段落
        paragraphs = content.find_all(["div", "p", "h2", "h3"])
        full_text_parts = []
        current_section = ""

        for p in paragraphs:
            text = _clean_text(p.get_text())
            if not text:
                continue

            # 检测章节标题
            if p.name in ["h2", "h3"] or p.get("class") and any("title" in c for c in p.get("class", [])):
                current_section = text
                full_text_parts.append(f"\n## {text}\n")
                continue

            full_text_parts.append(text)

            # 按章节分类提取关键信息
            section_lower = current_section.lower()
            text_lower = text.lower()

            if any(k in section_lower for k in ["症状", "为害", "危害", "表现", "特征"]):
                result["symptoms"] += text + "\n"
            elif any(k in section_lower for k in ["发病条件", "发生规律", "传播", "流行", "环境"]):
                result["conditions"] += text + "\n"
            elif any(k in section_lower for k in ["防治", "治疗", "防控", "治理"]):
                result["prevention"] += text + "\n"
                # 尝试提取用药信息
                if any(k in text for k in ["喷施", "喷雾", "用药", "药剂", "农药", "可湿性粉剂", "乳油", "悬浮剂"]):
                    result["medicine"] += text + "\n"

        result["raw_text"] = "\n".join(full_text_parts)

        # 尝试提取别名
        alias_tag = soup.find("span", class_="view-tip-text")
        if alias_tag:
            alias_text = alias_tag.get_text()
            if "别名" in alias_text or "又称" in alias_text:
                result["aliases"] = [a.strip() for a in re.split(r"[，、,；;]", alias_text) if a.strip()]

        # 从摘要和正文中提取危害作物
        for crop in ["水稻", "小麦", "玉米", "棉花", "大豆", "花生", "番茄", "黄瓜", "白菜",
                      "柑橘", "苹果", "梨", "葡萄", "桃", "荔枝", "芒果", "猕猴桃", "蔬菜"]:
            if crop in result["summary"] or crop in result["raw_text"]:
                result["host_crops"].append(crop)

        return result

    except Exception as e:
        print(f"  [ERROR] 爬取 {keyword} 失败: {e}")
        return None


def _clean_text(text: str) -> str:
    """清理文本"""
    text = re.sub(r"\[\d+\]", "", text)  # 去掉引用标记 [1]
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ============================================================
# 第二部分：中国农业农村信息网爬虫
# ============================================================

def fetch_agri_pest_list() -> list[dict]:
    """爬取农业农村信息网病虫害列表"""
    results = []
    try:
        base_url = "https://www.agri.cn/sc/zxjc/zwbch"
        resp = SESSION.get(base_url, timeout=15)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "lxml")

        # 提取文章链接
        links = soup.find_all("a", href=True)
        for link in links:
            href = link.get("href", "")
            title = link.get_text(strip=True)
            if title and ("病虫" in title or "防治" in title or "疫病" in title):
                full_url = urljoin(base_url, href)
                results.append({"title": title, "url": full_url})

    except Exception as e:
        print(f"[ERROR] 爬取农技网站列表失败: {e}")

    return results


def fetch_agri_article(url: str) -> dict | None:
    """爬取农技网站文章详情"""
    try:
        resp = SESSION.get(url, timeout=15)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "lxml")

        content = soup.find("div", class_="article-content") or soup.find("div", class_="content")
        if not content:
            return None

        title_tag = soup.find("h1") or soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        text = _clean_text(content.get_text())

        return {
            "name": title,
            "source": "农业农村信息网",
            "source_url": url,
            "raw_text": text,
            "symptoms": "",
            "conditions": "",
            "prevention": text,  # 农技文章通常整篇都是防治内容
            "medicine": "",
            "host_crops": [],
        }

    except Exception as e:
        print(f"  [ERROR] 爬取文章 {url} 失败: {e}")
        return None


# ============================================================
# 第三部分：图片爬虫
# ============================================================

IMAGE_DIR = Path(__file__).parent.parent / "data" / "images"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)


def search_baidu_images(keyword: str, max_images: int = 50) -> list[str]:
    """搜索百度图片获取图片URL列表"""
    image_urls = []
    try:
        # 百度图片搜索API
        search_url = "https://image.baidu.com/search/acjson"
        params = {
            "tn": "resultjson_com",
            "word": f"{keyword} 病虫害",
            "pn": 0,
            "rn": max_images,
            "ipn": "rj",
            "fp": "result",
        }
        resp = SESSION.get(search_url, params=params, timeout=15)
        data = resp.json()

        for item in data.get("data", []):
            url = item.get("thumbURL") or item.get("middleURL") or item.get("objURL")
            if url and url.startswith("http"):
                image_urls.append(url)

    except Exception as e:
        print(f"  [ERROR] 搜索图片 {keyword} 失败: {e}")

    return image_urls


def download_images(keyword: str, urls: list[str], max_count: int = 30) -> int:
    """下载图片到本地"""
    crop_dir = IMAGE_DIR / keyword.replace("/", "_")
    crop_dir.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    for i, url in enumerate(urls[:max_count]):
        try:
            resp = SESSION.get(url, timeout=10, stream=True)
            if resp.status_code == 200 and len(resp.content) > 5000:  # 过滤太小的图
                ext = ".jpg"
                if "png" in resp.headers.get("content-type", ""):
                    ext = ".png"
                filepath = crop_dir / f"{downloaded + 1:04d}{ext}"
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                downloaded += 1

            time.sleep(random.uniform(0.3, 0.8))

        except Exception:
            continue

    return downloaded


# ============================================================
# 主流程
# ============================================================

def crawl_knowledge_base():
    """主爬虫流程：先爬文字知识库"""
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

            record = fetch_baidu_baike(pest)
            if record:
                record["host_crops"] = list(set(record["host_crops"] + [crop]))
                all_records.append(record)
                print(f"    ✓ 成功 - 症状:{len(record['symptoms'])}字 防治:{len(record['prevention'])}字")
            else:
                print(f"    ✗ 未找到词条")

            time.sleep(random.uniform(1.0, 2.5))  # 礼貌爬取

    # 保存结果
    output_file = DATA_DIR / "pest_knowledge_baike.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"爬取完成！共获取 {len(all_records)} 条病虫害知识")
    print(f"保存至: {output_file}")
    print(f"{'='*50}")

    # 统计
    has_symptoms = sum(1 for r in all_records if r["symptoms"])
    has_prevention = sum(1 for r in all_records if r["prevention"])
    has_medicine = sum(1 for r in all_records if r["medicine"])
    print(f"  有症状描述: {has_symptoms}")
    print(f"  有防治方案: {has_prevention}")
    print(f"  有用药建议: {has_medicine}")

    return all_records


def crawl_images(knowledge_records: list[dict], images_per_pest: int = 30):
    """图片爬虫流程"""
    print(f"\n开始爬取图片，每种病虫害目标 {images_per_pest} 张")

    total_downloaded = 0
    for i, record in enumerate(knowledge_records):
        name = record["name"]
        print(f"\n  [{i+1}/{len(knowledge_records)}] 搜索图片: {name}")

        urls = search_baidu_images(name, max_images=images_per_pest * 2)
        if urls:
            count = download_images(name, urls, max_count=images_per_pest)
            total_downloaded += count
            print(f"    下载 {count} 张图片")
        else:
            print(f"    未找到图片")

        time.sleep(random.uniform(1.0, 2.0))

    print(f"\n图片爬取完成！共下载 {total_downloaded} 张")
    return total_downloaded


def crawl_agri_articles():
    """爬取农技网站文章"""
    print("\n开始爬取农业农村信息网文章...")

    articles = fetch_agri_pest_list()
    print(f"找到 {len(articles)} 篇相关文章")

    results = []
    for i, article in enumerate(articles[:20]):  # 先爬20篇
        print(f"  [{i+1}/{min(len(articles), 20)}] {article['title']}")
        detail = fetch_agri_article(article["url"])
        if detail:
            results.append(detail)
        time.sleep(random.uniform(1.0, 2.0))

    output_file = DATA_DIR / "pest_knowledge_agri.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"农技文章爬取完成，共 {len(results)} 篇")
    return results


if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "knowledge"

    if mode == "knowledge":
        crawl_knowledge_base()
    elif mode == "images":
        # 先加载已有的知识库，再爬图片
        kb_file = DATA_DIR / "pest_knowledge_baike.json"
        if kb_file.exists():
            with open(kb_file, "r", encoding="utf-8") as f:
                records = json.load(f)
            crawl_images(records, images_per_pest=30)
        else:
            print("请先运行 knowledge 模式爬取文字知识库")
    elif mode == "agri":
        crawl_agri_articles()
    elif mode == "all":
        records = crawl_knowledge_base()
        crawl_agri_articles()
        crawl_images(records, images_per_pest=30)
    else:
        print("用法: python crawler.py [knowledge|images|agri|all]")
