"""
数据层实现 - 支持多会话功能

提供两种实现方式：
1. InMemoryDataLayer - 内存存储（适合开发测试）
2. SQLiteDataLayer - SQLite持久化存储（适合生产环境）

白话解释：
- 内存版本：就像在白纸上记笔记，关闭程序后消失
- SQLite版本：就像在本子上记笔记，关闭程序后依然保存
"""

from typing import Optional, Dict, List, Any
from datetime import datetime
import uuid
import sqlite3
import json
from pathlib import Path

from chainlit.data import BaseDataLayer
from chainlit.data.base import ThreadDict
from chainlit.types import Pagination, PaginatedResponse, ThreadFilter
from chainlit.user import PersistedUser


class InMemoryDataLayer(BaseDataLayer):
    """
    内存数据层实现
    
    核心数据结构：
    - threads: 存储所有会话的字典 {thread_id: ThreadDict}
    - steps: 存储每个会话的消息 {thread_id: [StepDict]}
    """
    
    def __init__(self):
        """初始化内存存储"""
        self.threads: Dict[str, ThreadDict] = {}  # 会话字典
        self.steps: Dict[str, List[Dict[str, Any]]] = {}  # 消息字典
        self.users: Dict[str, Dict[str, Any]] = {}  # 用户字典
        print("[InMemoryDataLayer] 内存数据层已初始化")
    
    # ==================== Thread（会话）管理 ====================
    
    async def create_thread(self, thread: ThreadDict) -> ThreadDict:
        """
        创建新会话
        
        场景：用户点击"新建对话"时调用
        """
        thread_id = thread.get("id") or str(uuid.uuid4())
        thread["id"] = thread_id
        thread["createdAt"] = datetime.utcnow().isoformat()
        
        # 确保 userIdentifier 字段存在（Chainlit 要求）
        if "userId" in thread and "userIdentifier" not in thread:
            thread["userIdentifier"] = thread["userId"]
        
        # 存储会话
        self.threads[thread_id] = thread
        self.steps[thread_id] = []  # 初始化空消息列表
        
        print(f"[InMemoryDataLayer] 创建新会话: {thread_id}, 名称: {thread.get('name', '未命名')}")
        return thread
    
    async def get_thread(self, thread_id: str) -> Optional[ThreadDict]:
        """
        获取指定会话
        
        场景：用户点击某个历史会话时调用
        """
        thread = self.threads.get(thread_id)
        if thread:
            print(f"[InMemoryDataLayer] 获取会话: {thread_id}")
        return thread
    
    async def update_thread(
        self,
        thread_id: str,
        name: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
    ):
        """
        更新会话信息
        
        场景：系统自动根据对话内容生成会话名称
        """
        if thread_id in self.threads:
            thread = self.threads[thread_id]
            if name is not None:
                thread["name"] = name
            if user_id is not None:
                thread["userId"] = user_id
                thread["userIdentifier"] = user_id  # 同步更新 userIdentifier
            if metadata is not None:
                thread["metadata"] = metadata
            if tags is not None:
                thread["tags"] = tags
            
            print(f"[InMemoryDataLayer] 更新会话: {thread_id}, 新名称: {name}")
    
    async def delete_thread(self, thread_id: str):
        """
        删除会话
        
        场景：用户删除某个历史会话
        """
        if thread_id in self.threads:
            del self.threads[thread_id]
            if thread_id in self.steps:
                del self.steps[thread_id]
            print(f"[InMemoryDataLayer] 删除会话: {thread_id}")
    
    async def list_threads(
        self, pagination: Pagination, filters: ThreadFilter
    ) -> PaginatedResponse[ThreadDict]:
        """
        获取会话列表
        
        场景：展示侧边栏的历史会话列表
        """
        print(f"\n{'='*60}")
        print(f"[list_threads] 开始获取会话列表")
        print(f"[list_threads] 当前存储的会话数: {len(self.threads)}")
        print(f"[list_threads] 会话ID列表: {list(self.threads.keys())}")
        
        # 获取所有会话
        all_threads = list(self.threads.values())
        
        # 打印每个会话的详细信息
        for thread in all_threads:
            print(f"[list_threads]   - ID: {thread.get('id')}, Name: {thread.get('name')}, UserID: {thread.get('userId')}")
        
        # 按创建时间倒序排列（最新的在前）
        all_threads.sort(
            key=lambda x: x.get("createdAt", ""), 
            reverse=True
        )
        
        # 分页处理
        first = pagination.first or 20
        cursor = pagination.cursor or 0
        
        start_idx = int(cursor) if isinstance(cursor, (int, str)) and str(cursor).isdigit() else 0
        end_idx = start_idx + first
        
        page_threads = all_threads[start_idx:end_idx]
        has_next = end_idx < len(all_threads)
        
        print(f"[list_threads] 返回会话数: {len(page_threads)}")
        print(f"{'='*60}\n")
        
        return PaginatedResponse(
            data=page_threads,
            pageInfo={
                "hasNextPage": has_next,
                "startCursor": str(start_idx),
                "endCursor": str(end_idx) if has_next else None,
            }
        )
    
    async def get_thread_author(self, thread_id: str) -> str:
        """获取会话作者"""
        thread = self.threads.get(thread_id)
        return thread.get("userId", "anonymous") if thread else "anonymous"
    
    # ==================== Step（消息）管理 ====================
    
    async def create_step(self, step_dict: Dict[str, Any]):
        """
        保存消息
        
        场景：用户发送消息或 AI 回复时调用
        """
        thread_id = step_dict.get("threadId")
        if thread_id:
            if thread_id not in self.steps:
                self.steps[thread_id] = []
            
            self.steps[thread_id].append(step_dict)
            print(f"[InMemoryDataLayer] 保存消息到会话 {thread_id}: {step_dict.get('name', 'message')}")
    
    async def update_step(self, step_dict: Dict[str, Any]):
        """更新消息（例如流式输出完成后）"""
        thread_id = step_dict.get("threadId")
        step_id = step_dict.get("id")
        
        if thread_id and thread_id in self.steps:
            for i, step in enumerate(self.steps[thread_id]):
                if step.get("id") == step_id:
                    self.steps[thread_id][i] = step_dict
                    break
    
    async def delete_step(self, step_id: str):
        """删除消息"""
        for thread_id, steps in self.steps.items():
            self.steps[thread_id] = [s for s in steps if s.get("id") != step_id]
    
    # ==================== 获取会话历史（用于恢复会话）====================
    
    def get_thread_messages(self, thread_id: str) -> List[Dict[str, Any]]:
        """
        获取会话的所有消息
        
        场景：用户切换到旧会话时，需要加载历史消息
        """
        messages = self.steps.get(thread_id, [])
        print(f"[InMemoryDataLayer] 获取会话 {thread_id} 的历史消息: {len(messages)} 条")
        return messages
    
    # ==================== 用户管理 ====================
    
    async def get_user(self, identifier: str) -> Optional[PersistedUser]:
        """
        获取用户信息
        
        场景：用户登录后，系统查询用户是否存在
        """
        print(f"[InMemoryDataLayer] 尝试获取用户: {identifier}, 当前用户列表: {list(self.users.keys())}")
        user_dict = self.users.get(identifier)
        if user_dict:
            print(f"[InMemoryDataLayer] ✓ 找到用户: {identifier}")
            # 返回 PersistedUser 对象而不是字典
            return PersistedUser(
                id=user_dict["id"],
                identifier=user_dict["identifier"],
                metadata=user_dict.get("metadata", {}),
                createdAt=user_dict.get("createdAt")
            )
        else:
            print(f"[InMemoryDataLayer] ✗ 用户不存在: {identifier}")
        return None
    
    async def create_user(self, user) -> PersistedUser:
        """
        创建新用户
        
        场景：用户首次登录时自动创建用户记录
        
        白话解释：
        就像第一次用微信时，系统给你创建一个账号
        """
        identifier = user.identifier if hasattr(user, 'identifier') else str(user.get('identifier'))
        created_at = datetime.utcnow().isoformat()
        
        user_dict = {
            "id": identifier,
            "identifier": identifier,
            "metadata": user.metadata if hasattr(user, 'metadata') else user.get('metadata', {}),
            "createdAt": created_at
        }
        
        self.users[identifier] = user_dict
        print(f"[InMemoryDataLayer] 创建用户: {identifier}")
        
        # 返回 PersistedUser 对象
        return PersistedUser(
            id=identifier,
            identifier=identifier,
            metadata=user_dict["metadata"],
            createdAt=created_at
        )
    
    # ==================== 其他未实现的方法 ====================
    
    async def upsert_feedback(self, feedback):
        """保存反馈（简易版不需要）"""
        return ""
    
    async def delete_feedback(self, feedback_id: str):
        """删除反馈"""
        return True
    
    async def create_element(self, element_dict):
        """创建元素（如图片、文件）"""
        pass
    
    async def get_element(self, thread_id: str, element_id: str):
        """获取元素"""
        return None
    
    async def delete_element(self, element_id: str):
        """删除元素"""
        pass
    
    async def delete_user_session(self, id: str):
        """删除用户会话"""
        return True
    
    def build_debug_url(self) -> str:
        """构建调试 URL（简易版返回空字符串）"""
        return ""
    
    async def close(self):
        """关闭数据层连接（内存版无需操作）"""
        pass
    
    async def get_favorite_steps(self, user_id: str):
        """获取收藏的消息（简易版不支持收藏功能）"""
        return []


