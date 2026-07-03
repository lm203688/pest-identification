#!/usr/bin/env python3
"""
病虫害知识库批量扩充 v4 - 使用通义千问API
速度快、不限流、支持批量
"""

import json
import re
import time
import os
import requests
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "knowledge"
API_KEY = os.environ.get('DASHSCOPE_API_KEY', '')
API_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'

# 完整扩充列表
ALL_PESTS = {
    "水稻": ["稻曲病", "水稻菌核病", "褐飞虱", "稻蝽象", "稻铁甲虫"],
    "小麦": ["粘虫", "小麦叶蜂", "小麦潜叶蝇", "小麦黄矮病", "小麦丛矮病"],
    "玉米": ["玉米穗腐病", "玉米黑粉病", "玉米灰斑病", "玉米弯孢霉叶斑病", "玉米矮花叶病"],
    "大豆": ["大豆锈病", "大豆菌核病", "大豆紫斑病", "大豆褐斑病", "豆荚螟", "豆天蛾"],
    "花生": ["花生茎腐病", "花生白绢病", "花生黑斑病", "花生网斑病", "花生焦斑病"],
    "甘薯": ["甘薯茎线虫病", "甘薯根腐病", "甘薯软腐病", "甘薯瘟病", "甘薯天蛾", "甘薯叶甲"],
    "马铃薯": ["马铃薯晚疫病", "马铃薯早疫病", "马铃薯环腐病", "马铃薯黑胫病", "马铃薯疮痂病",
               "马铃薯病毒病", "马铃薯青枯病", "马铃薯二十八星瓢虫", "马铃薯块茎蛾"],
    "番茄": ["番茄枯萎病", "番茄溃疡病", "番茄斑枯病", "番茄白粉病", "番茄脐腐病",
             "番茄潜叶蝇", "番茄白粉虱", "番茄烟青虫"],
    "黄瓜": ["黄瓜黑星病", "黄瓜疫病", "黄瓜炭疽病", "黄瓜花叶病毒病", "黄瓜根结线虫病",
             "黄瓜靶斑病", "斑潜蝇", "黄瓜蓟马"],
    "白菜": ["白菜黑腐病", "白菜白斑病", "白菜根肿病", "白菜菌核病", "白菜干烧心",
             "白菜跳甲", "白菜夜蛾"],
    "辣椒": ["辣椒白粉病", "辣椒枯萎病", "辣椒疮痂病", "辣椒日灼病", "辣椒脐腐病",
             "辣椒烟青虫", "辣椒茶黄螨", "辣椒蓟马"],
    "茄子": ["茄子黄萎病", "茄子褐纹病", "茄子绵疫病", "茄子白粉病", "茄子枯萎病",
             "二十八星瓢虫", "茄子茶黄螨", "茄螟"],
    "西瓜": ["西瓜枯萎病", "西瓜炭疽病", "西瓜蔓枯病", "西瓜疫病", "西瓜白粉病",
             "西瓜病毒病", "西瓜根结线虫病", "瓜绢螟", "黄守瓜"],
    "萝卜": ["萝卜霜霉病", "萝卜黑腐病", "萝卜软腐病", "萝卜黑斑病", "萝卜根肿病",
             "萝卜蚜虫", "萝卜跳甲"],
    "芹菜": ["芹菜斑枯病", "芹菜叶斑病", "芹菜软腐病", "芹菜灰霉病", "芹菜菌核病", "芹菜斑潜蝇"],
    "韭菜": ["韭菜灰霉病", "韭菜疫病", "韭菜锈病", "韭蛆", "韭菜潜叶蝇"],
    "大葱": ["大葱霜霉病", "大葱紫斑病", "大葱锈病", "大葱软腐病", "葱蓟马", "葱蝇"],
    "生姜": ["姜瘟病", "姜斑点病", "姜炭疽病", "姜枯萎病", "姜螟"],
    "大蒜": ["大蒜叶枯病", "大蒜灰霉病", "大蒜锈病", "大蒜白腐病", "蒜蛆", "大蒜蓟马"],
    "柑橘": ["柑橘疮痂病", "柑橘树脂病", "柑橘黑斑病", "柑橘脂点黄斑病", "柑橘木虱",
             "柑橘粉虱", "柑橘花蕾蛆", "柑橘凤蝶"],
    "苹果": ["苹果斑点落叶病", "苹果轮纹病", "苹果红蜘蛛", "苹果蚜虫", "桃小食心虫",
             "苹果瘤蚜", "苹果绵蚜", "金纹细蛾"],
    "葡萄": ["葡萄黑痘病", "葡萄白粉病", "葡萄灰霉病", "葡萄透翅蛾", "葡萄虎天牛",
             "葡萄绿盲蝽", "葡萄短须螨"],
    "梨": ["梨黑星病", "梨锈病", "梨黑斑病", "梨轮纹病", "梨小食心虫",
           "梨木虱", "梨蚜", "梨网蝽"],
    "桃": ["桃褐腐病", "桃缩叶病", "桃疮痂病", "桃流胶病", "桃蚜",
           "桃潜叶蛾", "桃小食心虫", "桃红颈天牛"],
    "荔枝": ["荔枝霜疫霉病", "荔枝炭疽病", "荔枝酸腐病", "荔枝蒂蛀虫", "荔枝蝽象",
             "荔枝小灰蝶", "荔枝叶瘿蚊"],
    "芒果": ["芒果炭疽病", "芒果白粉病", "芒果细菌性黑斑病", "芒果蒂腐病", "芒果横线尾夜蛾",
             "芒果扁喙象", "芒果叶瘿蚊", "芒果蚜虫"],
    "香蕉": ["香蕉枯萎病", "香蕉叶斑病", "香蕉黑星病", "香蕉炭疽病", "香蕉束顶病",
             "香蕉花叶病", "香蕉象甲", "香蕉弄蝶"],
    "菠萝": ["菠萝心腐病", "菠萝黑腐病", "菠萝凋萎病", "菠萝粉蚧", "菠萝螟虫"],
    "猕猴桃": ["猕猴桃溃疡病", "猕猴桃褐斑病", "猕猴桃灰霉病", "猕猴桃软腐病",
               "猕猴桃介壳虫", "猕猴桃叶蝉"],
    "草莓": ["草莓灰霉病", "草莓白粉病", "草莓炭疽病", "草莓根腐病", "草莓红中柱病",
             "草莓芽枯病", "草莓蚜虫", "草莓红蜘蛛", "草莓蓟马"],
    "柿子": ["柿子炭疽病", "柿子角斑病", "柿子圆斑病", "柿蒂虫", "柿绵蚧"],
    "枣": ["枣疯病", "枣锈病", "枣炭疽病", "枣缩果病", "枣尺蠖", "枣粘虫", "枣龟蜡蚧"],
    "樱桃": ["樱桃褐斑病", "樱桃细菌性穿孔病", "樱桃流胶病", "樱桃灰霉病", "樱桃果蝇", "樱桃红蜘蛛"],
    "棉花": ["棉花炭疽病", "棉花立枯病", "棉花疫病", "棉红铃虫", "棉盲蝽", "棉蓟马"],
    "油菜": ["油菜菌核病", "油菜霜霉病", "油菜白锈病", "油菜病毒病", "油菜根肿病"],
    "甘蔗": ["甘蔗凤梨病", "甘蔗黑穗病", "甘蔗赤腐病", "甘蔗梢腐病", "甘蔗螟虫",
             "甘蔗绵蚜", "甘蔗蓟马"],
    "茶叶": ["茶饼病", "茶炭疽病", "茶云纹叶枯病", "茶轮斑病", "茶白星病",
             "茶小绿叶蝉", "茶尺蠖", "茶毛虫", "茶蚜", "茶叶螨类"],
    "烟草": ["烟草花叶病", "烟草黑胫病", "烟草赤星病", "烟草青枯病", "烟蚜", "烟青虫", "烟草粉虱"],
    "向日葵": ["向日葵菌核病", "向日葵锈病", "向日葵霜霉病", "向日葵列当", "向日葵螟"],
}


