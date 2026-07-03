#!/usr/bin/env python3
"""
病虫害知识库批量扩充 v3 - 批量模式
每次prompt生成5条，减少API调用次数
"""

import json
import re
import time
import subprocess
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "knowledge"

# 扩充列表（去掉已有的）
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
    "芹菜": ["芹菜斑枯病", "芹菜叶斑病", "芹菜软腐病", "芹菜灰霉病", "芹菜菌核病",
             "芹菜斑潜蝇"],
    "韭菜": ["韭菜灰霉病", "韭菜疫病", "韭菜锈病", "韭蛆", "韭菜潜叶蝇"],
    "大葱": ["大葱霜霉病", "大葱紫斑病", "大葱锈病", "大葱软腐病", "葱蓟马", "葱蝇"],
    "生姜": ["姜瘟病", "姜斑点病", "姜炭疽病", "姜枯萎病", "姜螟"],
    "大蒜": ["大蒜叶枯病", "大蒜灰霉病", "大蒜锈病", "大蒜白腐病", "蒜蛆", "大蒜蓟马"],
    "柑橘": ["柑橘疮痂病", "柑橘树脂病", "柑橘黑斑病", "柑橘星天牛", "柑橘粉虱",
             "柑橘花蕾蛆", "柑橘实蝇", "柑橘木虱"],
    "苹果": ["苹果炭疽病", "苹果锈病", "苹果白粉病", "苹果霉心病", "苹果绵蚜",
             "苹果卷叶蛾", "苹果金纹细蛾", "苹果透翅蛾"],
    "葡萄": ["葡萄穗轴褐枯病", "葡萄房枯病", "葡萄黑腐病", "葡萄根癌病",
             "葡萄虎天牛", "葡萄绿盲蝽", "葡萄斑衣蜡蝉"],
    "梨": ["梨黑星病", "梨锈病", "梨黑斑病", "梨轮纹病", "梨腐烂病",
           "梨木虱", "梨蚜", "梨星毛虫", "梨网蝽", "梨茎蜂"],
    "桃": ["桃褐腐病", "桃缩叶病", "桃流胶病", "桃疮痂病", "桃细菌性穿孔病",
           "桃潜叶蛾", "桃蛀螟", "桃红颈天牛", "桃介壳虫"],
    "荔枝": ["荔枝霜疫霉病", "荔枝炭疽病", "荔枝酸腐病", "荔枝椿象",
             "荔枝瘿螨", "荔枝龟背天牛"],
    "芒果": ["芒果炭疽病", "芒果白粉病", "芒果细菌性黑斑病", "芒果蒂腐病",
             "芒果横线尾夜蛾", "芒果扁喙象", "芒果叶瘿蚊", "芒果介壳虫"],
    "香蕉": ["香蕉枯萎病", "香蕉叶斑病", "香蕉黑星病", "香蕉炭疽病",
             "香蕉束顶病", "香蕉象甲", "香蕉弄蝶"],
    "猕猴桃": ["猕猴桃溃疡病", "猕猴桃褐斑病", "猕猴桃灰霉病", "猕猴桃根腐病",
               "猕猴桃介壳虫", "猕猴桃叶蝉"],
    "草莓": ["草莓灰霉病", "草莓白粉病", "草莓炭疽病", "草莓根腐病",
             "草莓红中柱病", "草莓芽枯病", "草莓蚜虫", "草莓红蜘蛛", "草莓蓟马"],
    "柿子": ["柿子炭疽病", "柿子角斑病", "柿子圆斑病", "柿蒂虫", "柿绵蚧"],
    "枣": ["枣疯病", "枣锈病", "枣炭疽病", "枣缩果病", "枣尺蠖", "枣粘虫", "枣龟蜡蚧"],
    "樱桃": ["樱桃褐斑病", "樱桃细菌性穿孔病", "樱桃流胶病", "樱桃灰霉病",
             "樱桃果蝇", "樱桃红蜘蛛"],
    "棉花": ["棉花炭疽病", "棉花立枯病", "棉花疫病", "棉红铃虫", "棉盲蝽", "棉蓟马"],
    "油菜": ["油菜菌核病", "油菜霜霉病", "油菜白锈病", "油菜病毒病", "油菜根肿病"],
    "甘蔗": ["甘蔗凤梨病", "甘蔗黑穗病", "甘蔗赤腐病", "甘蔗梢腐病",
             "甘蔗螟虫", "甘蔗绵蚜", "甘蔗蓟马"],
    "茶叶": ["茶饼病", "茶炭疽病", "茶云纹叶枯病", "茶轮斑病", "茶白星病",
             "茶小绿叶蝉", "茶尺蠖", "茶毛虫", "茶蚜", "茶叶螨类"],
    "烟草": ["烟草花叶病", "烟草黑胫病", "烟草赤星病", "烟草青枯病",
             "烟蚜", "烟青虫", "烟草粉虱"],
    "向日葵": ["向日葵菌核病", "向日葵锈病", "向日葵霜霉病", "向日葵列当", "向日葵螟"],
}


