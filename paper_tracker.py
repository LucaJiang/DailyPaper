import os
import requests
from openai import OpenAI

# --- 配置区 (这些将配置在 GitHub Secrets 中) ---
S2_API_KEY = os.getenv("S2_API_KEY")
LLM_API_KEY = os.getenv("LLM_API_KEY")
SERVERCHAN_KEY = os.getenv("SERVERCHAN_KEY")

HISTORY_FILE = "config/seen_papers.txt"
BLACKLIST_FILE = "config/blacklisted_venues.txt"
MAX_PAPERS_AQUIRED_FROM_S2 = 100


def read_list(file_path):
    """读取文件列表，忽略空行"""
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def read_seed_papers(file_path):
    """从本地读取 CSV 格式的文献 ID 列表"""
    papers = []
    if not os.path.exists(file_path):
        print(f"Warning: 找不到文件 {file_path}")
        return papers

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            # 移除换行符和首尾空格
            line = line.strip()
            # 忽略空行
            if line:
                papers.append(line)
    return papers


def get_paper_recommendations():
    """通过 Semantic Scholar 寻找相关新论文"""
    url = "https://api.semanticscholar.org/recommendations/v1/papers"
    headers = {"x-api-key": S2_API_KEY}

    positive_papers = read_seed_papers("config/seed_paper_positive.csv")
    negative_papers = read_seed_papers("config/seed_paper_negative.csv")

    print(f"载入正向论文: {len(positive_papers)} 篇")
    print(f"载入负向论文: {len(negative_papers)} 篇")

    if not positive_papers:
        print("错误：推荐系统至少需要一篇 Positive 论文作为基准。")
        return []

    payload = {"positivePaperIds": positive_papers, "negativePaperIds": negative_papers}

    # 步骤 1：获取推荐（注意：这里去掉了 tldr，防止 400 报错）
    params = {
        "fields": "paperId,title,abstract,authors,url,venue,externalIds,publicationDate,year",
        "limit": MAX_PAPERS_AQUIRED_FROM_S2,
    }

    response = requests.post(url, json=payload, headers=headers, params=params)

    if response.status_code != 200:
        print(f"API 请求失败: {response.status_code} - {response.text}")
        return []

    raw_papers = response.json().get("recommendedPapers", [])
    seen_papers = set(read_list(HISTORY_FILE))
    blacklisted_venues = [v.lower() for v in read_list(BLACKLIST_FILE)]

    print(f"从推荐系统获取到 {len(raw_papers)} 篇论文，正在筛选最新论文...")

    # 过滤掉已经推送过的论文
    unseen_papers = []
    for p in raw_papers:
        if p.get("paperId") in seen_papers:
            continue

        venue = (p.get("venue") or "").lower()
        if blacklisted_venues and any(bv in venue for bv in blacklisted_venues):
            continue

        abstract_text = (p.get("abstract") or "").strip()
        # 由于第一步没有获取 tldr，这里只判断摘要是否存在
        if not abstract_text:
            continue

        paper = dict(p)
        unseen_papers.append(paper)

    # 按发表日期倒序排列（最新的在前面）
    def get_date(p):
        pub_date = p.get("publicationDate")
        if pub_date:
            return pub_date
        year = p.get("year")
        if year:
            return f"{year}-12-31"
        return "1900-01-01"

    unseen_papers.sort(key=get_date, reverse=True)

    # print(f"筛选后剩余 {len(unseen_papers)} 篇未读论文，正在获取 TLDR...")

    # 只取前 10 篇最新的
    top_new_papers = unseen_papers[:10]

    # 步骤 2：调用 Batch API 批量查这 10 篇的 TLDR
    if top_new_papers:
        paper_ids = [p["paperId"] for p in top_new_papers]
        batch_url = "https://api.semanticscholar.org/graph/v1/paper/batch"
        batch_params = {"fields": "paperId,tldr"}

        batch_res = requests.post(
            batch_url, json={"ids": paper_ids}, headers=headers, params=batch_params
        )

        if batch_res.status_code == 200:
            tldr_data = batch_res.json()
            # 建立一个 { 'paperId': 'TLDR 文本' } 的映射字典
            tldr_dict = {}
            for item in tldr_data:
                if item and item.get("tldr") and isinstance(item.get("tldr"), dict):
                    tldr_dict[item["paperId"]] = (
                        item["tldr"].get("text") or ""
                    ).strip()

            # 将提取到的 tldr 文本塞回论文数据里
            for p in top_new_papers:
                p["tldrText"] = tldr_dict.get(p["paperId"], "")
        else:
            print(f"警告: TLDR 批量请求失败: {batch_res.text}")
            for p in top_new_papers:
                p["tldrText"] = ""

    return top_new_papers


