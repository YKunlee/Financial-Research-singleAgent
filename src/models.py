"""
模型配置管理模块

为什么存在？
统一管理项目中使用的多个AI模型实例，包括：
- GPT-4o: 用于复杂的财务分析和数据处理
- GPT-4o-mini/DeepSeek: 用于轻量级对话和辅助任务

确保 API Key 的安全加载和模型的正确初始化
"""

import os
from typing import Optional, Dict, Any
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


# 配置管理 - 集中管理参数
class ModelSettings(BaseModel):
    """模型基础配置 - 像身份证一样集中存储所有 API 钥匙和默认设置"""
    openai_api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    deepseek_api_key: str = Field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    
    # 默认参数
    analyzer_model_name: str = "gpt-4o-mini"
    chat_model_name: str = "deepseek-chat"
    fallback_model_name: str = "gpt-4o-mini"


class ModelManager:
    """模型管理器 - 工业级解耦实现,像快递站统一管理所有模型配送"""
    
    def __init__(self):
        self.settings = ModelSettings()
        self._models: Dict[str, ChatOpenAI] = {}
        
        # 预校验 - 启动时就检查必需的钥匙在不在
        if not self.settings.openai_api_key:
            raise ValueError("❌ 缺失关键配置: OPENAI_API_KEY")

    def _create_model(self, config: Dict[str, Any]) -> ChatOpenAI:
        """模型创建工厂方法 - 统一的模型生产流程"""
        return ChatOpenAI(**config)

    @property
    def analyzer_model(self) -> ChatOpenAI:
        """
        分析模型 (节点专用):专注逻辑、提取、工具调用
        
        温度设为 0.0 是因为金融数据分析不能有随机性,
        就像银行计算利息必须每次结果一样,不能今天算出来是 100 明天就变成 101
        """
        if "analyzer" not in self._models:
            self._models["analyzer"] = self._create_model({
                "model": self.settings.analyzer_model_name,
                "api_key": self.settings.openai_api_key,
                "temperature": 0.0,  # 分析任务必须用 0 保证稳定性
                "max_tokens": 4096,
                "model_kwargs": {"seed": 42},  # 进一步确保金融意图提取的一致性
            })
        return self._models["analyzer"]

    @property
    def chat_model(self) -> ChatOpenAI:
        """
        对话模型 (节点专用):专注自然语言回复、总结
        
        支持 DeepSeek 优先逻辑,如果有 DeepSeek 的钥匙就用它,
        没有就降级到 GPT-4o-mini(像外卖优先顺丰,没有就用邮政)
        """
        if "chat" not in self._models:
            # 逻辑:如果有 DeepSeek Key,尝试构建 DeepSeek
            if self.settings.deepseek_api_key:
                config = {
                    "model": self.settings.chat_model_name,
                    "api_key": self.settings.deepseek_api_key,
                    "base_url": "https://api.deepseek.com",
                    "temperature": 0.7,
                    "max_tokens": 2048,
                }
            else:
                config = {
                    "model": self.settings.fallback_model_name,
                    "api_key": self.settings.openai_api_key,
                    "temperature": 0.7,
                    "max_tokens": 2048,
                }
            
            self._models["chat"] = self._create_model(config)
        return self._models["chat"]


# --- 全局快捷访问 ---

_manager: Optional[ModelManager] = None


def get_manager() -> ModelManager:
    """获取全局模型管理器(单例模式)"""
    global _manager
    if _manager is None:
        _manager = ModelManager()
    return _manager


def get_model(role: str = "chat") -> ChatOpenAI:
    """
    根据角色获取模型 - 节点只需要说"我要一个分析模型"就行,不用管底层是什么
    
    用法: get_model("analyzer") 或 get_model("chat")
    
    这就像你去餐厅点菜,只需要说"来份宫保鸡丁",
    不用管厨师用的是鲁花油还是金龙鱼油
    """
    manager = get_manager()
    if role == "analyzer":
        return manager.analyzer_model
    return manager.chat_model


# 保留旧的快捷访问函数,保证向后兼容
def get_analyzer_model() -> ChatOpenAI:
    """获取分析模型(用于财务分析等复杂任务)"""
    return get_model("analyzer")


def get_chat_model() -> ChatOpenAI:
    """获取对话模型(用于用户交互等轻量任务)"""
    return get_model("chat")
