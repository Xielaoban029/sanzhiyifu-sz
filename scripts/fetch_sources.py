#!/usr/bin/env python3
"""多源时政抓取脚本 - 用于 GitHub Actions 每日更新
多源冗余设计，保证 100% 抓取成功率"""

import json, os, sys, re, hashlib
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'cache')
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'new_items.json')

os.makedirs(CACHE_DIR, exist_ok=True)

# ===== 多源配置 =====
SOURCES = [
    {
        'name': '中国政府网要闻',
        'url': 'https://www.gov.cn/yaowen/',
        'parser': 'gov_cn',
        'priority': 1,
    },
    {
        'name': '新华社时政',
        'url': 'https://www.xinhuanet.com/politics/',
        'parser': 'xinhua',
        'priority': 2,
    },
    {
        'name': '中国政府网最新政策',
        'url': 'https://www.gov.cn/zhengce/',
        'parser': 'gov_cn',
        'priority': 3,
    },
    {
        'name': '河北省政府',
        'url': 'https://www.hebei.gov.cn/',
        'parser': 'hebei_gov',
        'priority': 3,
    },
    {
        'name': '共产党员网',
        'url': 'https://www.12371.cn/',
        'parser': '12371',
        'priority': 4,
    },
    {
        'name': '人民日报时政',
        'url': 'https://www.people.com.cn/',
        'parser': 'people',
        'priority': 5,
    },
]

# ===== 重要度关键词 =====
CRITICAL_KEYWORDS = [
    '习近平', '总书记', '二十大', '中国式现代化',
    '核心', '首要', '本质', '中心任务', '根本',
    '必须', '坚持', '全面', '深化', '决定性',
]
HIGH_KEYWORDS = [
    '国务院', '总理', '政府工作报告', '一号文件',
    '高质量发展', '乡村振兴', '共同富裕', '改革',
    '全国两会', '中央经济工作', '全会', '重要讲话',
]
MEDIUM_KEYWORDS = [
    '部署', '印发', '通知', '发布', '召开',
    '强调', '指出', '要求', '规划', '意见',
]

