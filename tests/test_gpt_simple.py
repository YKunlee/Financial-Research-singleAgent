"""
简单测试 GPT 模型是否可用
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def test_openai_api():
    """测试 OpenAI API 连接"""
    print("=" * 70)
    print("测试 OpenAI API 连接")
    print("=" * 70)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ 未找到 OPENAI_API_KEY")
        return False
    
    print(f"✓ API Key 已加载: {api_key[:20]}...")
    
    try:
        from langchain_openai import ChatOpenAI
        
        # 测试 GPT-4o-mini（更便宜，更快）
        print("\n测试 GPT-4o-mini...")
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=api_key,
            temperature=0.7,
            max_tokens=100
        )
        
        response = llm.invoke("你好，请用一句话介绍你自己。")
        print(f"✅ GPT-4o-mini 响应成功!")
        print(f"回复: {response.content}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False


def test_deepseek_api():
    """测试 DeepSeek API 连接"""
    print("\n" + "=" * 70)
    print("测试 DeepSeek API 连接")
    print("=" * 70)
    
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("⚠️  未找到 DEEPSEEK_API_KEY（可选）")
        return False
    
    print(f"✓ API Key 已加载: {api_key[:20]}...")
    
    try:
        from langchain_openai import ChatOpenAI
        
        llm = ChatOpenAI(
            model="deepseek-chat",
            api_key=api_key,
            base_url="https://api.deepseek.com",
            temperature=0.7,
            max_tokens=100
        )
        
        response = llm.invoke("你好，请用一句话介绍你自己。")
        print(f"✅ DeepSeek 响应成功!")
        print(f"回复: {response.content}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False


if __name__ == "__main__":
    openai_ok = test_openai_api()
    deepseek_ok = test_deepseek_api()
    
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)
    print(f"OpenAI API: {'✅ 可用' if openai_ok else '❌ 不可用'}")
    print(f"DeepSeek API: {'✅ 可用' if deepseek_ok else '❌ 不可用 或 未配置'}")
