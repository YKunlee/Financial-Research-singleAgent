# 中文伪代码：抓取上市日期、状态

# 输入: state.company_name
# 输出: state.listing_data

# 步骤1：调用外部数据源（API/数据库）
# 步骤2：解析为统一字段（上市日期、状态、板块、来源）
# 步骤3：写入 state.listing_data
# 步骤4：标记 state.parallel_done.listing = true
