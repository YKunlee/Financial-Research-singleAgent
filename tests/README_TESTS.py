"""
测试套件使用说明

## 测试文件说明

### 1. test_gpt_simple.py - API 连接测试
快速测试 OpenAI 和 DeepSeek API 是否可用

运行方式：
```bash
python tests/test_gpt_simple.py
```

### 2. test_analyzer.py - Analyzer 节点测试
测试 analyzer 节点的意图识别和实体提取功能

运行方式：
```bash
python tests/test_analyzer.py
```

### 3. test_formatter_only.py - Fetcher & Formatter 节点测试
独立测试 fetcher 和 formatter 节点逻辑（不依赖 LLM）
通过手动构造 state 来验证节点功能

运行方式：
```bash
python tests/test_formatter_only.py
```

### 4. test_nodes.py - 完整流程集成测试
端到端测试完整的 Agent 流程：
analyzer → fetcher → tools → formatter

运行方式：
```bash
python tests/test_nodes.py
```

## 快速开始

1. 确保已安装依赖：
```bash
pip install -r requirements.txt
```

2. 配置环境变量（.env 文件）：
```
OPENAI_API_KEY=your_key_here
DEEPSEEK_API_KEY=your_key_here  # 可选
```

3. 运行所有测试：
```bash
# 先测试 API 连接
python tests/test_gpt_simple.py

# 再运行完整流程测试
python tests/test_nodes.py
```

## 测试覆盖

- ✅ API 连接验证
- ✅ 意图识别和实体提取
- ✅ 并行任务分发
- ✅ 数据格式化
- ✅ 错误处理和降级
- ✅ 端到端流程
"""

if __name__ == "__main__":
    print(__doc__)
