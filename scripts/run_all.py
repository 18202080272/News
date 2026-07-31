import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    date_str = None
    if len(sys.argv) > 1:
        date_str = sys.argv[1]

    print("=" * 50)
    print("每日要点 - 数据更新")
    print("=" * 50)

    print("\n[1/3] 抓取新闻联播...")
    try:
        from fetch_xinwenlianbo import run as run_xwlb
        run_xwlb(date_str)
    except Exception as e:
        print(f"  新闻联播抓取失败: {e}")

    print("\n[2/3] 抓取 AI/知识...")
    try:
        from fetch_ai_news import fetch_ai_news
        fetch_ai_news()
    except Exception as e:
        print(f"  AI/知识抓取失败: {e}")

    print("\n[3/3] 生成 HTML...")
    try:
        from build import build_html
        build_html()
    except Exception as e:
        print(f"  HTML 生成失败: {e}")

    print("\n" + "=" * 50)
    print("完成！请在 dist/ 目录查看网页")
    print("本地预览: cd dist && python -m http.server 8000")
    print("=" * 50)


if __name__ == "__main__":
    main()
