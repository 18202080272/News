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
        ("热门话题", "🔥", _fetch_zhihu_hot),
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
            print(f"  {name} 抓取失败: {e}")

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
    print(f"AI/知识已保存: {output}，共 {total} 条")
    return data


def _headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }


def _fetch_36kr_ai():
    url = "https://36kr.com/information/AI/"
    resp = requests.get(url, headers=_headers(), timeout=10)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    items = []
    seen = set()

    for a_tag in soup.find_all("a"):
        title = (a_tag.get("title", "") or a_tag.get_text("")).strip()
        href = a_tag.get("href", "")
        if not title or len(title) < 8 or len(title) > 100:
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

        summary = a_tag.find_next("p")
        summary_text = (summary.get_text().strip() if summary else "")[:120]
        if not summary_text:
            summary_text = f"{title}，关注 AI 领域最新动态。"

        items.append({
            "title": title[:60],
            "summary": summary_text + ("..." if len(summary_text) >= 120 else ""),
            "url": href,
        })

    return items[:10]


def _fetch_jiqizhixin():
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
            "summary": f"{title}，机器之心为您提供深度解读。",
            "url": href,
        })

    return items[:10]


def _fetch_zhihu_hot():
    url = "https://tophub.today/n/mproPpoq6O"
    try:
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
                full_text = text_td.get_text().strip()
                title = a_tag.get_text().strip()
                href = a_tag.get("href", "")
                if not title or len(title) < 8:
                    continue
                if title in seen:
                    continue
                seen.add(title)

                if href and not href.startswith("http"):
                    href = f"https://tophub.today{href}"

                items.append({
                    "title": title[:60],
                    "summary": f"「{title}」引发广泛讨论。",
                    "url": href,
                })

        if items:
            return items[:10]
    except Exception as e:
        print(f"    tophub 失败: {e}")

    return []


def _fetch_knowledge_paid():
    items = []

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
                        "summary": f"得到平台精选内容：{title}，助力知识升级。",
                    })
    except Exception:
        pass

    if not items:
        items = [
            {"title": "得到年度精选课程", "summary": "薛兆丰、万维钢等知名学者精品课，构建系统性知识框架。"},
            {"title": "混沌学园创新思维", "summary": "李善友教授主讲，案例拆解帮助企业找到第二增长曲线。"},
            {"title": "知乎盐选专栏", "summary": "多位行业专家分享职场进阶、投资理财等实用知识。"},
            {"title": "樊登读书每周精读", "summary": "40 分钟听书掌握核心要点，累计解读超 500 本好书。"},
        ]
    return items[:6]


def _fetch_health():
    items = []

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
                        "summary": f"丁香医生健康专栏：{title}。",
                    })
    except Exception:
        pass

    if not items:
        items = [
            {"title": "中医养生：四季调理指南", "summary": "传统中医分享四季养生要点，药膳食补增强体质。"},
            {"title": "改善睡眠的实用方法", "summary": "睡前远离屏幕、规律作息、适当运动，有效提升睡眠质量。"},
            {"title": "地中海饮食的益处", "summary": "橄榄油、鱼类、蔬果为主，降低心血管疾病风险。"},
            {"title": "每天走路 8000 步", "summary": "研究表明每天适量步行可显著降低死亡率。"},
        ]
    return items[:6]


if __name__ == "__main__":
    fetch_ai_news()
