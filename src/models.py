"""
模型配置管理模块

为什么存在？
统一管理项目中使用的多个AI模型实例，包括：
- GPT-4o: 用于复杂的财务分析和数据处理
- GPT-4o-mini/DeepSeek: 用于轻量级对话和辅助任务

确保 API Key 的安全加载和模型的正确初始化
"""

import os
from typing import Optional
from langchain_openai import ChatOpenAI


class ModelManager:
    """模型管理器 - 负责初始化和提供不同用途的AI模型"""
    
    def __init__(self):
        """
        初始化模型管理器
        从环境变量中加载 API Key
        """
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        
        if not self.openai_api_key:
            raise ValueError("未找到 OPENAI_API_KEY 环境变量，请在 .env 文件中配置")
        
        # 初始化模型实例
        self._analyzer_model = None
        self._chat_model = None
    
    @property
    def analyzer_model(self) -> ChatOpenAI:
        """
        分析模型 (GPT-4o)
        
        用途：处理复杂的财务分析、数据解读、负面信号检测等高级任务
        特点：推理能力强、准确度高
        """
        if self._analyzer_model is None:
            self._analyzer_model = ChatOpenAI(
                model="gpt-4o",
                api_key=self.openai_api_key,
                temperature=0.2,  # 较低温度，保证分析结果的一致性和准确性
                max_tokens=4096,
                model_kwargs={
                    "top_p": 0.9,
                }
            )
        return self._analyzer_model
    
    @property
    def chat_model(self) -> ChatOpenAI:
        """
        对话模型 (DeepSeek 或 GPT-4o-mini)
        
        用途：处理用户对话、问答、格式化输出等轻量级任务
        特点：响应快速、成本低
        """
        if self._chat_model is None:
            # 优先使用 DeepSeek，如果没有配置则使用 GPT-4o-mini
            if self.deepseek_api_key:
                self._chat_model = ChatOpenAI(
                    model="deepseek-chat",
                    api_key=self.deepseek_api_key,
                    base_url="https://api.deepseek.com",
                    temperature=0.7,  # 对话需要更自然，温度略高
                    max_tokens=2048,
                )
            else:
                self._chat_model = ChatOpenAI(
                    model="gpt-4o-mini",
                    api_key=self.openai_api_key,
                    temperature=0.7,
                    max_tokens=2048,
                )
        return self._chat_model
    
    def get_custom_model(
        self, 
        model_name: str, 
        temperature: float = 0.7,
        max_tokens: int = 2048,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ) -> ChatOpenAI:
        """
        获取自定义配置的模型
        
        Args:
            model_name: 模型名称
            temperature: 温度参数 (0-1)
            max_tokens: 最大令牌数
            api_key: API密钥（可选，默认使用 OpenAI）
            base_url: API基础URL（可选）
        
        Returns:
            配置好的模型实例
        """
        config = {
            "model": model_name,
            "api_key": api_key or self.openai_api_key,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if base_url:
            config["base_url"] = base_url
        
        return ChatOpenAI(**config)


# 全局单例实例
_model_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """
    获取全局模型管理器实例（单例模式）
    
    Returns:
        ModelManager: 模型管理器实例
    """
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager


# 快捷访问函数
def get_analyzer_model() -> ChatOpenAI:
    """获取分析模型（用于财务分析等复杂任务）"""
    return get_model_manager().analyzer_model


def get_chat_model() -> ChatOpenAI:
    """获取对话模型（用于用户交互等轻量任务）"""
    return get_model_manager().chat_model