# ===== 缓存池（抓取失败时使用）=====
BUFFER_POOL = [
    {"title": "习近平重要讲话", "content": "习近平总书记始终强调坚持和发展中国特色社会主义，推进全面从严治党，以中国式现代化全面推进中华民族伟大复兴。", "tags": ["总书记", "重要讲话"]},
    {"title": "高质量发展", "content": "高质量发展是全面建设社会主义现代化国家的首要任务。必须完整、准确、全面贯彻新发展理念，着力推动高质量发展，构建高水平社会主义市场经济体制。", "tags": ["经济", "发展"]},
    {"title": "中国式现代化", "content": "中国式现代化是中国共产党领导的社会主义现代化。既有各国现代化的共同特征，更有基于自己国情的中国特色：人口规模巨大的现代化、全体人民共同富裕的现代化、物质文明和精神文明相协调的现代化、人与自然和谐共生的现代化、走和平发展道路的现代化。", "tags": ["现代化", "核心"]},
    {"title": "乡村振兴", "content": "全面推进乡村振兴是新时代建设农业强国的重要任务。要扎实推动乡村产业、人才、文化、生态、组织振兴，巩固拓展脱贫攻坚成果同乡村振兴有效衔接。", "tags": ["乡村振兴", "三农"]},
    {"title": "全过程人民民主", "content": "全过程人民民主是社会主义民主政治的本质属性。要健全人民当家作主制度体系，扩大人民有序政治参与，保证人民依法实行民主选举、民主协商、民主决策、民主管理、民主监督。", "tags": ["民主", "政治"]},
    {"title": "新质生产力", "content": "新质生产力是创新起主导作用，摆脱传统经济增长方式、生产力发展路径，具有高科技、高效能、高质量特征，符合新发展理念的先进生产力质态。由技术革命性突破、生产要素创新性配置、产业深度转型升级而催生。", "tags": ["经济", "创新"]},
    {"title": "京津冀协同发展", "content": "京津冀协同发展是重大国家战略。河北的定位是\"三区一基地\"：全国现代商贸物流重要基地、产业转型升级试验区、新型城镇化与城乡统筹示范区、京津冀生态环境支撑区。", "tags": ["河北", "京津冀"]},
    {"title": "雄安新区", "content": "设立河北雄安新区是千年大计、国家大事。雄安新区位于河北省雄县、容城、安新三县，是北京非首都功能疏解集中承载地。", "tags": ["河北", "雄安"]},
    {"title": "党的中心任务", "content": "从现在起，中国共产党的中心任务就是团结带领全国各族人民全面建成社会主义现代化强国、实现第二个百年奋斗目标，以中国式现代化全面推进中华民族伟大复兴。", "tags": ["二十大", "核心"]},
    {"title": "三个务必", "content": "三个务必：务必不忘初心、牢记使命，务必谦虚谨慎、艰苦奋斗，务必敢于斗争、善于斗争。", "tags": ["二十大", "党建"]},
    {"title": "二十届三中全会", "content": "二十届三中全会于2024年7月在北京召开，重点研究进一步全面深化改革、推进中国式现代化问题。全会通过《中共中央关于进一步全面深化改革、推进中国式现代化的决定》。", "tags": ["改革", "全会"]},
    {"title": "中央一号文件", "content": "中央一号文件原指中共中央每年发布的第一份文件，现在已成为中共中央、国务院重视农村问题的专有名词。历年一号文件聚焦\"三农\"工作，推进乡村全面振兴。", "tags": ["三农", "政策"]},
    {"title": "新时代六尺巷工作法", "content": "\"六尺巷\"典故蕴含谦和礼让、以和为贵的中华优秀传统文化。新时代六尺巷工作法是将传统文化融入基层治理的创新实践，推动矛盾纠纷源头化解。", "tags": ["治理", "文化"]},
    {"title": "新安全格局", "content": "国家安全是民族复兴的根基。要坚持以人民安全为宗旨、以政治安全为根本、以经济安全为基础，健全国家安全体系，增强维护国家安全能力。", "tags": ["安全", "政治"]},
    {"title": "生态文明建设", "content": "中国坚持绿水青山就是金山银山的理念，坚持山水林田湖草沙一体化保护和系统治理，推动绿色发展，促进人与自然和谐共生。", "tags": ["生态", "发展"]},
]


def fetch_url(url, timeout=15):
    """尝试抓取 URL，支持多种编码"""
    try:
        import requests
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        resp = requests.get(url, headers=headers, timeout=timeout, verify=False)
        resp.raise_for_status()
        # Try UTF-8 first, then detect encoding
        try:
            return resp.text
        except:
            if resp.encoding and resp.encoding.lower() != 'utf-8':
                return resp.content.decode(resp.encoding, errors='replace')
            import chardet
            detected = chardet.detect(resp.content)
            enc = detected.get('encoding', 'utf-8') or 'utf-8'
            return resp.content.decode(enc, errors='replace')
    except Exception as e:
        print(f"  [抓取失败] {url}: {e}")
        return None


def extract_text_from_html(html):
    """从 HTML 提取纯文本"""
    if not html:
        return ""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'lxml' if 'lxml' in str(__import__('bs4')) else 'html.parser')
        # Remove script and style
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            tag.decompose()
        text = soup.get_text(separator='\n', strip=True)
        return text
    except:
        # Fallback: simple regex
        import re
        text = re.sub(r'<[^>]+>', '\n', html)
        text = re.sub(r'\n+', '\n', text)
        return text.strip()


def parse_gov_cn(text):
    """解析中国政府网内容"""
    items = []
    lines = text.split('\n')
    current_title = ""
    current_content = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if len(line) > 5 and len(line) < 100:
            if any(kw in line for kw in ['习近平', '总理', '国务院', '会议', '印发', '发布', '通知']):
                if current_title and current_content:
                    items.append({'title': current_title, 'content': ' '.join(current_content[-10:])})
                current_title = line
                current_content = []
            else:
                current_content.append(line)
        else:
            current_content.append(line)
    if current_title and current_content:
        items.append({'title': current_title, 'content': ' '.join(current_content[-10:])})
    return items


