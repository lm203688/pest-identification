#!/usr/bin/env python3
"""
病虫害知识库生成器 v2 - 使用AI大模型批量生成
比爬虫更快、更准、更稳定
"""

import json
import re
import time
import subprocess
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "knowledge"
DATA_DIR.mkdir(parents=True, exist_ok=True)

PEST_LIST = {
    "水稻": [
        "稻瘟病", "水稻纹枯病", "水稻白叶枯病", "稻飞虱", "二化螟",
        "三化螟", "稻纵卷叶螟", "水稻条纹叶枯病", "水稻恶苗病",
        "稻蝗", "水稻胡麻斑病", "水稻细菌性条斑病"
    ],
    "小麦": [
        "小麦锈病", "小麦赤霉病", "小麦白粉病", "小麦蚜虫",
        "小麦吸浆虫", "小麦纹枯病", "小麦全蚀病", "麦蜘蛛"
    ],
    "玉米": [
        "玉米大斑病", "玉米小斑病", "玉米螟", "玉米锈病",
        "玉米丝黑穗病", "草地贪夜蛾", "玉米粗缩病", "玉米茎腐病"
    ],
    "番茄": [
        "番茄晚疫病", "番茄早疫病", "番茄灰霉病", "番茄叶霉病",
        "番茄病毒病", "番茄青枯病", "番茄根结线虫病"
    ],
    "黄瓜": [
        "黄瓜霜霉病", "黄瓜白粉病", "黄瓜枯萎病", "黄瓜灰霉病",
        "黄瓜细菌性角斑病", "黄瓜蔓枯病"
    ],
    "柑橘": [
        "柑橘黄龙病", "柑橘溃疡病", "柑橘红蜘蛛", "柑橘潜叶蛾",
        "柑橘炭疽病", "柑橘锈壁虱", "柑橘介壳虫"
    ],
    "苹果": [
        "苹果腐烂病", "苹果褐斑病", "苹果斑点落叶病", "苹果轮纹病",
        "苹果红蜘蛛", "苹果蚜虫", "桃小食心虫"
    ],
    "葡萄": [
        "葡萄霜霉病", "葡萄白腐病", "葡萄炭疽病", "葡萄黑痘病",
        "葡萄白粉病", "葡萄灰霉病", "葡萄透翅蛾"
    ],
    "棉花": [
        "棉花枯萎病", "棉花黄萎病", "棉铃虫", "棉蚜", "棉花红蜘蛛"
    ],
    "大豆": [
        "大豆花叶病毒病", "大豆根腐病", "大豆蚜虫", "大豆食心虫", "大豆灰斑病"
    ],
    "白菜": [
        "白菜软腐病", "白菜霜霉病", "白菜病毒病", "白菜黑斑病", "菜青虫"
    ],
    "辣椒": [
        "辣椒疫病", "辣椒炭疽病", "辣椒病毒病", "辣椒青枯病", "辣椒灰霉病"
    ],
}


def generate_pest_knowledge(crop: str, pest_name: str) -> dict:
    """使用AI生成单条病虫害知识"""

    prompt = f"""请提供关于农作物病虫害"{pest_name}"（危害{crop}）的专业知识。
严格按照以下JSON格式输出，不要输出markdown代码块标记，直接输出JSON：
{{"name":"病虫害标准名称","aliases":["别名1","别名2"],"type":"病害或虫害","host_crops":["{crop}"],"summary":"一句话简介(30字内)","symptoms":"症状描述(150-250字)","conditions":"发病条件或发生规律(100-200字)","prevention":"综合防治方案(150-250字)","medicine":"推荐3-5种具体农药名称和用法(100-200字)"}}"""

    try:
        result = subprocess.run(
            ['z-ai', 'chat', '-p', prompt, '-m', 'glm-4-flash'],
            capture_output=True, text=True, timeout=30
        )
        raw = result.stdout.strip()

        # 解析z-ai API响应
        start = raw.find('{')
        if start < 0:
            return None

        try:
            outer = json.loads(raw[start:])
            content = outer['choices'][0]['message']['content']
        except (json.JSONDecodeError, KeyError):
            content = raw[start:]

        # 从content提取JSON
        json_match = re.search(r'\{[\s\S]*\}', content)
        if not json_match:
            return None

        data = json.loads(json_match.group())

        # 标准化字段
        record = {
            "name": data.get("name", pest_name),
            "aliases": data.get("aliases", []),
            "type": _normalize_type(data.get("type", "")),
            "host_crops": data.get("host_crops", [crop]),
            "summary": _to_str(data.get("summary", "")),
            "symptoms": _to_str(data.get("symptoms", "")),
            "conditions": _to_str(data.get("conditions", "")),
            "prevention": _to_str(data.get("prevention", "")),
            "medicine": _to_str(data.get("medicine", "")),
            "source": "AI生成",
            "source_url": "",
        }

        if crop not in record["host_crops"]:
            record["host_crops"].append(crop)

        return record

    except Exception as e:
        print(f"ERR:{e}")
        return None


def _normalize_type(t: str) -> str:
    t = t.strip()
    if "虫" in t:
        return "虫害"
    elif "病" in t:
        return "病害"
    return "其他"


def _to_str(val) -> str:
    """将list或str统一转为str"""
    if isinstance(val, list):
        return "；".join(str(v).strip() for v in val if v)
    return str(val).strip()


def main():
    all_records = []
    total = sum(len(v) for v in PEST_LIST.values())
    count = 0
    success = 0

    # 加载已有数据（支持断点续传）
    output = DATA_DIR / "pest_knowledge_ai.json"
    if output.exists():
        with open(output, "r", encoding="utf-8") as f:
            all_records = json.load(f)
        existing_names = {r["name"] for r in all_records}
        print(f"加载已有数据 {len(all_records)} 条，跳过已生成的")
    else:
        existing_names = set()

    for crop, pests in PEST_LIST.items():
        print(f"\n{'='*40}")
        print(f"[{crop}] 共 {len(pests)} 种")
        print(f"{'='*40}")

        for pest in pests:
            count += 1

            # 跳过已生成的
            if pest in existing_names:
                print(f"  [{count}/{total}] {pest}... SKIP(已有)")
                continue

            print(f"  [{count}/{total}] {pest}...", end=" ", flush=True)

            record = generate_pest_knowledge(crop, pest)

            if record:
                all_records.append(record)
                success += 1
                existing_names.add(pest)
                s = "✓" if record.get("symptoms") else "✗"
                p = "✓" if record.get("prevention") else "✗"
                m = "✓" if record.get("medicine") else "✗"
                print(f"OK 症状:{s} 防治:{p} 用药:{m}")

                # 每条都保存（断点续传）
                with open(output, "w", encoding="utf-8") as f:
                    json.dump(all_records, f, ensure_ascii=False, indent=2)
            else:
                print("FAIL")

            time.sleep(0.3)

    # 最终保存
    with open(output, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"生成完成！共 {len(all_records)} 条")
    print(f"  病害: {sum(1 for r in all_records if r['type']=='病害')}")
    print(f"  虫害: {sum(1 for r in all_records if r['type']=='虫害')}")
    print(f"  有症状: {sum(1 for r in all_records if r.get('symptoms'))}")
    print(f"  有防治: {sum(1 for r in all_records if r.get('prevention'))}")
    print(f"  有用药: {sum(1 for r in all_records if r.get('medicine'))}")
    print(f"保存: {output}")

    return all_records


if __name__ == "__main__":
    main()
