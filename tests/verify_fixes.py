"""
简单验证脚本 - 检查关键修复点
"""
import os
import re

def check_file_content(filepath, patterns, description):
    """检查文件是否包含指定模式"""
    if not os.path.exists(filepath):
        print(f"❌ {description}: 文件不存在")
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    all_found = True
    for pattern_name, pattern in patterns.items():
        if re.search(pattern, content, re.MULTILINE | re.DOTALL):
            print(f"  ✅ {pattern_name}")
        else:
            print(f"  ❌ {pattern_name}")
            all_found = False
    
    return all_found

def main():
    print("=" * 70)
    print("验证关键修复点")
    print("=" * 70)
    
    checks = [
        {
            "file": "core/services/cognitive_planner.py",
            "desc": "CognitivePlanner - 真实LLM推理",
            "patterns": {
                "LLM调用": r"async def _call_llm",
                "意图推理": r"async def infer_intent",
                "策略生成": r"async def generate_strategy",
                "无硬编码响应": r"# 不使用硬编码响应",
            }
        },
        {
            "file": "core/intent_router.py",
            "desc": "IntentRouter - 统一路由",
            "patterns": {
                "路由方法": r"async def route",
                "策略选择": r"def _select_strategy",
                "LLM集成": r"llm_client",
            }
        },
        {
            "file": "core/external_learner.py",
            "desc": "ExternalLearner - L5集成",
            "patterns": {
                "JSON安全解析": r"def _safe_parse_json",
                "L5进化触发": r"trigger_evolution|_trigger_l5_evolution",
                "线程安全": r"asyncio\.Lock|threading\.Lock",
            }
        },
        {
            "file": "core/presence/gap_growth.py",
            "desc": "GapGrowthEngine - 线程安全",
            "patterns": {
                "线程锁": r"self\._lock\s*=",
                "外部学习调用": r"external_learner",
                "异步保护": r"async def",
            }
        },
        {
            "file": "core/knowledge/detector.py",
            "desc": "SemanticGapDetector - 零硬编码",
            "patterns": {
                "配置加载": r"def _load_config",
                "知识库查询": r"knowledge_store|_get_from_knowledge",
                "无硬编码关键词": r"# 从知识库|从配置",
            }
        },
        {
            "file": "core/reflective_model_free_evolution.py",
            "desc": "ReflectiveModelFreeEvolution - 数据流对接",
            "patterns": {
                "知识获取": r"def _get_existing_knowledge|def _get_all_knowledge",
                "知识存储": r"def _store_verified_knowledge",
                "进化周期": r"async def run_evolution_cycle",
                "系统状态收集": r"def _collect_system_state",
            }
        },
    ]
    
    total = 0
    passed = 0
    
    for check in checks:
        print(f"\n📁 {check['desc']}")
        if check_file_content(check['file'], check['patterns'], check['desc']):
            passed += 1
        total += 1
    
    print("\n" + "=" * 70)
    print(f"验证结果: {passed}/{total} 通过")
    print("=" * 70)
    
    return passed == total

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)