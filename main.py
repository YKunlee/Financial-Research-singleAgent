# FastAPI 入口（中文伪代码）
# 目标：启动 Web 服务，连接前端与 Agent

# 步骤1：加载环境变量（例如 API Key、模型配置）
# 步骤2：初始化 LangGraph（调用 src/graph.py 的构建函数）
# 步骤3：创建 FastAPI 实例
# 步骤4：定义 /chat 接口
#   - 输入：前端消息
#   - 调用：graph.invoke(state)
#   - 输出：formatter 生成的 JSON 或普通文本
# 步骤5：启动服务（由外部命令触发）