# ==================== SQLite 数据层实现 ====================

class SQLiteDataLayer(BaseDataLayer):
    """
    SQLite 数据层实现
    
    核心特性：
    - 数据持久化：所有对话存储在SQLite数据库中
    - 自动创建表：首次运行自动初始化数据库结构
    - 多会话支持：支持多个用户的多个会话
    
    白话解释：
    就像一个"电子笔记本"：
    - 每条消息都写入数据库文件
    - 关闭程序后数据依然保存
    - 下次启动可以继续查看历史记录
    """
    
    def __init__(self, db_path: str = "chainlit_data.db"):
        """
        初始化SQLite数据层
        
        参数：
            db_path: 数据库文件路径，默认为当前目录下的 chainlit_data.db
        """
        self.db_path = db_path
        print(f"[SQLiteDataLayer] 初始化数据库: {db_path}")
        
        # 确保数据库文件所在目录存在
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库表
        self._init_database()
        print("[SQLiteDataLayer] ✓ 数据库初始化完成")
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使查询结果可以通过列名访问
        return conn
    
    def _init_database(self):
        """
        初始化数据库表结构
        
        创建三张核心表：
        1. users - 用户表
        2. threads - 会话表
        3. steps - 消息表
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                identifier TEXT UNIQUE NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        # 会话表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS threads (
                id TEXT PRIMARY KEY,
                name TEXT,
                user_id TEXT NOT NULL,
                user_identifier TEXT,
                created_at TEXT NOT NULL,
                metadata TEXT,
                tags TEXT,
                FOREIGN KEY (user_id) REFERENCES users(identifier)
            )
        """)
        
        # 消息表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS steps (
                id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                type TEXT,
                name TEXT,
                output TEXT,
                created_at TEXT NOT NULL,
                metadata TEXT,
                FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE
            )
        """)
        
        # 创建索引以提升查询性能
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_threads_user_id 
            ON threads(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_threads_created_at 
            ON threads(created_at DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_steps_thread_id 
            ON steps(thread_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_steps_created_at 
            ON steps(created_at)
        """)
        
        conn.commit()
        conn.close()
    
    # ==================== Thread（会话）管理 ====================
    
    async def create_thread(self, thread: ThreadDict) -> ThreadDict:
        """
        创建新会话
        
        场景：用户点击"新建对话"时调用
        """
        thread_id = thread.get("id") or str(uuid.uuid4())
        thread["id"] = thread_id
        created_at = datetime.utcnow().isoformat()
        thread["createdAt"] = created_at
        
        # 确保 userIdentifier 字段存在
        if "userId" in thread and "userIdentifier" not in thread:
            thread["userIdentifier"] = thread["userId"]
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO threads (id, name, user_id, user_identifier, created_at, metadata, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            thread_id,
            thread.get("name", "New Chat"),
            thread.get("userId", "anonymous"),
            thread.get("userIdentifier", "anonymous"),
            created_at,
            json.dumps(thread.get("metadata", {})),
            json.dumps(thread.get("tags", []))
        ))
        
        conn.commit()
        conn.close()
        
        print(f"[SQLiteDataLayer] 创建新会话: {thread_id}, 名称: {thread.get('name')}")
        return thread
    
    async def get_thread(self, thread_id: str) -> Optional[ThreadDict]:
        """
        获取指定会话（包含历史消息）
        
        场景：用户点击某个历史会话时调用
        
        重要：返回的 ThreadDict 必须包含 steps 字段，
        Chainlit 框架才能正确显示历史消息
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, user_id, user_identifier, created_at, metadata, tags
            FROM threads
            WHERE id = ?
        """, (thread_id,))
        
        row = cursor.fetchone()
        
        if row:
            # 获取该会话的所有消息
            cursor.execute("""
                SELECT id, thread_id, type, name, output, created_at, metadata
                FROM steps
                WHERE thread_id = ?
                ORDER BY created_at ASC
            """, (thread_id,))
            step_rows = cursor.fetchall()
            
            # 构建 steps 列表，转换为 Chainlit 期望的格式
            steps = []
            for step_row in step_rows:
                steps.append({
                    "id": step_row["id"],
                    "threadId": step_row["thread_id"],
                    "type": step_row["type"],
                    "name": step_row["name"],
                    "output": step_row["output"],
                    "createdAt": step_row["created_at"],
                    "metadata": json.loads(step_row["metadata"]) if step_row["metadata"] else {}
                })
            
            conn.close()
            
            thread = {
                "id": row["id"],
                "name": row["name"],
                "userId": row["user_id"],
                "userIdentifier": row["user_identifier"],
                "createdAt": row["created_at"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                "tags": json.loads(row["tags"]) if row["tags"] else [],
                "steps": steps  # 包含历史消息，Chainlit 会自动渲染
            }
            print(f"[SQLiteDataLayer] 获取会话: {thread_id}，包含 {len(steps)} 条消息")
            return thread
        
        conn.close()
        return None
    
    async def update_thread(
        self,
        thread_id: str,
        name: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
    ):
        """
        更新会话信息
        
        场景：系统自动根据对话内容生成会话名称
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 构建动态更新SQL
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        
        if user_id is not None:
            updates.append("user_id = ?")
            params.append(user_id)
            updates.append("user_identifier = ?")
            params.append(user_id)
        
        if metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata))
        
        if tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(tags))
        
        if updates:
            params.append(thread_id)
            sql = f"UPDATE threads SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(sql, params)
            conn.commit()
            print(f"[SQLiteDataLayer] 更新会话: {thread_id}, 新名称: {name}")
        
        conn.close()
    
    async def delete_thread(self, thread_id: str):
        """
        删除会话
        
        场景：用户删除某个历史会话
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 删除会话（级联删除相关消息）
        cursor.execute("DELETE FROM threads WHERE id = ?", (thread_id,))
        cursor.execute("DELETE FROM steps WHERE thread_id = ?", (thread_id,))
        
        conn.commit()
        conn.close()
        
        print(f"[SQLiteDataLayer] 删除会话: {thread_id}")
    
    async def list_threads(
        self, pagination: Pagination, filters: ThreadFilter
    ) -> PaginatedResponse[ThreadDict]:
        """
        获取会话列表
            
        场景:展示侧边栏的历史会话列表
        
        重要：只返回当前用户的会话，避免授权失败
        """
        print(f"\n{'='*60}")
        print(f"[SQLiteDataLayer.list_threads] 开始从数据库获取会话列表")
        print(f"[SQLiteDataLayer.list_threads] filters.userId = {filters.userId if filters else 'None'}")
            
        conn = self._get_connection()
        cursor = conn.cursor()
            
        # 基础查询
        sql = """
            SELECT id, name, user_id, user_identifier, created_at, metadata, tags
            FROM threads
            WHERE 1=1
        """
        params = []
        count_params = []
            
        # 按用户过滤（关键：只返回当前用户的会话）
        if filters and filters.userId:
            sql += " AND user_id = ?"
            params.append(filters.userId)
            count_params.append(filters.userId)
            
        # 排序:按创建时间倒序
        sql += " ORDER BY created_at DESC"
            
        # 分页
        first = pagination.first or 20
        cursor_value = pagination.cursor or 0
            
        offset = int(cursor_value) if isinstance(cursor_value, (int, str)) and str(cursor_value).isdigit() else 0
        sql += " LIMIT ? OFFSET ?"
        params.extend([first, offset])
            
        cursor.execute(sql, params)
        rows = cursor.fetchall()
            
        threads = []
        for row in rows:
            thread_data = {
                "id": row["id"],
                "name": row["name"],
                "userId": row["user_id"],
                "userIdentifier": row["user_identifier"],
                "createdAt": row["created_at"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                "tags": json.loads(row["tags"]) if row["tags"] else []
            }
            threads.append(thread_data)
            print(f"[list_threads]   - ID: {row['id'][:8]}..., Name: {row['name']}, User: {row['user_id']}")
            
        # 检查是否有下一页（需要与查询条件一致）
        count_sql = "SELECT COUNT(*) as count FROM threads WHERE 1=1"
        if filters and filters.userId:
            count_sql += " AND user_id = ?"
        cursor.execute(count_sql, count_params)
        total_count = cursor.fetchone()["count"]
        has_next = (offset + first) < total_count
            
        conn.close()
            
        print(f"[SQLiteDataLayer] ✓ 获取会话列表: {len(threads)} 条，总计: {total_count}")
        print(f"{'='*60}\n")
            
        return PaginatedResponse(
            data=threads,
            pageInfo={
                "hasNextPage": has_next,
                "startCursor": str(offset),
                "endCursor": str(offset + first) if has_next else None,
            }
        )
    
    async def get_thread_author(self, thread_id: str) -> str:
        """获取会话作者"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT user_id FROM threads WHERE id = ?", (thread_id,))
        row = cursor.fetchone()
        conn.close()
        
        return row["user_id"] if row else "anonymous"
    
    # ==================== Step（消息）管理 ====================
    
    async def create_step(self, step_dict: Dict[str, Any]):
        """
        保存消息（带去重检查）
        
        场景：用户发送消息或 AI 回复时调用
        
        去重逻辑：通过 INSERT OR IGNORE 避免保存重复消息
        """
        thread_id = step_dict.get("threadId")
        step_id = step_dict.get("id") or str(uuid.uuid4())
        
        if not thread_id:
            print("[SQLiteDataLayer] ✗ 保存消息失败: 缺少 threadId")
            return
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 使用 INSERT OR IGNORE 避免重复插入（基于主键 id 去重）
        cursor.execute("""
            INSERT OR IGNORE INTO steps (id, thread_id, type, name, output, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            step_id,
            thread_id,
            step_dict.get("type", ""),
            step_dict.get("name", ""),
            step_dict.get("output", ""),
            step_dict.get("createdAt", datetime.utcnow().isoformat()),
            json.dumps(step_dict.get("metadata", {}))
        ))
        
        conn.commit()
        conn.close()
        
        print(f"[SQLiteDataLayer] 保存消息到会话 {thread_id}: {step_dict.get('name')}")
    
    async def update_step(self, step_dict: Dict[str, Any]):
        """更新消息（例如流式输出完成后）"""
        step_id = step_dict.get("id")
        if not step_id:
            return
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE steps 
            SET type = ?, name = ?, output = ?, metadata = ?
            WHERE id = ?
        """, (
            step_dict.get("type", ""),
            step_dict.get("name", ""),
            step_dict.get("output", ""),
            json.dumps(step_dict.get("metadata", {})),
            step_id
        ))
        
        conn.commit()
        conn.close()
    
    async def delete_step(self, step_id: str):
        """删除消息"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM steps WHERE id = ?", (step_id,))
        
        conn.commit()
        conn.close()
    
    def get_thread_messages(self, thread_id: str) -> List[Dict[str, Any]]:
        """
        获取会话的所有消息
        
        场景：用户切换到旧会话时，需要加载历史消息
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, thread_id, type, name, output, created_at, metadata
            FROM steps
            WHERE thread_id = ?
            ORDER BY created_at ASC
        """, (thread_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        messages = []
        for row in rows:
            messages.append({
                "id": row["id"],
                "threadId": row["thread_id"],
                "type": row["type"],
                "name": row["name"],
                "output": row["output"],
                "createdAt": row["created_at"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
            })
        
        print(f"[SQLiteDataLayer] 获取会话 {thread_id} 的历史消息: {len(messages)} 条")
        return messages
    
    # ==================== 用户管理 ====================
    
    async def get_user(self, identifier: str) -> Optional[PersistedUser]:
        """
        获取用户信息
        
        场景：用户登录后，系统查询用户是否存在
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, identifier, metadata, created_at
            FROM users
            WHERE identifier = ?
        """, (identifier,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            print(f"[SQLiteDataLayer] ✓ 找到用户: {identifier}")
            return PersistedUser(
                id=row["id"],
                identifier=row["identifier"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                createdAt=row["created_at"]
            )
        
        print(f"[SQLiteDataLayer] ✗ 用户不存在: {identifier}")
        return None
    
    async def create_user(self, user) -> PersistedUser:
        """
        创建新用户
        
        场景：用户首次登录时自动创建用户记录
        """
        identifier = user.identifier if hasattr(user, 'identifier') else str(user.get('identifier'))
        created_at = datetime.utcnow().isoformat()
        
        metadata = user.metadata if hasattr(user, 'metadata') else user.get('metadata', {})
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 使用 INSERT OR IGNORE 避免重复插入
        cursor.execute("""
            INSERT OR IGNORE INTO users (id, identifier, metadata, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            identifier,
            identifier,
            json.dumps(metadata),
            created_at
        ))
        
        conn.commit()
        conn.close()
        
        print(f"[SQLiteDataLayer] 创建用户: {identifier}")
        
        return PersistedUser(
            id=identifier,
            identifier=identifier,
            metadata=metadata,
            createdAt=created_at
        )
    
    # ==================== 其他未实现的方法 ====================
    
    async def upsert_feedback(self, feedback):
        """保存反馈（简易版不需要）"""
        return ""
    
    async def delete_feedback(self, feedback_id: str):
        """删除反馈"""
        return True
    
    async def create_element(self, element_dict):
        """创建元素（如图片、文件）"""
        pass
    
    async def get_element(self, thread_id: str, element_id: str):
        """获取元素"""
        return None
    
    async def delete_element(self, element_id: str):
        """删除元素"""
        pass
    
    async def delete_user_session(self, id: str):
        """删除用户会话"""
        return True
    
    def build_debug_url(self) -> str:
        """构建调试 URL（简易版返回空字符串）"""
        return ""
    
    async def close(self):
        """关闭数据层连接"""
        print("[SQLiteDataLayer] 关闭数据库连接")
    
    async def get_favorite_steps(self, user_id: str):
        """获取收藏的消息（简易版不支持收藏功能）"""
        return []