def summarize_papers_with_llm(papers):
    """调用大模型进行总结"""
    client = OpenAI(
        api_key=LLM_API_KEY, base_url="https://api.deepseek.com"
    )  # deepseek
    # client = OpenAI(
    #     api_key=LLM_API_KEY, base_url="https://api.siliconflow.cn/v1"
    # )  # siliconflow

    report_content = ""
    for idx, paper in enumerate(papers):
        title = paper.get("title", "无标题")
        date = paper.get("publicationDate") or paper.get("year") or "未知日期"
        abstract_text = (paper.get("abstract") or "").strip()
        tldr_text = (paper.get("tldrText") or "").strip()

        # 优先使用 DOI 生成永久链接
        doi = ""
        external_ids = paper.get("externalIds")
        if isinstance(external_ids, dict):
            doi = (external_ids.get("DOI") or "").strip()
        url = f"https://doi.org/{doi}" if doi else paper.get("url", "")
        if url == "":
            url = f"https://www.semanticscholar.org/paper/{paper.get('paperId')}"

        venue_name = (paper.get("venue") or "").strip() or "未知会议/期刊"

        if not abstract_text and tldr_text:
            abstract_text = f"（原始摘要缺失，以下为TLDR）{tldr_text}"
        if not abstract_text:
            abstract_text = "无摘要"

        authors_list = paper.get("authors", [])
        if len(authors_list) > 4:
            author_names = [
                authors_list[0].get("name", "未知"),
                authors_list[1].get("name", "未知"),
                "...",
                authors_list[-2].get("name", "未知"),
                authors_list[-1].get("name", "未知"),
            ]
            authors = ", ".join(author_names)
        else:
            authors = ", ".join([author.get("name", "未知") for author in authors_list])

        prompt = f"""
你是一个严谨的学术专家。请基于以下论文信息，提取核心内容并转化为中文。
要求：
1. 极其精简、具体，拒绝空泛的套话，保留专业术语。
2. 绝对不要输出任何诸如“好的，这是为您总结的论文”之类的客套话。
3. 请严格按照以下 Markdown 格式输出:
**[试图解决的问题]**：(用一句话概括该研究针对的痛点或背景)
**[核心方法]**：(具体使用了什么架构、算法、模型或机制)
**[创新与效果]**：(实现了什么指标提升，或解决了什么具体的限制)

标题: {title}
TLDR: {tldr_text or "无"}
摘要原文: {abstract_text}
"""

        response = client.chat.completions.create(
            model="deepseek-chat",
            # model="deepseek-ai/DeepSeek-V3.2",
            messages=[{"role": "user", "content": prompt}],
        )

        summary = response.choices[0].message.content
        report_content += (
            f"## {idx+1}\n[{title}]({url})\n*{venue_name}* | {authors} | {date}\n\n"
            f"**TLDR:** {tldr_text}\n\n"
            f"> {abstract_text}\n\n"
            f"{summary}\n\n---\n"
        )

    return report_content


def update_history(papers):
    """将已推送的论文 ID 追加到历史记录文件"""
    if not papers:
        return

    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)

    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        for p in papers:
            f.write(p.get("paperId") + "\n")


def push_to_wechat(content):
    """通过 Server 酱 推送到微信"""
    url = f"https://sctapi.ftqq.com/{SERVERCHAN_KEY}.send"
    data = {"title": "📚 你的每日文献追踪晨报到了！", "desp": content}
    requests.post(url, data=data)


if __name__ == "__main__":
    print("正在寻找最新推荐...")
    new_papers = get_paper_recommendations()
    if new_papers:
        print(f"找到 {len(new_papers)} 篇最新论文，正在使用 LLM 总结...")
        report = summarize_papers_with_llm(new_papers)
        print("正在推送到微信...")
        push_to_wechat(report)
        print("更新历史记录...")
        update_history(new_papers)
        print("全部完成！")
    else:
        print("今天没有发现未读的最新相关文献。")
