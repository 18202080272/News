import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import os
import re


def fetch_ai_news():
    today = datetime.now().strftime("%Y-%m-%d")
    weekday_map = {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}
    weekday = weekday_map[datetime.now().weekday()]

    categories = []

    sources = [
        ("AI 前沿", "🤖", _fetch_36kr_ai),
        ("科技动态", "💡", _fetch_jiqizhixin),
        ("热门话题", "🔥", _fetch_weibo_hot),
        ("知识付费", "📚", _fetch_knowledge_paid),
        ("健康生活", "🌿", _fetch_health),
    ]

    for name, icon, fetcher in sources:
        try:
            items = fetcher()
            if items:
                categories.append({"name": name, "icon": icon, "items": items[:8]})
                print(f"  {name}: {len(items)} 条")
        except Exception as e:
            print(f"  {name} 抓取失败：{e}")

    data = {
        "date": today,
        "weekday": weekday,
        "categories": categories,
    }

    output = "data/ai_news.json"
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    total = sum(len(c["items"]) for c in categories)
    print(f"AI/知识已保存：{output}，共 {total} 条")
    return data


def _headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }


def _extract_key_info(title, text=""):
    """从标题和文本中提取关键信息"""
    info_parts = []

    # 数据
    data_matches = re.findall(r"\d+[%.万亿元亿]", text or title)
    if data_matches:
        info_parts.append("数据：" + data_matches[0])

    # 人名
    person_matches = re.findall(r"[一 - 龥]{2,4}(?:教授 | 博士 | 专家 | 负责人 | 称 | 表示)", text or title)
    if person_matches:
        info_parts.append("人物：" + person_matches[0].rstrip("称表示"))

    return info_parts


def _fetch_36kr_ai():
    """从 36  AI 频道抓取"""
    url = "https://36kr.com/information/AI/"
    resp = requests.get(url, headers=_headers(), timeout=10)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    items = []
    seen = set()

    # 查找文章卡片
    for article_div in soup.find_all("div", class_=lambda x: x and any(k in x.lower() for k in ["article", "item", "post"])):
        a_tag = article_div.find("a")
        if not a_tag:
            continue

        title = (a_tag.get("title", "") or a_tag.get_text("")).strip()
        href = a_tag.get("href", "")
        if not title or len(title) < 8:
            continue
        if title in seen:
            continue
        if not href or href == "#":
            continue
        if "/p/" not in href and "/newsflashes/" not in href:
            continue

        seen.add(title)
        if not href.startswith("http"):
            href = "https://36kr.com" + href

        # 获取摘要（从文章卡片中提取）
        summary_text = ""
        p_tags = article_div.find_all("p")
        for p in p_tags:
            text = p.get_text().strip()
            if text and text != title and len(text) > 10:
                summary_text = text[:150]
                break

        if not summary_text:
            # 尝试从标题中提取（去掉来源和时间）
            full_text = article_div.get_text().strip()
            if full_text != title:
                summary_text = full_text[len(title):][:150].strip()

        if not summary_text:
            summary_text = title + "。"

        items.append({
            "title": title[:60],
            "summary": summary_text + ("..." if len(summary_text) >= 150 else ""),
            "url": href,
        })

    return items[:10]


def _fetch_jiqizhixin():
    """从机器之心抓取"""
    url = "https://www.jiqizhixin.com/"
    resp = requests.get(url, headers=_headers(), timeout=10)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    items = []
    seen = set()

    for h in soup.find_all(["h2", "h3"]):
        a_tag = h.find("a")
        if not a_tag:
            continue
        title = (a_tag.get("title", "") or a_tag.get_text("")).strip()
        href = a_tag.get("href", "")
        if not title or len(title) < 8:
            continue
        if title in seen:
            continue
        seen.add(title)

        if href and not href.startswith("http"):
            href = "https://www.jiqizhixin.com" + href

        items.append({
            "title": title[:60],
            "summary": f"机器之心：{title}。",
            "url": href,
        })

    return items[:10]


