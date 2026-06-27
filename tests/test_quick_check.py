import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.memory.stereo_memory import get_stereo_memory

store = get_stereo_memory()

print("测试 get_recent:")
recent = store.get_recent(limit=5)
print(f"  最近记忆数: {len(recent)}")

print("\n测试 get_by_topic:")
topic_memories = store.get_by_topic("项目", limit=5)
print(f"  主题记忆数: {len(topic_memories)}")

print("\n测试 get_stats:")
stats = store.get_stats()
print(f"  总记忆数: {stats.get('total_memories', 0)}")

print("\n✅ 立体记忆适配方法测试通过")