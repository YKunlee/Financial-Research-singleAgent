"""
快速检查数据库状态
"""
import sqlite3
from pathlib import Path

db_path = "chainlit_data.db"

if not Path(db_path).exists():
    print(f"❌ 数据库文件不存在: {db_path}")
    print("提示：可能需要先运行一次应用创建数据库")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 查看所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"✓ 数据库表: {tables}")
    
    # 查看数据量
    cursor.execute("SELECT COUNT(*) FROM threads")
    thread_count = cursor.fetchone()[0]
    print(f"✓ 会话数量: {thread_count}")
    
    cursor.execute("SELECT COUNT(*) FROM steps")
    step_count = cursor.fetchone()[0]
    print(f"✓ 消息数量: {step_count}")
    
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    print(f"✓ 用户数量: {user_count}")
    
    # 查看最近的会话
    cursor.execute("SELECT id, name, user_id, created_at FROM threads ORDER BY created_at DESC LIMIT 5")
    recent_threads = cursor.fetchall()
    if recent_threads:
        print(f"\n最近的会话:")
        for thread in recent_threads:
            print(f"  - ID: {thread[0][:8]}..., Name: {thread[1]}, User: {thread[2]}, Time: {thread[3]}")
    
    conn.close()
