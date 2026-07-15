#!/usr/bin/env python3
"""解析抓取的内容，生成结构化的知识点和题目"""
import json, os, sys, re
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'docs')
NEW_ITEMS_FILE = os.path.join(BASE_DIR, 'data', 'new_items.json')


def load_new_items():
    if os.path.exists(NEW_ITEMS_FILE):
        with open(NEW_ITEMS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def load_existing_data():
    data_path = os.path.join(DATA_DIR, 'data.json')
    if os.path.exists(data_path):
        with open(data_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def generate_id(prefix, existing_ids):
    """生成不重复的 ID"""
    max_num = 0
    for eid in existing_ids:
        if eid.startswith(prefix + '_'):
            try:
                num = int(eid.split('_')[-1])
                max_num = max(max_num, num)
            except:
                pass
    return f"{prefix}_{max_num + 1:03d}"


def process_content(new_items, existing_data):
    """处理新内容并合并到现有数据"""
    if not new_items or not new_items.get('knowledgePoints'):
        print("没有新内容需要处理")
        return None

    kps = existing_data.get('knowledgePoints', []) if existing_data else []
    questions = existing_data.get('questions', []) if existing_data else []

    existing_kp_ids = set(kp['id'] for kp in kps)
    existing_q_ids = set(q['id'] for q in questions)

    # Get existing ID prefixes
    existing_kp_prefixes = set()
    for kp_id in existing_kp_ids:
        parts = kp_id.split('_')
        if len(parts) >= 2:
            existing_kp_prefixes.add('_'.join(parts[:-1]))
    existing_q_prefixes = set()
    for q_id in existing_q_ids:
        parts = q_id.split('_')
        if len(parts) >= 2:
            existing_q_prefixes.add('_'.join(parts[:-1]))

    today = datetime.now().strftime('%Y%m%d')
    new_kps = []
    new_qs = []

    # Determine category based on content keywords
    def detect_category(title, content):
        cat_keywords = {
            'ershida': ['二十大', '中国式现代化', '党的', '全面从严治党'],
            '2024': ['2024', '二十届三中全会', '新质生产力', '嫦娥六号'],
            '2025': ['2025', '十四五', '抗战胜利80周年'],
            '2026': ['2026', '十五五'],
            'hebei': ['河北', '雄安', '京津冀', '燕赵'],
        }
        text = title + content
        for cat, kws in cat_keywords.items():
            for kw in kws:
                if kw in text:
                    return cat
        return 'daily'  # Default daily update category

    for item in new_items.get('knowledgePoints', []):
        title = item.get('title', '')
        content = item.get('content', '')
        if not title or not content:
            continue

        category = detect_category(title, content)
        importance = item.get('importance', 'medium')

        kp_id = generate_id(f'kp_{today}', existing_kp_ids)
        if kp_id in existing_kp_ids:
            continue

        kp = {
            'id': kp_id,
            'title': title[:80],
            'category': category,
            'date': today[:4] + '-' + today[4:6] + '-' + today[6:8],
            'importance': importance,
            'content': content[:600],
            'highlights': item.get('highlights', []),
            'tags': item.get('tags', []),
            'examFrequency': 'high' if importance in ('critical', 'high') else 'medium',
        }
        new_kps.append(kp)
        existing_kp_ids.add(kp_id)
        kps.append(kp)

    for item in new_items.get('questions', []):
        q_type = item.get('type', 'single')
        question = item.get('question', '')
        options = item.get('options', [])
        correct = item.get('correct', [])

        if not question or not options:
            continue

        q_id = generate_id(f'q_{today}', existing_q_ids)
        if q_id in existing_q_ids:
            continue

        q = {
            'id': q_id,
            'type': q_type,
            'category': 'daily',
            'difficulty': item.get('difficulty', 2),
            'question': question[:200],
            'options': [o[:150] for o in options],
            'correct': correct,
            'explanation': item.get('explanation', '')[:300],
            'highlights': item.get('highlights', []),
            'relatedKpId': new_kps[0]['id'] if new_kps else '',
            'source': '每日时政更新',
        }
        new_qs.append(q)
        existing_q_ids.add(q_id)
        questions.append(q)

    return {
        'knowledgePoints': kps,
        'questions': questions,
        'newKps': len(new_kps),
        'newQuestions': len(new_qs),
        'updateDate': today[:4] + '-' + today[4:6] + '-' + today[6:8],
    }


def save_merged_data(merged):
    """保存合并后的数据"""
    existing = load_existing_data()
    if existing is None:
        print("错误: 现有 data.json 未找到")
        return False

    existing['knowledgePoints'] = merged['knowledgePoints']
    existing['questions'] = merged['questions']
    existing['version'] = '1.' + datetime.now().strftime('%Y%m%d')
    existing['lastUpdated'] = merged['updateDate']
    existing['dailyUpdate'] = {
        'date': merged['updateDate'],
        'summary': f"新增{merged['newKps']}个知识点，{merged['newQuestions']}道练习题",
        'newKps': merged['newKps'],
        'newQuestions': merged['newQuestions'],
        'source': 'GitHub Actions 每日更新',
    }

    output_path = os.path.join(DATA_DIR, 'data.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"数据已更新: {merged['newKps']} 新知识点, {merged['newQuestions']} 新题目")
    print(f"总计: {len(merged['knowledgePoints'])} 知识点, {len(merged['questions'])} 题目")
    return True


def main():
    new_items = load_new_items()
    if not new_items:
        print("没有新抓取的内容")
        return

    existing_data = load_existing_data()
    if not existing_data:
        print("现有数据未找到，无法合并")
        return

    merged = process_content(new_items, existing_data)
    if merged and merged['newKps'] > 0:
        save_merged_data(merged)
    else:
        print("没有新的内容需要添加")


if __name__ == '__main__':
    main()
