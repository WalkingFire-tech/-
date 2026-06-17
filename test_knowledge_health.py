"""
测试知识健康度评估
"""
import sys
sys.path.insert(0, ".")

from core.knowledge_health import knowledge_health

print("\n" + "="*60)
print("📊 知识健康度评估测试")
print("="*60)

# 执行健康检查
result = knowledge_health.check()

# 显示报告
print(result['report'])

# 显示详细数据
print("\n【详细数据】")
print(f"\n知识统计:")
print(f"  总数: {result['knowledge']['total']}条")
print(f"  类型分布: {result['knowledge']['by_type']}")

print(f"\n记忆层级:")
for layer, count in result['memory']['layers'].items():
    print(f"  {layer}: {count}条")

print(f"\n技能与规则:")
print(f"  工具函数: {result['skills']['total']}个")
print(f"  学习规则: {result['rules']['total']}条")
print(f"  活跃规则: {result['rules']['active']}条")

print(f"\n质量指标:")
print(f"  平均质量: {result['quality']['avg_quality']:.1f}")
print(f"  高质量占比: {result['quality']['high_quality_ratio']*100:.1f}%")

print(f"\n学习趋势:")
print(f"  7天增长: {result['trend']['week_growth']}条")
print(f"  30天增长: {result['trend']['month_growth']}条")

print(f"\n综合评分:")
print(f"  覆盖度: {result['score']['coverage']:.0f}/20")
print(f"  质量: {result['score']['quality']:.0f}/20")
print(f"  记忆结构: {result['score']['memory']:.0f}/15")
print(f"  技能: {result['score']['skills']:.0f}/15")
print(f"  规则: {result['score']['rules']:.0f}/15")
print(f"  活力: {result['score']['activity']:.0f}/15")
print(f"  总分: {result['score']['total']:.0f}/100")

print("\n" + "="*60)
print("✅ 测试完成")
print("="*60)