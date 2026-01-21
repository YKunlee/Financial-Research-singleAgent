# 中文伪代码：逻辑分发节点（触发并行工具）

# 输入: state.need_financial, state.need_listing
# 输出: 发送到对应工具节点

# 步骤1：如果 need_financial 为 true -> 调用 financial 工具节点
# 步骤2：如果 need_listing 为 true -> 调用 listing 工具节点
# 步骤3：若两者都为 false -> 直接返回 formatter
