# 中文伪代码：LLM 分析意图，提取公司名

# 输入: state.user_query
# 输出: 更新 state.company_name, state.intent, state.need_financial, state.need_listing

# 步骤1：加载提示词（src/prompts/analyzer.yaml）
# 步骤2：构造 LLM 输入
#   - 传入 user_query
#   - 约束输出结构：company_name, intent, need_financial, need_listing, confidence
# 步骤3：调用 LLM
# 步骤4：解析结构化输出
#   - 若 company_name 为空 且 intent 非 chat：
#       intent = chat
#       need_financial = false
#       need_listing = false
# 步骤5：写回 state
#   - state.company_name = 解析结果
#   - state.intent = 解析结果
#   - state.need_financial = 解析结果
#   - state.need_listing = 解析结果
#   - state.confidence = 解析结果
# 步骤6：记录 trace
#   - state.trace += "analyzer 完成"

# 路由建议（由 graph.py 读取）
# - intent=chat -> 直接进入 formatter 或 chat 处理节点
# - intent=financial/listing -> 进入 fetcher 触发并行工具