def _fetch_weibo_hot():
    """从微博热搜抓取"""
    url = "https://weibo.com/ajax/side/hotSearch"
    headers = _headers()
    headers["Referer"] = "https://weibo.com/hot/search"

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        items = []
        for entry in data.get("data", {}).get("realtime", [])[:15]:
            word = entry.get("word", "").strip()
            label = entry.get("label_name", "")
            num = entry.get("num", 0)
            summary = entry.get("note", "")

            if not word or len(word) < 4:
                continue

            hot_text = ""
            if label:
                hot_text += f"【{label}】"
            if num:
                hot_text += f"{num // 10000}万热度"
            if summary:
                hot_text += f" {summary[:80]}"

            items.append({
                "title": word[:50],
                "summary": hot_text or f"微博热搜：{word}",
                "url": f"https://s.weibo.com/weibo?q={word}",
            })

        if items:
            return items[:10]
    except Exception as e:
        print(f"    微博 API 失败：{e}")

    # 备用：从 tophub 抓取微博热搜
    try:
        url = "https://tophub.today/n/KqndgxeLl9"
        resp = requests.get(url, headers=_headers(), timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        items = []
        seen = set()
        for table in soup.find_all("table"):
            for tr in table.find_all("tr"):
                tds = tr.find_all("td")
                if len(tds) < 3:
                    continue
                text_td = tds[2]
                a_tag = text_td.find("a")
                if not a_tag:
                    continue
                title = a_tag.get_text().strip()
                if not title or len(title) < 4 or title in seen:
                    continue
                seen.add(title)
                items.append({
                    "title": title[:50],
                    "summary": f"微博热搜：{title}",
                })
        if items:
            return items[:10]
    except Exception as e:
        print(f"    备用微博源失败：{e}")

    return []


def _fetch_knowledge_paid():
    """从权威知识付费平台抓取"""
    items = []

    # 得到 APP
    try:
        url = "https://www.dedao.cn/"
        resp = requests.get(url, headers=_headers(), timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for h in soup.find_all(["h3", "h4"]):
                title = h.get_text().strip()
                if title and len(title) > 5:
                    items.append({
                        "title": title[:60],
                        "summary": f"得到平台：{title}。",
                    })
    except Exception:
        pass

    # 混沌学园
    try:
        url = "https://www.hundun.cn/"
        resp = requests.get(url, headers=_headers(), timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for h in soup.find_all(["h3", "h2"]):
                title = h.get_text().strip()
                if title and len(title) > 5:
                    items.append({
                        "title": title[:60],
                        "summary": f"混沌学园：{title}。",
                    })
    except Exception:
        pass

    if not items:
        items = [
            {"title": "得到年度精选课程", "summary": "薛兆丰、万维钢等知名学者精品课，构建系统性知识框架。"},
            {"title": "混沌学园创新思维", "summary": "李善友教授主讲，案例拆解帮助企业找到第二增长曲线。"},
        ]
    return items[:6]


def _fetch_health():
    """从权威健康平台抓取"""
    items = []

    # 丁香医生
    try:
        url = "https://dxy.com/"
        resp = requests.get(url, headers=_headers(), timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for h in soup.find_all(["h2", "h3"]):
                title = h.get_text().strip()
                if title and len(title) > 5:
                    items.append({
                        "title": title[:60],
                        "summary": f"丁香医生：{title}。",
                    })
    except Exception:
        pass

    if not items:
        items = [
            {"title": "中医养生：四季调理指南", "summary": "传统中医分享四季养生要点，药膳食补增强体质。"},
            {"title": "改善睡眠的实用方法", "summary": "睡前远离屏幕、规律作息、适当运动，有效提升睡眠质量。"},
        ]
    return items[:6]


if __name__ == "__main__":
    fetch_ai_news()
