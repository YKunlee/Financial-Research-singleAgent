"""
清理空会话脚本

功能：
1. 检查数据库中的所有会话
2. 找出没有任何消息的会话（空会话）
3. 删除这些空会话

白话解释：
就像清理咖啡店的空账单，把那些客人拿了号但没点任何东西的单子删掉
"""

import sqlite3
from pathlib import Path

# 数据库路径
db_path = Path(__file__).parent.parent / "chainlit_data.db"

def cleanup_empty_chats():
    """清理空会话"""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print("开始检查空会话...")
    
    # 1. 获取所有会话
    cursor.execute("SELECT id, name, created_at FROM threads ORDER BY created_at DESC")
    all_threads = cursor.fetchall()
    print(f"\n总会话数: {len(all_threads)}")
    
    # 2. 检查每个会话的消息数量
    empty_threads = []
    for thread in all_threads:
        thread_id = thread['id']
        cursor.execute("SELECT COUNT(*) as count FROM steps WHERE thread_id = ?", (thread_id,))
        msg_count = cursor.fetchone()['count']
        
        if msg_count == 0:
            empty_threads.append(thread)
            print(f"  [空会话] ID: {thread_id[:30]}..., Name: {thread['name']}, Created: {thread['created_at']}")
    
    print(f"\n发现 {len(empty_threads)} 个空会话")
    
    # 3. 询问是否删除
    if empty_threads:
        response = input("\n是否删除这些空会话？(y/n): ")
        if response.lower() == 'y':
            for thread in empty_threads:
                cursor.execute("DELETE FROM threads WHERE id = ?", (thread['id'],))
                print(f"  ✓ 删除会话: {thread['name']}")
            
            conn.commit()
            print(f"\n✓ 已删除 {len(empty_threads)} 个空会话")
        else:
            print("\n取消删除")
    else:
        print("\n✓ 没有空会话需要清理")
    
    conn.close()
    print("="*60 + "\n")

if __name__ == "__main__":
    cleanup_empty_chats()
