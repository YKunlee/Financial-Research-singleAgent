# 中文伪代码：将 state 的数据加工成前端卡片 JSON

# 输入: state
# 输出: state.card_json 或 chat_reply

# 步骤1：判断 intent
#   如果 intent == "chat":
#     - 使用 assistant 提示词生成回复（或复用已有 chat_reply）
#     - 输出为普通文本结构
#     - 写入 state.card_json = {"type": "chat", "text": reply}
#     - 结束

# 步骤2：构造金融卡片 JSON 骨架
#   card = {
#     "type": "fin_card",
#     "company": state.company_name,
#     "sections": []
#   }

# 步骤3：填充 financial 数据
#   如果 state.financial_data 存在:
#     - 添加 section: 市值、盈利、数据来源

# 步骤4：填充 listing 数据
#   如果 state.listing_data 存在:
#     - 添加 section: 上市日期、状态、板块、数据来源

# 步骤5：追加元信息
#   - 如果 errors 非空，附加 warning 区块
#   - 写入 state.card_json = card

# 步骤6：记录 trace
#   - state.trace += "formatter 完成"
