"""
自动化测试脚本 - 测试问题清单并积累训练数据
"""
import sys
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from main_integrated import AlliancePioneer

# 测试问题清单
TEST_QUESTIONS = [
    # 第一批：概念解释类
    {
        "id": 1,
        "category": "概念解释",
        "question": "什么是Transformer架构的核心创新？",
        "expected_points": [
            "自注意力机制",
            "并行计算优势",
            "位置编码",
            "对比RNN/LSTM"
        ]
    },
    {
        "id": 2,
        "category": "概念解释",
        "question": "什么是迁移学习的原理？",
        "expected_points": [
            "预训练-微调范式",
            "知识迁移机制",
            "应用场景举例",
            "冻结层作用"
        ]
    },
    {
        "id": 3,
        "category": "概念解释",
        "question": "什么是梯度消失问题？",
        "expected_points": [
            "链式法则导致梯度衰减",
            "深层网络影响",
            "激活函数作用",
            "解决方案（ReLU、残差连接）"
        ]
    },
    {
        "id": 4,
        "category": "概念解释",
        "question": "什么是批量归一化的作用？",
        "expected_points": [
            "内部协变量偏移",
            "训练加速原理",
            "推理时处理",
            "对比层归一化"
        ]
    },
    # 第二批：学习路径类
    {
        "id": 5,
        "category": "学习路径",
        "question": "如何从零开始学习自然语言处理？",
        "expected_points": [
            "分阶段规划",
            "具体资源推荐",
            "时间估计",
            "实践项目建议"
        ]
    },
    {
        "id": 6,
        "category": "学习路径",
        "question": "如何系统学习Transformer和BERT？",
        "expected_points": [
            "基础概念开始",
            "论文和课程推荐",
            "代码实践建议",
            "进阶路径"
        ]
    },
    {
        "id": 7,
        "category": "学习路径",
        "question": "如何学习PyTorch深度学习框架？",
        "expected_points": [
            "安装指导",
            "基础概念（张量、自动求导）",
            "模型构建流程",
            "项目练习推荐"
        ]
    },
    # 第三批：工具生成类
    {
        "id": 8,
        "category": "工具生成",
        "question": "帮我写一个Python脚本，自动整理下载文件夹",
        "expected_points": [
            "按文件类型分类",
            "预览模式",
            "错误处理",
            "配置选项"
        ]
    },
    {
        "id": 9,
        "category": "工具生成",
        "question": "帮我写一个数据分析脚本，统计CSV文件的基本信息",
        "expected_points": [
            "统计行数、列数",
            "检测缺失值",
            "基本统计量",
            "可视化选项"
        ]
    },
    {
        "id": 10,
        "category": "工具生成",
        "question": "帮我写一个批量图片压缩脚本",
        "expected_points": [
            "支持多种格式",
            "质量参数",
            "预览功能",
            "保留元数据选项"
        ]
    },
    # 第四批：方案建议类
    {
        "id": 11,
        "category": "方案建议",
        "question": "我想搭建一个个人知识库系统，有什么推荐方案？",
        "expected_points": [
            "对比多种方案",
            "各方案优缺点",
            "成本对比",
            "具体搭建步骤"
        ]
    },
    {
        "id": 12,
        "category": "方案建议",
        "question": "我需要部署一个机器学习模型到生产环境，如何选择方案？",
        "expected_points": [
            "对比多种方案",
            "性能和扩展性",
            "监控建议",
            "成本考虑"
        ]
    },
    {
        "id": 13,
        "category": "方案建议",
        "question": "我想学习数据分析，应该先学Python还是R？",
        "expected_points": [
            "对比两种语言",
            "适用场景",
            "学习曲线",
            "具体建议"
        ]
    },
    # 第五批：技术对比类
    {
        "id": 14,
        "category": "技术对比",
        "question": "PyTorch和TensorFlow有什么区别？",
        "expected_points": [
            "动态图vs静态图",
            "调试体验",
            "社区生态",
            "部署能力"
        ]
    },
    {
        "id": 15,
        "category": "技术对比",
        "question": "BERT和GPT有什么区别？",
        "expected_points": [
            "架构对比（Encoder vs Decoder）",
            "预训练任务对比",
            "应用场景对比",
            "参数规模对比"
        ]
    },
    {
        "id": 16,
        "category": "技术对比",
        "question": "CNN和RNN有什么区别？",
        "expected_points": [
            "适用数据类型",
            "架构特点",
            "计算效率",
            "应用场景"
        ]
    }
]

