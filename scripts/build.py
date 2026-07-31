import html
import json
import os
from datetime import datetime
from datetime import timezone, timedelta


# 北京时间 UTC+8
BJT = timezone(timedelta(hours=8))


HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>每日要点 - {date}</title>
    <meta name="description" content="每日新闻联播和 AI/知识付费要点 {date}">
    <meta name="theme-color" content="#C62828">
    <link rel="manifest" href="manifest.json">
    <link rel="apple-touch-icon" href="icon-192.png">
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>📺 每日要点</h1>
            <p class="date">{date} {weekday}</p>
            <p class="update-time">更新时间：{update_time}</p>
        </header>

        <div class="tab-bar">
            <button class="tab-btn active" data-tab="news">📺 新闻联播 <span class="badge">{news_count}</span></button>
            <button class="tab-btn" data-tab="ai">🤖 AI/知识 <span class="badge">{ai_count}</span></button>
        </div>

        <main class="main">
            <div id="tab-news" class="tab-content active">
                {news_html}
            </div>
            <div id="tab-ai" class="tab-content">
                {ai_html}
            </div>
        </main>

        <footer class="footer">
            <p>数据来源：CCTV新闻联播、36氪、知乎等</p>
            <p>每天 20:30 自动更新</p>
        </footer>
    </div>

    <script>
    document.querySelectorAll('.tab-btn').forEach(btn => {{
        btn.addEventListener('click', () => {{
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
        }});
    }});
    </script>
</body>
</html>'''

CATEGORY_TEMPLATE = '''<section class="category">
    <h2 class="category-title">
        <span class="icon">{icon}</span>
        {name}
        <span class="count">({count})</span>
    </h2>
    <div class="cards">{cards_html}</div>
</section>'''

CARD_TEMPLATE = '''<article class="card">
    <h3 class="card-title">{title}</h3>
    <p class="card-summary">{summary}</p>
    {url_link}
</article>'''


def build_categories_html(categories):
    parts = []
    for cat in categories:
        cards = []
        for item in cat.get("items", []):
            url = item.get("url", "")
            url_link = f'<a class="card-link" href="{html.escape(url)}" target="_blank">查看详情</a>' if url else ""
            card = CARD_TEMPLATE.format(
                title=html.escape(item.get("title", "")),
                summary=html.escape(item.get("summary", "")),
                url_link=url_link,
            )
            cards.append(card)
        cat_html = CATEGORY_TEMPLATE.format(
            icon=cat.get("icon", "📌"),
            name=html.escape(cat.get("name", "")),
            count=len(cat.get("items", [])),
            cards_html="\n".join(cards),
        )
        parts.append(cat_html)
    return "\n".join(parts)


def build_html():
    news_path = "data/xinwenlianbo.json"
    ai_path = "data/ai_news.json"
    output_path = "index.html"

    news_data = {"date": "", "weekday": "", "categories": []}
    if os.path.exists(news_path):
        with open(news_path, "r", encoding="utf-8") as f:
            news_data = json.load(f)

    ai_data = {"date": "", "weekday": "", "categories": []}
    if os.path.exists(ai_path):
        with open(ai_path, "r", encoding="utf-8") as f:
            ai_data = json.load(f)

    date = news_data.get("date") or ai_data.get("date") or datetime.now(BJT).strftime("%Y-%m-%d")
    weekday = news_data.get("weekday") or ai_data.get("weekday") or ""
    update_time = datetime.now(BJT).strftime("%Y-%m-%d %H:%M")

    news_html = build_categories_html(news_data.get("categories", []))
    ai_html = build_categories_html(ai_data.get("categories", []))

    news_count = sum(len(c.get("items", [])) for c in news_data.get("categories", []))
    ai_count = sum(len(c.get("items", [])) for c in ai_data.get("categories", []))

    page = HTML_TEMPLATE.format(
        date=date,
        weekday=weekday,
        update_time=update_time,
        news_count=news_count,
        ai_count=ai_count,
        news_html=news_html,
        ai_html=ai_html,
    )

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(page)

    print(f"HTML 已生成: {output_path}")
    print(f"  新闻联播: {news_count} 条")
    print(f"  AI/知识: {ai_count} 条")


if __name__ == "__main__":
    build_html()
