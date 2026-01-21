# 中文伪代码：定义 LangGraph 的 State 结构

# State = {
#   # 用户输入
#   user_query: "用户原始提问",

#   # LLM 解析结果
#   company_name: "公司名或股票代码",
#   intent: "financial | listing | chat",
#   confidence: "解析置信度(0-1)",

#   # 并行任务开关
#   need_financial: true/false,
#   need_listing: true/false,

#   # 任务执行结果（由工具节点写入）
#   financial_data: {
#     market_cap: "市值",
#     profit: "盈利/净利润",
#     source: "数据来源"
#   } | null,

#   listing_data: {
#     listed_date: "上市日期",
#     listing_status: "上市/退市/暂停",
#     board: "板块",
#     source: "数据来源"
#   } | null,

#   # 日常对话回复（当 intent=chat）
#   chat_reply: "聊天回复文本" | null,

#   # 前端卡片输出
#   card_json: { ... } | null,

#   # 控制与诊断
#   errors: ["错误信息"],
#   trace: ["节点执行轨迹"],
#   parallel_done: {
#     financial: true/false,
#     listing: true/false
#   }
# }

# 说明
# - 各节点只读写与自己相关的字段
# - 并行节点写入 financial_data 或 listing_data
# - formatter 统一消费所有字段并产出 card_json
