# Financial-Research-Agent
Financial Research Agent automates equity research by collecting market data, financial statements, filings, and news for a given company or industry. It summarizes revenue, profitability, guidance, risks, and management tone, and flags negative signals to support structured investment decisions.

金融研究智能体通过收集特定公司或行业的市场数据、财务报表、监管披露与新闻，自动化完成股票研究。它会总结收入、盈利能力、业绩指引、风险与管理层口径，并标记负面信号，以支持结构化的投资决策。

## Project Structure / 项目结构

```
Financial-Research-multiAgent/
├── app.py                  # Chainlit entry / Chainlit 入口（只读向量库）
├── .chainlit               # Chainlit config / Chainlit 配置
├── .env                    # Environment variables / 环境变量
├── requirements.txt        # Dependencies / 依赖列表
├── data/
│   ├── pdfs/               # PDF documents to index / 待索引的 PDF 文档
│   └── chroma_db/          # ChromaDB storage / 向量库持久化目录
├── src/
│   ├── models.py           # Multi-model manager / 多模型配置管理
│   ├── state.py            # LangGraph State schema / LangGraph State 结构
│   ├── graph.py            # Graph wiring & routing / LangGraph 编排与路由
│   ├── nodes/              # Agent logic nodes / Agent 逻辑节点
│   │   ├── analyzer.py     # Intent + entity parsing / 意图识别与公司名抽取
│   │   ├── fetcher.py      # Fan-out dispatcher / 分发与并行触发
│   │   ├── retriever.py    # RAG retrieval node / RAG 检索节点
│   │   └── formatter.py    # Card JSON builder / 前端卡片 JSON 组装
│   ├── rag/                # RAG module (读写分离) / RAG 模块
│   │   ├── loader.py       # PDF parsing / PDF 解析与切分
│   │   ├── vectorstore.py  # ChromaDB operations / 向量库读取
│   │   └── ingest.py       # Indexing script / 索引脚本（写操作）
│   ├── tools/              # Data tools / 数据抓取工具
│   │   ├── financial.py    # Market cap & profit / 市值/盈利
│   │   └── listing.py      # Listing info / 上市信息
│   └── prompts/            # Prompt configs / Prompt 配置
│       ├── analyzer.yaml   # Intent parsing / 意图解析
│       └── assistant.yaml  # Small talk / 日常对话
└── tests/                  # Test files / 测试文件
```

## Tech Stack / 用到的技术
- **LangGraph**: Graph orchestration, parallel fan-out/fan-in, and state passing / 负责 StateGraph 编排、并行 Fan-out/Fan-in 与状态传递
- **Chainlit**: Modern conversational UI framework / 现代化对话式界面框架
- **Multi-Model Manager**: Unified LLM configuration management / 统一管理多模型配置
  - GPT-4o: Complex financial analysis / 复杂财务分析
  - DeepSeek/GPT-4o-mini: User chat & light tasks / 用户对话与轻量任务
- **LLM**: Intent and entity extraction via prompts / 意图识别与实体抽取(通过 prompts 配置)

## Quick Start / 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置环境变量
在项目根目录创建 `.env` 文件：
```bash
# 根据使用的模型配置对应的 API Key
GPT_4O_MINI_API_KEY=your_api_key_here
# 或
DEEPSEEK_CHAT_API_KEY=your_api_key_here
```

### 3. 启动应用
```bash
# 启动 Chainlit 前端（带热重载）
python -m chainlit run app.py -w
```

应用将在浏览器中自动打开，访问地址：`http://localhost:8000`，直接输入公司名或问题即可查询

## RAG 知识库 / Knowledge Base

采用读写分离设计：`app.py` 只读取向量库，索引操作由 `ingest.py` 独立执行。

### 索引文档

1. 将 PDF 放入 `data/pdfs/` 目录
2. 运行索引命令：

**增量索引**（只处理新文件）：
```bash
python -m src.rag.ingest
```

**强制重建全部索引**：
```bash
python -m src.rag.ingest --force
```

**指定自定义目录**：
```bash
python -m src.rag.ingest --dir ./custom_pdfs
```

### 使用示例
- **查询财务数据**：输入 "腾讯的市值是多少？"
- **查询上市信息**：输入 "小米什么时候上市的？"
- **知识库问答**：输入相关问题，系统会检索已索引的 PDF 内容回答
- **日常对话**：输入 "你好"

## Features / 功能特性
- ✅ **实时流式响应**：展示 Agent 处理进度
- ✅ **智能意图识别**：自动判断查询类型（财务/上市/对话）
- ✅ **并行数据获取**：同时调用多个数据工具提升效率
- ✅ **富文本展示**：Markdown 格式化输出研究报告
- ✅ **错误处理**：友好的异常提示和降级策略
