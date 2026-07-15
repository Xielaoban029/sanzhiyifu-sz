#!/usr/bin/env python3
"""更新 data.json 并输出变更摘要（用于 commit message）"""
import json, os, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, 'docs', 'data.json')
NEW_ITEMS_FILE = os.path.join(BASE_DIR, 'data', 'new_items.json')


def main():
    changes = {'newKps': 0, 'newQuestions': 0, 'summary': ''}

    # Read existing data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        print("data.json 不存在，跳过更新")
        return

    # Read new items if available
    if os.path.exists(NEW_ITEMS_FILE):
        with open(NEW_ITEMS_FILE, 'r', encoding='utf-8') as f:
            new_data = json.load(f)
        changes['newKps'] = len(new_data.get('knowledgePoints', []))
        changes['newQuestions'] = len(new_data.get('questions', []))
    else:
        print("没有新的抓取数据")
        # Even without new data, update the timestamp
        data['lastUpdated'] = datetime.now().strftime('%Y-%m-%d')
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("updated_at_only")
        return

    # Verify data integrity
    kp_count = len(data.get('knowledgePoints', []))
    q_count = len(data.get('questions', []))
    cat_count = len(data.get('categories', []))

    print(f"当前数据: {kp_count} 知识点, {q_count} 题目, {cat_count} 分类")
    print(f"本次新增: {changes['newKps']} 知识点, {changes['newQuestions']} 题目")
    print(f"数据版本: {data.get('version', 'unknown')}")
    print(f"最后更新: {data.get('lastUpdated', 'unknown')}")

    # Generate change summary for commit message
    if changes['newKps'] > 0 or changes['newQuestions'] > 0:
        changes['summary'] = f"新增{changes['newKps']}个知识点、{changes['newQuestions']}道题目"
        print(f"变更摘要: {changes['summary']}")
    else:
        print("无变更")


if __name__ == '__main__':
    main()
