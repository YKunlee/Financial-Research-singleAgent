# Financial-Research-Agent
Financial Research Agent automates equity research by collecting market data, financial statements, filings, and news for a given company or industry. It summarizes revenue, profitability, guidance, risks, and management tone, and flags negative signals to support structured investment decisions.

金融研究智能体通过收集特定公司或行业的市场数据、财务报表、监管披露与新闻，自动化完成股票研究。它会总结收入、盈利能力、业绩指引、风险与管理层口径，并标记负面信号，以支持结构化的投资决策。

## Project Structure / 项目结构

```
Financial-Research-multiAgent/
├── main.py                 # FastAPI entry / FastAPI 入口
├── .env                    # Environment variables / 环境变量
├── src/
│   ├── state.py            # LangGraph State schema / LangGraph State 结构
│   ├── graph.py            # Graph wiring & routing / LangGraph 编排与路由
│   ├── nodes/              # Agent logic nodes / Agent 逻辑节点
│   │   ├── analyzer.py     # Intent + entity parsing / 意图识别与公司名抽取
│   │   ├── fetcher.py      # Fan-out dispatcher / 分发与并行触发
│   │   └── formatter.py    # Card JSON builder / 前端卡片 JSON 组装
│   ├── tools/              # Data tools / 数据抓取工具
│   │   ├── financial.py    # Market cap & profit / 市值/盈利
│   │   └── listing.py      # Listing info / 上市信息
│   └── prompts/            # Prompt configs / Prompt 配置
│       ├── analyzer.yaml   # Intent parsing / 意图解析
│       └── assistant.yaml  # Small talk / 日常对话
├── templates/              # Frontend templates / 前端模板
│   ├── index.html          # Chat page / Chat 页面
│   └── components/         # Components / 组件
│       ├── chat_bubble.html
│       └── fin_card.html
└── static/                 # Static assets / 静态资源
    ├── css/
    │   └── chatgpt.css
    └── js/
        └── chat.js
```

## Tech Stack / 用到的技术
- LangGraph: Graph orchestration, parallel fan-out/fan-in, and state passing / 负责 StateGraph 编排、并行 Fan-out/Fan-in 与状态传递
- FastAPI: Web server entry and API layer / Web 服务入口与接口层
- LLM: Intent and entity extraction via prompts / 意图识别与实体抽取（通过 prompts 配置）
- Template + Static: UI rendering and basic interactions / 前端卡片展示与基础交互
