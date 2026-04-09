# 自动学术论文追踪器

这是一个基于 `GitHub Actions` 的全自动化科研追踪工具。它利用 Semantic Scholar 的推荐 API，根据你设定的“种子论文”自动找到最新相关的研究工作，并利用大语言模型（如 DeepSeek）生成中文深度总结，最后每天准时将内容推送到你的微信上。

广告：使用我的硅基流动链接注册并实名认证可以获得16元人民币的任意AI模型 （包括DeepSeek） 试用额度！[[点击注册](https://cloud.siliconflow.cn/i/5eXyqjuv)](https://cloud.siliconflow.cn/i/5eXyqjuv) 。也可以在vscode、cursor、notion等工具中使用。

---

## 更新日志

- **2026-03-31**：完成核心功能开发和测试，公开仓库。
- **2026-04-01**：增加出版商黑名单功能。

## 🌟 功能特性

- **高度贴合**：通过配置“正向(Positive)”和“负向(Negative)”种子论文，让推荐算法越来越懂你的研究偏好。
- **过滤不感兴趣的出版商**：内置出版商黑名单功能，自动屏蔽来自特定会议或期刊（`config/publisher_blacklist.txt`）的论文，专注于你真正关心的研究。
- **AI 智能读库**：对晦涩的英文摘要进行精读总结，自动提取3大核心要点（创新、方法、解决的问题），用通俗易懂的中文呈现。
- **仅推最新**：每次从海量推荐中智能筛选出 top 10 最新论文，按发表日期倒序排列。
- **防止重复**：自动维护推送历史记录（`config/seen_papers.txt`），杜绝重复推送同一篇论文，不浪费你的微信通知。
- **两步抓取 TLDR**：首轮筛选最新且含摘要的推荐论文，随后利用 Batch API 精准回补 TLDR（一句话极简总结），丰富 AI 的分析上下文。
- **免服务器部署**：完全依托于 GitHub Actions 运行，零开销、零维护。
- **微信准时送达**：结合 Server 酱，把你每天需要在各个平台刷论文的时间省下来，早晨直接在微信查收日报。

---

## 🚀 快速开始教程

如果你想在自己的 GitHub 账号下运行这套系统，请按照以下步骤操作：

### 1. Fork 本仓库

点击页面右上角的 `Fork` 按钮，将当前代码仓库复制一份到你自己的账号下。

### 2. 获取必要的 API Keys (密钥)

你需要提前准备好以下三个服务的 API 密钥：

1. **Semantic Scholar API Key (S2_API_KEY)**
   - 官方虽然有无 Key 调用的额度，但为了保证推荐 API 稳定运行，建议去 [Semantic Scholar API](https://www.semanticscholar.org/product/api) 拉到最下面的表格，申请专属 Key。用教育邮箱申请后，大概10分钟就能拿到。
2. **LLM API Key (LLM_API_KEY)**
   - 代码默认接入的是性价比极高的 **DeepSeek**。你可以去 [DeepSeek 开放平台](https://platform.deepseek.com/) 注册并生成一个 API 密钥。*(如果你想使用其他平台，只需在 `paper_tracker.py` 中更改 `base_url` 并换成对应服务的 Key 即可)*。实测一次推送大概要0.02元人民币，如果不需要AI自动总结，可以关闭这个功能。
3. **Server酱 SendKey (SERVERCHAN_KEY)**
   - 用于微信推送。访问 [Server酱官网](https://sct.ftqq.com/login) 用你的微信扫码登录，获取你的 `SendKey`，并配置好微信推送通道。

### 3. 配置 GitHub Secrets

为了保护你的密钥不被泄露，请将上面的 Key 填入 GitHub 仓库的加密设置中：

1. 进入你 Fork 后的仓库，点击顶部的 `Settings` (设置)。
2. 在左侧边栏找到 `Secrets and variables` -> 点击 `Actions`。
3. 点击绿色的 `New repository secret` 按钮，依次添加以下 3 个环境变量：
   - 变量名：`S2_API_KEY` （填入 Semantic Scholar 密钥）
   - 变量名：`LLM_API_KEY` （填入 DeepSeek 密钥）
   - 变量名：`SERVERCHAN_KEY` （填入 Server酱 SendKey）

### 4. 设置你的“种子论文”

修改工作区 `config/` 目录下的两个 CSV 文件以调教推荐算法：

- **`config/seed_paper_positive.csv`** (必须)：放入你觉得**很有价值、希望推荐类似研究**的论文 ID（每行一个）。
- **`config/seed_paper_negative.csv`** (可选)：放入你觉得**不相关、不希望系统推荐**的论文 ID（每行一个）。

> **💡 提示**：系统会自动创建和维护 `config/seen_papers.txt` 文件来记录已推送过的论文，防止重复推送。你无需手动操作。

### 5. 设置出版商黑名单（可选）

修改 `config/publisher_blacklist.txt` 文件，添加你不想接收论文的出版商名称（每行一个）。请使用论文推荐 API 返回的 `venue` 字段中的名称（大小写不敏感），例如：

```
arXiv
bioRxiv
```

#### 支持的论文 ID 格式

以下是系统支持的论文 ID 格式，你可以从 Semantic Scholar、arXiv、DOI 等平台获取这些 ID：

- `DOI:<doi>` - a Digital Object Identifier, e.g. `DOI:10.18653/v1/N18-3011`
- `ARXIV:<id>` - arXiv.org, e.g. `ARXIV:2106.15928`
- `<sha>` - a Semantic Scholar ID, e.g. `649def34f8be52c8b66281af98ae884c09aef38b`
- `CorpusId:<id>` - a Semantic Scholar numerical ID, e.g. `CorpusId:215416146`
- `MAG:<id>` - Microsoft Academic Graph, e.g. `MAG:112218234`
- `ACL:<id>` - Association for Computational Linguistics, e.g. `ACL:W12-3903`
- `PMID:<id>` - PubMed/Medline, e.g. `PMID:19872477`
- `PMCID:<id>` - PubMed Central, e.g. `PMCID:2323736`
- `URL:<url>` - URL from one of the sites listed below, e.g. `URL:https://arxiv.org/abs/2106.15928v1`
  - semanticscholar.org
  - arxiv.org
  - aclweb.org
  - acm.org
  - biorxiv.org

### 5. 启动与测试运行

完成以上步骤后，你可以手动触发一次来测试是否配置成功：
1. 点击仓库顶部的 `Actions` 选项卡。
2. (可能需要) 点击绿色的 `I understand my workflows, go ahead and enable them` 启用 Actions 工作流。
3. 在左侧列表中选中 `Daily Paper Tracker`。
4. 点击右侧的 `Run workflow` -> `Run workflow`。
5. 等待 1~2 分钟，如果全部打勾为绿色，你的微信就会收到第一封文献晨报！

*(此外，系统每天北京时间早上 9:00 会自动运行一次，同时允许手动触发)*。

---

## 工作原理

### 防止重复推送

脚本每次运行前会读取 `config/seen_papers.txt` 中的论文ID(Semantic Scholar ID)历史记录，并自动过滤掉已推送过的论文。发送完毕后，新推送的论文ID会被追加到该文件中，GitHub Actions 机器人会自动将此变更提交并推送到你的仓库，保证下次运行时不会重复推送同一篇论文。

### 日期排序与最新优选

系统会向 Semantic Scholar API 一次性请求50篇推荐，然后按 `publicationDate`（发表日期）倒序排列，只推送前10篇最新的未推送论文。日期缺失时会自动使用 `year` 兜底。

### 链接与摘要策略

系统会分两步走响应中提取 `externalIds.DOI`、`venue` 和 `tldr.text`：

- 第一步：使用推荐 API 初选包含 `abstract` 的候选论文。
- 第二步：通过 Batch API 回补这批论文的 `tldr` 文本（一句话概括）。
- 链接优先使用 `https://doi.org/<DOI>`，无 DOI 时回退到 API 返回的 `url`。
- 展示字段优先使用 `venue`，避免 publicationVenue 缺失导致“未知出版社”。

---

## 进阶定制

这个仓库基本通过 vibe coding 实现。欢迎根据自己的需求进行修改和优化：

- **更改运行时间**：编辑 `.github/workflows/daily_tracker.yml` 文件中的 `cron: '0 1 * * *'` (注意这是 UTC 时间)。
- **更改 AI 提示词**：直接修改 `paper_tracker.py` 中的 `prompt` 字段，以生成符合你排版和侧重点的报告。 
- **替换其他的大模型**：如果你想用诸如 Kimi、通义千问等，只要它们兼容 OpenAI SDK 格式，直接在 `paper_tracker.py` 修改 `base_url` 即可。

## License

MIT License
