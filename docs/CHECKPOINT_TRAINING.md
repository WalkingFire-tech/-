# 🔥 断点续传式进化架构

## 核心理念

**"随开随学，关机不丢进度，开机继续炼丹"**

系统不能假设永远在线，必须适配"不连续存在"的生命状态。通过断点续传机制，系统利用任何可用的时间窗口（哪怕只有15分钟），也能完成一次有效的自我迭代。

---

## 📊 架构对比

| 特性 | 传统训练 | 断点续传式进化 |
| :--- | :--- | :--- |
| **训练中断** | 进度丢失，从头开始 | 保存检查点，继续训练 |
| **系统关机** | 状态丢失 | 状态持久化到文件 |
| **开机恢复** | 无法恢复 | 自动从检查点继续 |
| **时间利用** | 需要长时间窗口 | 利用碎片时间（15分钟） |
| **计算浪费** | 中断后全部浪费 | 完全不浪费 |

---

## 🧬 工作流程

### 完整生命周期

```
【场景1: 系统开机】
   ↓
检查状态文件: data/furnace_state.json
   ↓
发现待学习数据: 14条
   ↓
【场景2: 开始训练】
   ↓
Step 0/100 → Step 20/100
   ↓
【场景3: 用户要用电脑】
   ↓
训练暂停 → 保存检查点 (step=20, loss=2.20)
   ↓
【场景4: 系统关机】
   ↓
状态持久化到文件
   ↓
【场景5: 再次开机】
   ↓
检查状态文件 → 发现检查点
   ↓
【场景6: 继续训练】
   ↓
从 step 20 继续 → Step 100/100
   ↓
训练完成 → 版本升级 ✅
```

---

## 📁 文件结构

```
alliance_pioneer/
├── core/
│   ├── furnace_state.py          # 状态管理器（断点续传核心）
│   ├── furnace_trainer.py        # 碎片时间训练器
│   ├── furnace_scheduler.py      # 主调度器
│   ├── gold_extractor.py         # 黄金数据提取器
│   └── instant_learning.py       # L1即时学习
├── scripts/
│   ├── start_furnace.py          # 启动脚本
│   └── demo_checkpoint.py        # 断点续传演示
├── data/
│   ├── furnace_state.json        # 状态文件（关机不丢失）
│   └── pending_training.jsonl    # 待学习数据
└── start_furnace.bat             # Windows启动脚本
```

---

## 🔥 核心组件

### 1. 状态管理器 (furnace_state.py)

```python
class FurnaceState:
    """
    炼丹炉状态管理器
    
    核心功能：
    - 记录训练进度（检查点）
    - 管理待学习样本
    - 支持断点续传
    - 持久化到文件（关机不丢失）
    """
    
    def checkpoint(self, epoch, step, total_steps, loss):
        """保存训练检查点"""
        
    def get_checkpoint(self) -> Optional[Dict]:
        """获取检查点"""
```

### 2. 碎片时间训练器 (furnace_trainer.py)

```python
class FurnaceTrainer:
    """
    碎片时间训练器
    
    核心能力：
    - 估算可用时间窗口
    - 执行增量训练
    - 支持断点续传
    - 自动控制训练时长
    """
    
    def _get_available_time(self) -> int:
        """估算当前可用的训练时间（分钟）"""
        hour = datetime.now().hour
        
        if 0 <= hour < 6:
            return 180  # 深夜，有3小时
        elif 6 <= hour < 9:
            return 60   # 早晨，有1小时
        elif 12 <= hour < 14:
            return 30   # 午休，有30分钟
        elif 22 <= hour < 24:
            return 90   # 晚间，有1.5小时
        else:
            return 15   # 其他时间，只有15分钟
```

### 3. 主调度器 (furnace_scheduler.py)

```python
class FurnaceScheduler:
    """
    炼丹炉调度器
    
    适配开关机场景：
    - 开机时自动检查并执行训练
    - 关机时保存状态
    - 利用碎片时间进行训练
    """
    
    def _shutdown(self, signum, frame):
        """优雅关机"""
        self.is_running = False
        self.state.save()
```

---

## 🚀 使用方式

### 方式1: 持续运行（推荐）

```bash
# Windows
双击 start_furnace.bat

# 或命令行
python scripts/start_furnace.py
```

### 方式2: 单次检查

```bash
python scripts/start_furnace.py --once
```

### 方式3: 自定义配置

```bash
python scripts/start_furnace.py --interval 600 --threshold 10
```

---

## 📊 状态文件示例

```json
{
  "current_version": 5,
  "total_learned_samples": 247,
  "pending_samples": [...],
  "training_checkpoint": {
    "epoch": 0,
    "step": 156,
    "total_steps": 500,
    "loss": 2.34,
    "last_updated": "2026-06-27T22:15:00"
  },
  "training_history": [
    {"date": "2026-06-27", "samples": 14, "version": 5, "duration_minutes": 32},
    {"date": "2026-06-26", "samples": 11, "version": 4, "duration_minutes": 28}
  ]
}
```

---

## 💡 时间窗口估算

| 时间段 | 可用时间 | 说明 |
| :--- | :--- | :--- |
| 0:00 - 6:00 | 180分钟 | 深夜，用户不在 |
| 6:00 - 9:00 | 60分钟 | 早晨，可能空闲 |
| 12:00 - 14:00 | 30分钟 | 午休，短暂空闲 |
| 22:00 - 24:00 | 90分钟 | 晚间，可能空闲 |
| 其他时间 | 15分钟 | 碎片时间 |

---

## ✅ 核心优势

| 特性 | 如何实现 |
| :--- | :--- |
| **支持关机** | 训练状态持久化到 `furnace_state.json` |
| **断点续传** | 每次训练保存检查点，下次从中断处继续 |
| **碎片时间利用** | 根据当前时间估算可用时长，自动调整训练量 |
| **零停机进化** | 训练与推理分离，不影响主服务 |
| **渐进式积累** | 每次只学5-10条，稳定不遗忘 |
| **优雅关机** | 捕获关机信号，保存状态后退出 |

---

## 🎯 与PSAA架构的关系

断点续传式进化是PSAA架构的L2层（夜间固化区）的增强版：

| PSAA层次 | 功能 | 断点续传增强 |
| :--- | :--- | :--- |
| **L1即时学习** | 秒级生效 | 无需增强（已经即时） |
| **L2夜间固化** | 每周训练 | **支持断点续传，碎片时间训练** |
| **L3季度升华** | 范式突破 | 无需增强（手动触发） |

---

## 🔥 启动你的炼丹炉

```bash
# Windows
双击 start_furnace.bat

# 或命令行
python scripts/start_furnace.py

# 演示断点续传
python scripts/demo_checkpoint.py
```

---

## 💡 最终启示

**"系统不能假设永远在线，但可以永远准备好学习"**

通过断点续传机制，系统实现了：

1. **随开随学**：任何时间开机都能学习
2. **关机不丢进度**：状态持久化到文件
3. **开机继续炼丹**：从检查点恢复训练
4. **碎片时间利用**：15分钟也能完成一次迭代

**这才是真正的"碎片时间进化引擎"！**