def call_qwen(prompt, retries=3):
    """调用通义千问API"""
    for attempt in range(retries):
        try:
            resp = requests.post(
                API_URL,
                headers={
                    'Authorization': f'Bearer {API_KEY}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': 'qwen-turbo',
                    'messages': [{'role': 'user', 'content': prompt}],
                    'temperature': 0.7,
                    'max_tokens': 2000,
                    'response_format': {'type': 'json_object'},
                },
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data['choices'][0]['message']['content']
                return content
            elif resp.status_code == 429:
                time.sleep(5)
            else:
                return None
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
    return None


def generate_single(crop, pest_name):
    """生成单条病虫害知识"""
    prompt = f"""请提供关于农作物病虫害"{pest_name}"（危害{crop}）的专业知识。

严格按照以下JSON格式输出：
{{
    "name": "{pest_name}",
    "aliases": ["别名1", "别名2"],
    "type": "病害或虫害",
    "host_crops": ["{crop}"],
    "summary": "一句话简介（50字以内）",
    "symptoms": "症状描述（200-300字，详细描述各部位症状）",
    "conditions": "发病条件或发生规律（150-200字）",
    "prevention": "综合防治方案（200-300字，包括农业防治、物理防治、化学防治）",
    "medicine": "推荐用药（列出3-5种具体农药名称、浓度和用法）"
}}"""

    content = call_qwen(prompt)
    if not content:
        return None

    try:
        data = json.loads(content)
        # 验证必要字段
        if not data.get('name') or not data.get('symptoms'):
            return None
        data['source'] = 'AI生成'
        data['source_url'] = ''
        return data
    except json.JSONDecodeError:
        # 尝试从文本中提取JSON
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                data = json.loads(json_match.group())
                data['source'] = 'AI生成'
                data['source_url'] = ''
                return data
            except:
                pass
    return None


def main():
    output = DATA_DIR / "pest_knowledge_ai.json"

    # 加载已有数据
    if output.exists():
        with open(output, 'r', encoding='utf-8') as f:
            existing = json.load(f)
    else:
        existing = []

    existing_names = {r['name'] for r in existing}

    # 计算新增
    new_pests = {}
    for crop, pests in ALL_PESTS.items():
        new_list = [p for p in pests if p not in existing_names]
        if new_list:
            new_pests[crop] = new_list

    total_new = sum(len(v) for v in new_pests.values())
    print(f"已有: {len(existing)} 条")
    print(f"待新增: {total_new} 条")
    print(f"目标总计: {len(existing) + total_new} 条")

    if total_new == 0:
        print("无需新增")
        return

    success = 0
    fail = 0
    count = 0

    for crop, pests in new_pests.items():
        print(f"\n{'='*40}")
        print(f"[{crop}] 新增 {len(pests)} 种")
        print(f"{'='*40}")

        for pest in pests:
            count += 1
            print(f"  [{count}/{total_new}] {pest}...", end=" ", flush=True)

            record = generate_single(crop, pest)

            if record:
                existing.append(record)
                existing_names.add(record['name'])
                success += 1
                s = "✓" if record.get('symptoms') else "✗"
                p = "✓" if record.get('prevention') else "✗"
                m = "✓" if record.get('medicine') else "✗"
                print(f"OK 症状:{s} 防治:{p} 用药:{m}")

                # 每20条保存
                if success % 20 == 0:
                    with open(output, 'w', encoding='utf-8') as f:
                        json.dump(existing, f, ensure_ascii=False, indent=2)
            else:
                fail += 1
                print("FAIL")

            time.sleep(0.5)

    # 最终保存
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    # 统计
    disease_count = sum(1 for r in existing if '虫' in r.get('type', ''))
    pest_count = len(existing) - disease_count

    print(f"\n{'='*50}")
    print(f"完成！共 {len(existing)} 条（新增 {success}，失败 {fail}）")
    print(f"  病害: {pest_count}")
    print(f"  虫害: {disease_count}")

    crop_stats = {}
    for r in existing:
        for c in r.get('host_crops', []):
            if isinstance(c, str):
                crop_stats[c] = crop_stats.get(c, 0) + 1
    print(f"\n覆盖 {len(crop_stats)} 种作物:")
    for crop, cnt in sorted(crop_stats.items(), key=lambda x: -x[1]):
        print(f"  {crop}: {cnt}")

    print(f"\n保存: {output}")


if __name__ == "__main__":
    main()
