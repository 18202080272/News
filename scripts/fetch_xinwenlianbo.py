import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import os
import time
import re


def fetch_xinwenlianbo(date_str=None):
    if date_str is None:
        date_str = datetime.now().strftime("%Y%m%d")
    elif isinstance(date_str, str) and "-" in date_str:
        date_str = date_str.replace("-", "")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }

    for attempt in range(7):
        current_date = date_str
        if attempt > 0:
            dt = datetime.strptime(date_str, "%Y%m%d") - timedelta(days=attempt)
            current_date = dt.strftime("%Y%m%d")

        url = f"https://tv.cctv.com/lm/xwlb/day/{current_date}.shtml"
        print(f"尝试抓取: {url}")
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.encoding = "utf-8"
            resp.raise_for_status()
            date_str = current_date
            break
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 404:
                print(f"  日期 {current_date} 无数据，尝试前一天...")
                continue
            raise
    else:
        raise ValueError(f"最近 7 天均未找到新闻联播数据")

    soup = BeautifulSoup(resp.text, "html.parser")

    segments = []
    seen_titles = set()
    for a_tag in soup.select("a[href]"):
        href = a_tag.get("href", "")
        title = (a_tag.get("title", "") or a_tag.get_text("")).strip()
        if not title or len(title) < 4:
            continue
        if not href.endswith(".shtml"):
            continue
        if "VIDE" not in href:
            continue
        if title in seen_titles:
            continue
        seen_titles.add(title)
        if not href.startswith("http"):
            href = "https://tv.cctv.com" + href
        segments.append({"title": title, "url": href})

    if not segments:
        raise ValueError(f"日期 {date_str} 未找到任何新闻，可能当天没有新闻联播")

    print(f"找到 {len(segments)} 条新闻，正在获取详情...")

    items = []
    for seg in segments:
        try:
            detail = _fetch_detail(seg["url"], headers)
            title = seg["title"]
            if title.startswith("[视频]"):
                title = title[4:]

            # 跳过节目本身条目
            if re.match(r"《新闻联播》\s*\d{8}\s*19:00", title):
                continue

            # 提取重点摘要
            summary = _extract_key_points(detail["full_text"], title)

            # 如果没有提取到摘要，用标题作为摘要
            if not summary:
                summary = title + "。"

            items.append({
                "title": title,
                "summary": summary,
                "url": seg["url"],
            })
        except Exception as e:
            print(f"  详情获取失败 [{seg['title']}]: {e}")
        time.sleep(0.3)

    if not items:
        raise ValueError("未能获取任何新闻内容")

    date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    return {
        "date": date_formatted,
        "title": f"新闻联播 {date_formatted}",
        "items": items,
    }


def _fetch_detail(url, headers):
    resp = requests.get(url, headers=headers, timeout=10)
    resp.encoding = "utf-8"
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    content_div = (
        soup.find("div", class_="cnt_bd")
        or soup.find("div", class_="text_area")
        or soup.find("div", class_="article_content")
        or soup.find("div", id="content")
    )

    if not content_div:
        return {"full_text": ""}

    for tag in content_div.find_all(["script", "style", "iframe"]):
        tag.decompose()

    lines = []
    for line in content_div.get_text(separator="\n").splitlines():
        line = line.strip()
        if not line:
            continue
        if line in ("主要内容", "央视网消息"):
            continue
        if line.startswith(("编辑：", "责任编辑：", "（新闻联播）：")):
            continue
        lines.append(line)

    full_text = "\n".join(lines[:30])
    return {"full_text": full_text}


def _extract_key_points(text, title):
    """提取新闻重点，结构化摘要"""
    if not text:
        return ""

    lines = text.split("\n")
    key_lines = []

    # 优先保留包含关键信息的句子
    for line in lines:
        if not line or len(line) < 10:
            continue

        # 包含关键信息的句子
        has_key_info = False
        key_patterns = [
            r"\d+%", r"\d+亿", r"\d+万", r"\d+元",  # 数据
            r"会议", r"决定", r"指出", r"强调", r"部署",  # 官方动作
            r"增长", r"下降", r"提升", r"突破", r"完成",  # 成效
            r"成功", r"发布", r"启动", r"推进", r"深化",  # 进展
        ]
        for pattern in key_patterns:
            if re.search(pattern, line):
                has_key_info = True
                break

        if has_key_info:
            key_lines.append(line)
        elif len(key_lines) < 3:
            # 也保留前几条重要句子
            if line.endswith(("。", "！", "？")):
                key_lines.append(line)

    # 组合摘要，最多 3 个要点
    if not key_lines:
        # 如果没提取到关键句，取前 2 句
        key_lines = [l for l in lines if len(l) > 15 and l.endswith(("。", "！", "？"))][:2]

    summary_parts = key_lines[:3]

    # 格式化摘要
    if len(summary_parts) == 1:
        return summary_parts[0][:120] + ("..." if len(summary_parts[0]) > 120 else "")
    else:
        # 用分号连接多个要点
        combined = "；".join(p.rstrip("。；") for p in summary_parts)
        if len(combined) > 200:
            combined = combined[:200] + "..."
        return combined


def categorize(items):
    rules = [
        ("时政要闻", "", ["习近平", "主席", "总理", "国务院", "中央", "政治局", "会见", "会晤", "党外人士"]),
        ("国际新闻", "🌍", ["美国", "俄罗斯", "欧洲", "日本", "联合国", "国际", "访问", "外交部", "外国"]),
        ("经济财经", "💰", ["GDP", "经济", "金融", "股市", "投资", "贸易", "增长", "收入", "消费"]),
        ("社会民生", "👥", ["教育", "医疗", "就业", "社保", "住房", "民生", "群众", "养老"]),
        ("科技文教", "🎓", ["科技", "文化", "艺术", "体育", "创新", "研究", "航天", "人工智能"]),
        ("国内动态", "🌐", ["省", "市", "发展", "改革", "建设", "项目", "产业"]),
    ]

    categories = {}
    for item in items:
        text = item["title"] + " " + item.get("summary", "")
        matched = False
        for name, icon, keywords in rules:
            if any(kw in text for kw in keywords):
                categories.setdefault(name, {"name": name, "icon": icon, "items": []})
                categories[name]["items"].append(item)
                matched = True
                break
        if not matched:
            categories.setdefault("其他", {"name": "其他", "icon": "📌", "items": []})
            categories["其他"]["items"].append(item)

    result = []
    for name, _, _ in rules:
        if name in categories:
            result.append(categories[name])
    if "其他" in categories:
        result.append(categories["其他"])
    return result


def run(date_str=None, output="data/xinwenlianbo.json"):
    raw = fetch_xinwenlianbo(date_str)
    categories = categorize(raw["items"])

    date_formatted = raw["date"]
    try:
        date_obj = datetime.strptime(date_formatted, "%Y-%m-%d")
        weekday_map = {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}
        weekday = weekday_map[date_obj.weekday()]
    except Exception:
        weekday = ""

    data = {
        "date": date_formatted,
        "weekday": weekday,
        "title": raw["title"],
        "categories": categories,
        "total_items": len(raw["items"]),
    }

    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"已保存：{output}，共 {len(raw['items'])} 条新闻，{len(categories)} 个分类")
    return data


if __name__ == "__main__":
    import sys
    date = sys.argv[1] if len(sys.argv) > 1 else None
    run(date)
