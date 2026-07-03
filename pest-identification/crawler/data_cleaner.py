#!/usr/bin/env python3
"""
病虫害知识库数据清洗和结构化
将爬取的原始数据清洗为标准格式，准备导入MySQL
"""

import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "knowledge"


def clean_knowledge(raw: dict) -> dict:
    """清洗单条知识记录"""
    cleaned = {
        "name": raw.get("name", "").strip(),
        "aliases": raw.get("aliases", []),
        "host_crops": list(set(raw.get("host_crops", []))),
        "type": _classify_type(raw),
        "summary": _clean_field(raw.get("summary", "")),
        "symptoms": _clean_field(raw.get("symptoms", "")),
        "conditions": _clean_field(raw.get("conditions", "")),
        "prevention": _clean_field(raw.get("prevention", "")),
        "medicine": _extract_medicine(raw),
        "source": raw.get("source", ""),
        "source_url": raw.get("source_url", ""),
    }

    # 如果没有提取到用药信息，从防治方案中提取
    if not cleaned["medicine"] and cleaned["prevention"]:
        cleaned["medicine"] = _extract_medicine_from_text(cleaned["prevention"])

    return cleaned


def _classify_type(record: dict) -> str:
    """判断是病害还是虫害"""
    name = record.get("name", "")
    text = record.get("raw_text", "") + record.get("summary", "")

    pest_keywords = ["虫", "蛾", "蝶", "蝇", "蚜", "螨", "蝗", "螟", "虱", "蚁",
                     "蚧", "蝉", "蝽", "蚊", "蜂", "甲", "金龟", "天牛", "象甲",
                     "食心虫", "卷叶蛾", "夜蛾", "蛆", "蛴螬", "蝼蛄", "地老虎"]
    disease_keywords = ["病", "霉", "腐", "枯", "萎", "锈", "斑", "疫", "瘿",
                        "烂", "焦", "枯", "粉", "毒", "菌"]

    pest_score = sum(1 for k in pest_keywords if k in name)
    disease_score = sum(1 for k in disease_keywords if k in name)

    if pest_score > disease_score:
        return "虫害"
    elif disease_score > pest_score:
        return "病害"
    else:
        # 看正文
        pest_text = sum(1 for k in pest_keywords if k in text[:200])
        disease_text = sum(1 for k in disease_keywords if k in text[:200])
        if pest_text > disease_text:
            return "虫害"
        elif disease_text > pest_text:
            return "病害"
        return "其他"


def _extract_medicine(record: dict) -> str:
    """提取用药信息"""
    medicine = record.get("medicine", "")
    if medicine:
        return _clean_field(medicine)
    return ""


def _extract_medicine_from_text(text: str) -> str:
    """从防治文本中提取用药相关句子"""
    sentences = re.split(r"[。；\n]", text)
    medicine_sentences = []
    medicine_keywords = ["喷施", "喷雾", "用药", "药剂", "农药", "可湿性粉剂", "乳油",
                         "悬浮剂", "水剂", "粒剂", "粉剂", "倍液", "克/亩", "毫升/亩",
                         "多菌灵", "百菌清", "代森锰锌", "甲基硫菌灵", "三唑酮",
                         "吡虫啉", "啶虫脒", "阿维菌素", "氯氰菊酯", "高效氯氟氰菊酯",
                         "毒死蜱", "辛硫磷", "敌百虫", "杀虫双", "噻嗪酮"]

    for s in sentences:
        if any(k in s for k in medicine_keywords):
            medicine_sentences.append(s.strip())

    return "。".join(medicine_sentences)


def _clean_field(text: str) -> str:
    """清理字段文本"""
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^编辑\s*", "", text)
    return text


def process_all():
    """处理所有爬取的数据"""
    all_cleaned = []

    # 处理百度百科数据
    baike_file = DATA_DIR / "pest_knowledge_baike.json"
    if baike_file.exists():
        with open(baike_file, "r", encoding="utf-8") as f:
            baike_data = json.load(f)
        print(f"百度百科原始数据: {len(baike_data)} 条")

        for record in baike_data:
            cleaned = clean_knowledge(record)
            all_cleaned.append(cleaned)

    # 处理农技网站数据
    agri_file = DATA_DIR / "pest_knowledge_agri.json"
    if agri_file.exists():
        with open(agri_file, "r", encoding="utf-8") as f:
            agri_data = json.load(f)
        print(f"农技网站原始数据: {len(agri_data)} 条")

        for record in agri_data:
            cleaned = clean_knowledge(record)
            all_cleaned.append(cleaned)

    # 去重（按名称）
    seen = set()
    unique = []
    for r in all_cleaned:
        if r["name"] not in seen:
            seen.add(r["name"])
            unique.append(r)
        else:
            # 合并信息到已有记录
            for existing in unique:
                if existing["name"] == r["name"]:
                    if r["prevention"] and not existing["prevention"]:
                        existing["prevention"] = r["prevention"]
                    if r["medicine"] and not existing["medicine"]:
                        existing["medicine"] = r["medicine"]
                    existing["host_crops"] = list(set(existing["host_crops"] + r["host_crops"]))
                    break

    # 保存清洗后的数据
    output_file = DATA_DIR / "pest_knowledge_cleaned.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)

    # 统计
    print(f"\n清洗完成！共 {len(unique)} 条去重后的病虫害知识")
    print(f"  病害: {sum(1 for r in unique if r['type'] == '病害')}")
    print(f"  虫害: {sum(1 for r in unique if r['type'] == '虫害')}")
    print(f"  其他: {sum(1 for r in unique if r['type'] == '其他')}")
    print(f"  有症状描述: {sum(1 for r in unique if r['symptoms'])}")
    print(f"  有防治方案: {sum(1 for r in unique if r['prevention'])}")
    print(f"  有用药建议: {sum(1 for r in unique if r['medicine'])}")

    # 按作物统计
    crop_stats = {}
    for r in unique:
        for crop in r["host_crops"]:
            crop_stats[crop] = crop_stats.get(crop, 0) + 1
    print(f"\n按作物分布:")
    for crop, count in sorted(crop_stats.items(), key=lambda x: -x[1]):
        print(f"  {crop}: {count} 种")

    print(f"\n保存至: {output_file}")
    return unique


if __name__ == "__main__":
    process_all()