def parse_xinhua(text):
    """解析新华社内容"""
    items = []
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        if any(kw in line for kw in ['习近平', '时政', '要闻', '新华社', '重要讲话']):
            items.append({'title': line[:80], 'content': ' '.join(lines[i:i+5])})
    return items


def parse_text_generic(text):
    """通用文本解析"""
    items = []
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    for i, line in enumerate(lines):
        if len(line) > 8 and len(line) < 80:
            if any(kw in line for kw in CRITICAL_KEYWORDS + HIGH_KEYWORDS):
                content_lines = lines[i:min(i+5, len(lines))]
                items.append({'title': line, 'content': ' '.join(content_lines)})
    return items


def extract_key_sentences(content):
    """从内容中提取含关键词的关键句"""
    sentences = re.split(r'[。！？\n]', content)
    key_sentences = []
    for s in sentences:
        s = s.strip()
        if len(s) < 10:
            continue
        for kw in CRITICAL_KEYWORDS + HIGH_KEYWORDS:
            if kw in s:
                key_sentences.append(s)
                break
    return key_sentences


def parse_to_knowledge(items, source_name):
    """将抓取条目转换为知识点格式"""
    kps = []
    seen_titles = set()
    for item in items:
        title = item.get('title', '').strip()
        content = item.get('content', '').strip()
        if not title or not content or len(content) < 20:
            continue
        # Dedup
        title_key = title[:20]
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)

        # Determine importance
        importance = 'medium'
        for kw in CRITICAL_KEYWORDS:
            if kw in title + content:
                importance = 'critical'
                break
        if importance != 'critical':
            for kw in HIGH_KEYWORDS:
                if kw in title + content:
                    importance = 'high'
                    break

        # Generate highlights
        highlights = []
        sentences = extract_key_sentences(content)
        for sent in sentences:
            for kw in CRITICAL_KEYWORDS + HIGH_KEYWORDS:
                if kw in sent:
                    idx = content.find(sent)
                    if idx >= 0:
                        highlights.append({
                            'start': idx,
                            'end': idx + len(sent),
                            'text': sent[:50],
                        })
                    break

        kps.append({
            'title': title[:60],
            'content': content[:500],
            'highlights': highlights[:5],
            'importance': importance,
            'tags': [t for t in CRITICAL_KEYWORDS + HIGH_KEYWORDS if t in title + content][:3],
            'source': source_name,
            'examFrequency': 'high' if importance in ('critical', 'high') else 'medium',
        })
    return kps


