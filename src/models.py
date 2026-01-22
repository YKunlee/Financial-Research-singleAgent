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
    """模型基础配置 - 像身份证一样集中存储所有模型名

    前端负责告诉我“现在用哪个模型名字”,
    我再根据这个名字去环境变量里翻对应的 Key。
    """

    # 单一默认模型名称:
    # - 想换模型时,只需要改这里或通过前端传参覆盖
    # - 例如前端传入 "gpt-4o-mini" / "deepseek-chat"
    model_name: str = "gpt-4o-mini"

    def get_api_key(self) -> str:
        """根据当前模型名去环境变量里查找对应的 Key。

        约定:
        - 模型名: gpt-4o-mini  -> 环境变量: GPT_4O_MINI_API_KEY
        - 模型名: deepseek-chat -> 环境变量: DEEPSEEK_CHAT_API_KEY

        这样前端只需要传模型名,后端按约定拼出变量名去 .env 里找即可。
        """
        # 把模型名转换成环境变量风格: 小写/横杠 -> 大写/下划线
        normalized = self.model_name.replace("-", "_").upper()
        env_var = f"{normalized}_API_KEY"
        return os.getenv(env_var, "")


class ModelManager:
    """模型管理器 - 工业级解耦实现,像快递站统一管理所有模型配送"""
    
    def __init__(self):
        self.settings = ModelSettings()
        self._models: Dict[str, ChatOpenAI] = {}
        
        # 预校验 - 启动时就检查当前模型对应的 Key 在不在
        if not self.settings.get_api_key():
            raise ValueError(
                f"❌ 缺失模型 {self.settings.model_name} 的 API Key 环境变量,请在 .env 中配置对应的 *_API_KEY"
            )

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
                "model": self.settings.model_name,
                "api_key": self.settings.get_api_key(),
                "temperature": 0.0,  # 分析任务必须用 0 保证稳定性
                "max_tokens": 4096,
                "model_kwargs": {"seed": 42},  # 进一步确保金融意图提取的一致性
            })
        return self._models["analyzer"]

    @property
    def chat_model(self) -> ChatOpenAI:
        """
        对话模型 (节点专用):专注自然语言回复、总结
        
        这里与 analyzer_model 共用同一个底层模型名称,只是温度和用途不同;
        多模型选择(例如“DeepSeek / GPT-4o-mini”)交给前端控制。
        """
        if "chat" not in self._models:
            self._models["chat"] = self._create_model({
                "model": self.settings.model_name,
                "api_key": self.settings.get_api_key(),
                "temperature": 0.7,
                "max_tokens": 2048,
            })
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
