"""
种子数据注入器
为高频确定性话题预先注入核心三元组
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from infrastructure.fact_store import fact_store


def inject_seed_data():
    """注入种子数据"""
    
    seeds = [
        # 冰雹形成（针对之前的错误案例）
        {
            "question": "为什么会有冰雹",
            "subject": "冰雹",
            "predicate": "形成机制",
            "object": "过冷水滴在强对流云中反复冻结",
            "source": "meteorology_textbook",
            "confidence": 0.95
        },
        {
            "question": "为什么会有冰雹",
            "subject": "冰雹",
            "predicate": "形成条件",
            "object": "强烈上升气流",
            "source": "meteorology_textbook",
            "confidence": 0.95
        },
        {
            "question": "为什么会有冰雹",
            "subject": "冰雹胚胎",
            "predicate": "形成位置",
            "object": "云层中上部零度层以上",
            "source": "meteorology_textbook",
            "confidence": 0.90
        },
        {
            "question": "为什么会有冰雹",
            "subject": "水蒸气",
            "predicate": "相变过程",
            "object": "凝华成冰晶",
            "source": "physics_textbook",
            "confidence": 0.95
        },
        {
            "question": "为什么会有冰雹",
            "subject": "高空",
            "predicate": "温度变化",
            "object": "高度越高温度越低",
            "source": "physics_textbook",
            "confidence": 0.95
        },
        
        # 数学确定性知识
        {
            "question": "圆周率",
            "subject": "π",
            "predicate": "数值",
            "object": "约等于3.14159",
            "source": "math_constant",
            "confidence": 1.0
        },
        {
            "question": "勾股定理",
            "subject": "直角三角形",
            "predicate": "边长关系",
            "object": "a²+b²=c²",
            "source": "math_theorem",
            "confidence": 1.0
        },
        
        # 物理确定性知识
        {
            "question": "光速",
            "subject": "光",
            "predicate": "真空速度",
            "object": "约30万公里每秒",
            "source": "physics_constant",
            "confidence": 1.0
        },
        {
            "question": "万有引力",
            "subject": "引力",
            "predicate": "公式",
            "object": "F=Gm₁m₂/r²",
            "source": "physics_law",
            "confidence": 1.0
        },
        
        # 史实确定性知识
        {
            "question": "中华人民共和国成立",
            "subject": "新中国成立",
            "predicate": "时间",
            "object": "1949年10月1日",
            "source": "history_record",
            "confidence": 1.0
        },
        {
            "question": "第一次工业革命",
            "subject": "蒸汽机",
            "predicate": "发明者",
            "object": "瓦特改良",
            "source": "history_record",
            "confidence": 0.95
        },
        
        # 化学确定性知识
        {
            "question": "水的分子式",
            "subject": "水",
            "predicate": "分子式",
            "object": "H₂O",
            "source": "chemistry_basic",
            "confidence": 1.0
        },
        {
            "question": "水的沸点",
            "subject": "水",
            "predicate": "标准大气压沸点",
            "object": "100摄氏度",
            "source": "chemistry_basic",
            "confidence": 1.0
        },
        
        # 生物学确定性知识
        {
            "question": "DNA双螺旋",
            "subject": "DNA",
            "predicate": "结构",
            "object": "双螺旋结构",
            "source": "biology_basic",
            "confidence": 1.0
        },
        {
            "question": "光合作用",
            "subject": "植物",
            "predicate": "能量转换",
            "object": "光能转化为化学能",
            "source": "biology_basic",
            "confidence": 0.95
        },
    ]
    
    # 注入种子数据
    injected = 0
    for seed in seeds:
        if not fact_store.check_assertion_exists(
            seed["question"],
            seed["subject"],
            seed["predicate"],
            seed["object"]
        ):
            fact_store.add_assertion(
                question=seed["question"],
                subject=seed["subject"],
                predicate=seed["predicate"],
                obj=seed["object"],
                source=seed["source"],
                confidence=seed["confidence"]
            )
            injected += 1
    
    return injected


def inject_correction_examples():
    """注入纠错示例（针对之前的错误案例）"""
    
    corrections = [
        # 露点/凝华概念纠错
        {
            "question": "为什么会有冰雹",
            "old": ("水蒸气", "相变", "露点或冰点"),
            "new": ("水蒸气", "相变", "凝华或冻结核化"),
            "source": "user_correction_expert"
        },
        # 温度变化逻辑纠错
        {
            "question": "为什么会有冰雹",
            "old": ("冰晶", "高空温度变化", "温度升高融化"),
            "new": ("冰晶", "高空温度变化", "温度降低继续冻结"),
            "source": "user_correction_expert"
        },
        # 天气描述纠错
        {
            "question": "为什么会有冰雹",
            "old": ("冰雹发生时", "天气状态", "天气晴朗"),
            "new": ("冰雹发生时", "天气状态", "积雨云雷暴天气"),
            "source": "user_correction_expert"
        },
        # 初始位置纠错
        {
            "question": "为什么会有冰雹",
            "old": ("冰雹胚胎", "初始形成位置", "云层底部"),
            "new": ("冰雹胚胎", "初始形成位置", "云层中上部"),
            "source": "user_correction_expert"
        },
    ]
    
    corrected = 0
    for corr in corrections:
        fact_store.add_correction(
            question=corr["question"],
            old_subject=corr["old"][0],
            old_predicate=corr["old"][1],
            old_obj=corr["old"][2],
            new_subject=corr["new"][0],
            new_predicate=corr["new"][1],
            new_obj=corr["new"][2],
            correction_source=corr["source"]
        )
        corrected += 1
    
    return corrected


if __name__ == "__main__":
    print("=" * 60)
    print("🌱 开始注入种子数据...")
    print("=" * 60)
    
    injected = inject_seed_data()
    print(f"\n✅ 注入了 {injected} 条新种子数据")
    
    corrected = inject_correction_examples()
    print(f"✅ 注入了 {corrected} 条纠错示例")
    
    stats = fact_store.get_stats()
    print(f"\n📊 当前统计:")
    print(f"   总断言数: {stats['total']}")
    print(f"   正向断言: {stats['positive']}")
    print(f"   否定断言: {stats['negations']}")
    print(f"   纠错记录: {stats['corrections']}")
    
    print("\n" + "=" * 60)
    print("种子数据注入完成")
    print("=" * 60)