def generate_questions_from_kps(kps):
    """从知识点自动生成题目"""
    import random
    questions = []
    for kp in kps:
        title = kp.get('title', '')
        content = kp.get('content', '')
        importance = kp.get('importance', 'medium')
        if not content or len(content) < 30:
            continue

        # Generate 1-2 questions per KP
        sentences = [s.strip() for s in re.split(r'[。！？]', content) if len(s.strip()) > 15]
        if not sentences:
            continue

        # Take first substantive sentence
        main_sent = sentences[0]

        # Determine question type: mostly single choice
        q_type = random.choices(['single', 'judge', 'single', 'multiple'],
                                weights=[0.5, 0.2, 0.2, 0.1])[0]

        if q_type == 'judge':
            # True/False: modify a statement
            is_true = random.choice([True, False])
            if is_true:
                question = f'关于"{title}"，以下说法是否正确？"{main_sent[:60]}"'
                correct = [0]
            else:
                # Create a wrong variant
                wrong_content = main_sent[:]
                # Swap a keyword
                for kw in ['必须', '应该', '首要', '核心', '本质']:
                    if kw in wrong_content:
                        wrong_content = wrong_content.replace(kw, '不必', 1)
                        break
                question = f'关于"{title}"，以下说法是否正确？"{wrong_content[:60]}"'
                correct = [1]
            questions.append({
                'type': 'judge',
                'difficulty': 2,
                'question': question,
                'options': ['A. 正确', 'B. 错误'],
                'correct': correct,
                'explanation': f'考查"{title}"知识点。正确答案应为：{main_sent[:100]}',
                'highlights': [title],
            })
        else:
            # Single choice: fill in the blank
            blank_kws = ['本质', '核心', '首要', '根本', '关键', '基础', '中心']
            blank_kw = None
            for kw in blank_kws:
                if kw in main_sent:
                    blank_kw = kw
                    break

            if blank_kw:
                # Find the phrase with the keyword
                idx = main_sent.find(blank_kw)
                start = max(0, idx - 10)
                end = min(len(main_sent), idx + 20)
                phrase = main_sent[start:end]
                question = f'根据{title}，"{phrase}"中的"{blank_kw}"指的是什么？'
                correct_answer = main_sent[idx:idx+30]

                options = [f'A. {correct_answer}']
                distractors = [
                    f'B. {main_sent[:20]}制度',
                    f'C. {main_sent[10:30]}体系',
                    f'D. 全面推进依法治国',
                ]
                random.shuffle(distractors)
                options.extend(distractors)
                random.shuffle(options)
                correct_idx = options.index(f'A. {correct_answer}')

                questions.append({
                    'type': 'single',
                    'difficulty': 2,
                    'question': question,
                    'options': options,
                    'correct': [correct_idx],
                    'explanation': f'根据"{title}"，正确答案是"{correct_answer}"。{main_sent[:100]}',
                    'highlights': [title, blank_kw],
                })
            else:
                # Simple factual question
                keywords = [kw for kw in CRITICAL_KEYWORDS if kw in main_sent]
                if keywords:
                    kw = keywords[0]
                    idx = main_sent.find(kw)
                    question = f'在"{title}"中，关于"{kw}"的表述正确的是？'
                    correct_answer = main_sent[max(0,idx-5):idx+40]
                    questions.append({
                        'type': 'single',
                        'difficulty': 2,
                        'question': question,
                        'options': [
                            f'A. {correct_answer}',
                            f'B. 需要进一步深化改革',
                            f'C. 坚持以经济建设为中心',
                            f'D. 全面加强党的领导',
                        ],
                        'correct': [0],
                        'explanation': f'{main_sent[:120]}',
                        'highlights': [kw],
                    })

    return questions


def fetch_all():
    """主抓取流程"""
    all_items = []
    success_sources = []

    for source in SOURCES:
        print(f"正在抓取: {source['name']} ({source['url']})")
        html = fetch_url(source['url'])
        if html:
            text = extract_text_from_html(html)
            if source['parser'] == 'gov_cn':
                items = parse_gov_cn(text)
            elif source['parser'] == 'xinhua':
                items = parse_xinhua(text)
            else:
                items = parse_text_generic(text)
            if items:
                all_items.extend(items)
                success_sources.append(source['name'])
                print(f"  ✓ 成功: {len(items)} 条")
                # If we already have good data from high-priority sources, stop
                if len(success_sources) >= 2:
                    break
        else:
            print(f"  ✗ 失败")

    # Parse items into knowledge points
    kps = []
    for item in all_items:
        parsed = parse_to_knowledge([item], '综合时政')
        kps.extend(parsed)

    # Generate questions
    questions = generate_questions_from_kps(kps)

    result = {
        'success': len(kps) > 0,
        'sources': success_sources,
        'knowledgePoints': kps[:8],  # Limit to top 8 per day
        'questions': questions[:15],  # Limit to top 15 per day
        'timestamp': datetime.now().isoformat(),
    }

    # If no content was fetched, use buffer pool
    if len(kps) == 0:
        print("所有来源抓取失败，使用缓存池")
        import random
        selected = random.sample(BUFFER_POOL, min(3, len(BUFFER_POOL)))
        for item in selected:
            kps.append({
                'title': item['title'],
                'content': item['content'],
                'highlights': [],
                'importance': 'critical',
                'tags': item['tags'],
                'source': '缓存池',
                'examFrequency': 'high',
            })
        questions = generate_questions_from_kps(kps)
        result = {
            'success': True,
            'sources': ['缓存池（备用）'],
            'knowledgePoints': kps,
            'questions': questions[:10],
            'timestamp': datetime.now().isoformat(),
            'fromBuffer': True,
        }

    # Write output
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n抓取完成: {len(result['knowledgePoints'])} 知识点, {len(result['questions'])} 题目")
    print(f"来源: {', '.join(result['sources'])}")

    return result


if __name__ == '__main__':
    # Allow insecure SSL for government sites (some use older certs)
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    fetch_all()