def evaluate_answer(answer: str, expected_points: list) -> dict:
    """
    评估回答质量
    
    Returns:
        {
            'score': 0-100,
            'covered_points': [],
            'missing_points': [],
            'needs_correction': bool
        }
    """
    answer_lower = answer.lower()
    covered = []
    missing = []
    
    for point in expected_points:
        # 简单的关键词匹配
        keywords = point.replace("（", "").replace("）", "").split("、")
        found = any(kw.lower() in answer_lower for kw in keywords if kw)
        
        if found:
            covered.append(point)
        else:
            missing.append(point)
    
    score = len(covered) / len(expected_points) * 100 if expected_points else 0
    needs_correction = score < 70 or len(answer) < 100
    
    return {
        'score': score,
        'covered_points': covered,
        'missing_points': missing,
        'needs_correction': needs_correction
    }

def run_automated_test():
    """
    运行自动化测试
    """
    print("="*70)
    print("联盟拓荒者 - 自动化测试")
    print("="*70)
    print()
    
    # 初始化系统
    print("🚀 初始化系统...")
    try:
        pioneer = AlliancePioneer()
        print("✅ 系统初始化成功")
    except Exception as e:
        print(f"❌ 系统初始化失败: {e}")
        return
    
    # 准备结果存储
    results = []
    corrections = []
    
    # 逐题测试
    for i, test_item in enumerate(TEST_QUESTIONS, 1):
        print(f"\n{'='*70}")
        print(f"测试 {i}/{len(TEST_QUESTIONS)}: [{test_item['category']}]")
        print(f"问题: {test_item['question']}")
        print(f"{'='*70}")
        
        try:
            # 调用系统处理问题
            result = pioneer.process_question(test_item['question'])
            answer = result['response']
            
            print(f"\n📝 系统回答:\n{answer[:500]}...")
            
            # 评估回答
            evaluation = evaluate_answer(answer, test_item['expected_points'])
            
            print(f"\n📊 评估结果:")
            print(f"   得分: {evaluation['score']:.1f}/100")
            print(f"   覆盖要点: {len(evaluation['covered_points'])}/{len(test_item['expected_points'])}")
            
            if evaluation['covered_points']:
                print(f"   ✅ 已覆盖: {', '.join(evaluation['covered_points'][:3])}")
            if evaluation['missing_points']:
                print(f"   ❌ 缺失: {', '.join(evaluation['missing_points'][:3])}")
            
            # 保存结果
            test_result = {
                'id': test_item['id'],
                'category': test_item['category'],
                'question': test_item['question'],
                'answer': answer,
                'expected_points': test_item['expected_points'],
                'evaluation': evaluation,
                'timestamp': datetime.now().isoformat()
            }
            results.append(test_result)
            
            # 如果需要纠错，记录
            if evaluation['needs_correction']:
                corrections.append({
                    'question': test_item['question'],
                    'system_answer': answer,
                    'issues': evaluation['missing_points'],
                    'category': test_item['category']
                })
                print(f"   ⚠️  标记为需要纠错")
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            results.append({
                'id': test_item['id'],
                'question': test_item['question'],
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
    
    # 保存测试结果
    output_dir = Path(__file__).parent.parent / "data" / "test_results"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存完整结果
    results_file = output_dir / f"test_results_{timestamp}.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            'test_time': datetime.now().isoformat(),
            'total_questions': len(TEST_QUESTIONS),
            'results': results,
            'corrections_needed': len(corrections)
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*70}")
    print("测试完成！")
    print(f"{'='*70}")
    print(f"✅ 测试结果已保存: {results_file}")
    print(f"📊 统计:")
    print(f"   - 总测试题数: {len(TEST_QUESTIONS)}")
    print(f"   - 需要纠错: {len(corrections)} 题")
    print(f"   - 平均得分: {sum(r['evaluation']['score'] for r in results if 'evaluation' in r) / len(results):.1f}/100")
    
    # 显示需要纠错的问题
    if corrections:
        print(f"\n⚠️  需要纠错的问题:")
        for i, corr in enumerate(corrections, 1):
            print(f"   {i}. [{corr['category']}] {corr['question'][:50]}...")
    
    print(f"\n💡 下一步: 为需要纠错的问题提供完整答案")

if __name__ == "__main__":
    run_automated_test()