def generate_batch(crop: str, pests: list, batch_size=5) -> list:
    """批量生成5条病虫害知识"""
    batch = pests[:batch_size]
    pest_names = "、".join(batch)

    prompt = f"""请提供以下{len(batch)}种农作物病虫害的专业知识，每种都是危害{crop}的病虫害。

病虫害列表：{pest_names}

请严格按照以下JSON数组格式输出，不要输出其他内容：
[
  {{
    "name": "病虫害名称",
    "aliases": ["别名1"],
    "type": "病害或虫害",
    "host_crops": ["{crop}"],
    "summary": "一句话简介",
    "symptoms": "症状描述200字",
    "conditions": "发病条件150字",
    "prevention": "防治方案200字",
    "medicine": "推荐用药3-5种"
  }}
]"""

    try:
        result = subprocess.run(
            ['z-ai', 'chat', '-p', prompt, '-m', 'glm-4-flash'],
            capture_output=True, text=True, timeout=60
        )
        raw = result.stdout.strip()

        # 解析API响应
        start = raw.find('{')
        if start < 0:
            return []

        try:
            outer = json.loads(raw[start:])
            content = outer['choices'][0]['message']['content']
        except:
            content = raw[start:]

        # 提取JSON数组
        json_match = re.search(r'\[[\s\S]*\]', content)
        if not json_match:
            return []

        data = json.loads(json_match.group())

        # 标准化
        results = []
        for item in data:
            if not isinstance(item, dict) or 'name' not in item:
                continue
            for field in ['symptoms', 'conditions', 'prevention', 'medicine']:
                val = item.get(field)
                if isinstance(val, list):
                    item[field] = '\n'.join(
                        json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else str(v)
                        for v in val
                    )
            if isinstance(item.get('aliases'), list):
                item['aliases'] = ','.join(str(a) for a in item['aliases'])
            item['source'] = 'AI生成'
            item['source_url'] = ''
            results.append(item)

        return results

    except Exception as e:
        print(f"ERR:{e}")
        return []


def main():
    output = DATA_DIR / "pest_knowledge_ai.json"

    # 加载已有数据
    with open(output, 'r', encoding='utf-8') as f:
        existing = json.load(f)

    existing_names = {r['name'] for r in existing}
    print(f"已有 {len(existing)} 条")

    # 统计待新增
    new_pests = {}
    for crop, pests in ALL_PESTS.items():
        new_list = [p for p in pests if p not in existing_names]
        if new_list:
            new_pests[crop] = new_list

    total_new = sum(len(v) for v in new_pests.values())
    print(f"待新增: {total_new} 条")

    if total_new == 0:
        print("无需新增")
        return

    success = 0
    fail = 0

    for crop, pests in new_pests.items():
        print(f"\n[{crop}] 新增 {len(pests)} 种")

        # 每5条一批
        for i in range(0, len(pests), 5):
            batch = pests[i:i+5]
            print(f"  批次 {batch}...", end=" ", flush=True)

            results = generate_batch(crop, batch)

            if results:
                for r in results:
                    if r['name'] not in existing_names:
                        existing.append(r)
                        existing_names.add(r['name'])
                        success += 1
                print(f"OK +{len(results)}")
            else:
                fail += len(batch)
                print("FAIL")

            # 保存
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)

            time.sleep(1)  # 批量模式间隔长一点

    # 最终统计
    print(f"\n{'='*50}")
    print(f"完成！共 {len(existing)} 条（新增 {success}，失败 {fail}）")

    crop_stats = {}
    for r in existing:
        for c in r.get('host_crops', []):
            crop_stats[c] = crop_stats.get(c, 0) + 1
    print(f"覆盖 {len(crop_stats)} 种作物:")
    for crop, cnt in sorted(crop_stats.items(), key=lambda x: -x[1])[:15]:
        print(f"  {crop}: {cnt}")


if __name__ == "__main__":
    main()
