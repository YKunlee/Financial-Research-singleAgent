# 中文伪代码：抓取市值、盈利

# 输入: state.company_name
# 输出: state.financial_data

# 步骤1：调用外部数据源（API/数据库）
# 步骤2：解析为统一字段（市值、盈利、来源）
# 步骤3：写入 state.financial_data
# 步骤4：标记 state.parallel_done.financial = true
