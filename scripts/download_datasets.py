"""
下载高质量开源数据集
"""
import json
import os
from pathlib import Path
from typing import List, Dict

def download_alpaca_zh_sample():
    """
    下载Alpaca中文数据集样例
    实际使用时应该从Hugging Face下载完整数据集
    """
    # 这里提供一些示例数据
    # 完整数据集应该从 https://huggingface.co/datasets 下载
    sample_data = [
        {
            "instruction": "解释什么是机器学习",
            "input": "",
            "output": "机器学习是人工智能的一个分支，它使计算机系统能够从数据中学习并改进，而无需明确编程。机器学习算法通过分析大量数据来识别模式，并利用这些模式做出预测或决策。"
        },
        {
            "instruction": "总结以下文本的主要内容",
            "input": "深度学习是机器学习的一个子集，使用多层神经网络来学习数据的表示。它在图像识别、语音识别和自然语言处理等领域取得了突破性进展。",
            "output": "该文本介绍了深度学习的定义和主要应用领域。深度学习作为机器学习的子集，通过多层神经网络学习数据表示，在图像、语音和NLP领域有重要应用。"
        },
        {
            "instruction": "将以下句子翻译成英文",
            "input": "人工智能正在改变我们的生活方式。",
            "output": "Artificial intelligence is changing the way we live."
        },
        {
            "instruction": "什么是监督学习？请举例说明。",
            "input": "",
            "output": "监督学习是机器学习的一种类型，算法从标记的训练数据中学习。训练数据包含输入和对应的正确输出。例如：垃圾邮件分类（输入是邮件内容，输出是垃圾邮件或正常邮件）、房价预测（输入是房屋特征，输出是价格）。"
        },
        {
            "instruction": "计算以下数学问题",
            "input": "一个神经网络有3层，第一层有100个神经元，第二层有50个神经元，第三层有10个神经元。总共有多少个神经元？",
            "output": "总神经元数量 = 100 + 50 + 10 = 160个神经元。"
        },
        {
            "instruction": "比较过拟合和欠拟合的区别",
            "input": "",
            "output": "过拟合：模型在训练数据上表现很好，但在新数据上表现差。原因：模型太复杂、训练数据太少。解决方法：正则化、增加数据、简化模型。\n\n欠拟合：模型在训练数据和新数据上都表现不好。原因：模型太简单、特征不足。解决方法：增加模型复杂度、添加更多特征。"
        },
        {
            "instruction": "解释梯度下降算法的工作原理",
            "input": "",
            "output": "梯度下降是一种优化算法，用于最小化损失函数。工作原理：1）计算损失函数在当前参数下的梯度（导数）；2）沿着梯度的反方向更新参数（因为梯度指向增长最快的方向）；3）重复直到收敛或达到最大迭代次数。学习率控制每次更新的步长。"
        },
        {
            "instruction": "什么是特征工程？为什么它很重要？",
            "input": "",
            "output": "特征工程是从原始数据中提取、构造和选择特征的过程，目的是让机器学习算法能更好地学习。它很重要因为：1）好的特征可以显著提升模型性能；2）可以降低模型复杂度；3）可以融入领域知识。特征工程往往决定了模型性能的上限。"
        },
        {
            "instruction": "用简单的语言解释神经网络",
            "input": "",
            "output": "神经网络模仿人脑的工作方式。它由许多神经元组成，这些神经元分层排列。每个神经元接收输入，进行计算，然后传递输出。通过调整神经元之间的连接强度（权重），网络可以学习识别模式。就像教孩子认字一样，通过大量练习，网络逐渐学会正确识别。"
        },
        {
            "instruction": "列出机器学习项目的主要步骤",
            "input": "",
            "output": "机器学习项目的主要步骤：\n1. 问题定义：明确要解决什么问题\n2. 数据收集：获取相关数据\n3. 数据预处理：清洗、转换数据\n4. 特征工程：提取有意义的特征\n5. 模型选择：选择合适的算法\n6. 模型训练：用数据训练模型\n7. 模型评估：测试模型性能\n8. 参数调优：优化模型参数\n9. 模型部署：将模型应用到生产环境"
        }
    ]
    
    output_dir = Path('data/external')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'alpaca_zh_sample.jsonl'
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in sample_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"✅ Alpaca中文样例已保存: {output_file}")
    print(f"   数量: {len(sample_data)}条")
    
    return len(sample_data)


def download_coig_cqia_sample():
    """
    下载COIG-CQIA样例
    这是一个高质量中文指令数据集
    """
    sample_data = [
        {
            "instruction": "请解释以下概念",
            "input": "反向传播算法",
            "output": "反向传播（Backpropagation）是训练神经网络的核心算法。它通过链式法则计算损失函数对每个权重的梯度。过程：1）前向传播计算输出；2）计算损失；3）反向传播计算梯度；4）更新权重。这个算法使得训练深层网络成为可能。"
        },
        {
            "instruction": "分析以下代码的功能",
            "input": "model.fit(X_train, y_train, epochs=100, batch_size=32)",
            "output": "这行代码用于训练机器学习模型。参数说明：\n- X_train: 训练数据的特征\n- y_train: 训练数据的标签\n- epochs=100: 训练100轮\n- batch_size=32: 每次使用32个样本更新参数\n\n这是典型的监督学习训练过程。"
        },
        {
            "instruction": "什么是卷积神经网络？它有什么优势？",
            "input": "",
            "output": "卷积神经网络（CNN）是一种专门用于处理网格状数据的神经网络，特别适合图像处理。\n\n主要组件：\n- 卷积层：提取局部特征\n- 池化层：降低维度\n- 全连接层：分类\n\n优势：\n1. 参数共享，减少参数数量\n2. 平移不变性\n3. 自动特征提取\n4. 在图像识别任务上表现优异"
        },
        {
            "instruction": "解释强化学习中的探索与利用平衡",
            "input": "",
            "output": "在强化学习中，智能体需要在探索和利用之间平衡：\n\n探索（Exploration）：尝试新的动作，发现可能更好的策略。\n利用（Exploitation）：使用已知的最优动作，获得即时奖励。\n\n如果只探索：浪费时间在已知不好的动作上。\n如果只利用：可能错过更好的策略。\n\n常用方法：ε-贪心算法（以ε概率探索，1-ε概率利用）。"
        },
        {
            "instruction": "比较批梯度下降和随机梯度下降",
            "input": "",
            "output": "批梯度下降（BGD）：\n- 每次使用全部数据计算梯度\n- 收敛稳定\n- 计算慢，内存需求大\n\n随机梯度下降（SGD）：\n- 每次使用单个样本计算梯度\n- 收敛快，但波动大\n- 可以跳出局部最优\n\n小批量梯度下降（Mini-batch GD）：\n- 折中方案，每次使用一小批数据\n- 结合了BGD和SGD的优点\n- 实践中最常用"
        }
    ]
    
    output_dir = Path('data/external')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'coig_cqia_sample.jsonl'
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in sample_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"✅ COIG-CQIA样例已保存: {output_file}")
    print(f"   数量: {len(sample_data)}条")
    
    return len(sample_data)


def download_sharegpt_sample():
    """
    下载ShareGPT样例
    真实用户对话数据
    """
    sample_data = [
        {
            "instruction": "我想学习机器学习，应该从哪里开始？",
            "input": "",
            "output": "建议的学习路径：\n\n1. 基础知识：\n   - Python编程\n   - 线性代数、概率统计\n   - 基本的微积分\n\n2. 入门课程：\n   - Andrew Ng的机器学习课程\n   - fast.ai的实践课程\n\n3. 实践项目：\n   - Kaggle竞赛\n   - 经典数据集练习（MNIST、Titanic等）\n\n4. 进阶学习：\n   - 深度学习框架（PyTorch/TensorFlow）\n   - 阅读经典论文\n\n关键是边学边练，不要只看不练！"
        },
        {
            "instruction": "我的模型准确率只有60%，怎么提升？",
            "input": "",
            "output": "准确率低可能的原因和解决方案：\n\n1. 数据问题：\n   - 数据量不够？→ 收集更多数据\n   - 数据不平衡？→ 使用采样或加权\n   - 数据质量差？→ 数据清洗\n\n2. 特征问题：\n   - 特征不够？→ 特征工程\n   - 特征选择不当？→ 特征选择\n\n3. 模型问题：\n   - 模型太简单？→ 换更复杂的模型\n   - 模型太复杂？→ 正则化、简化\n\n4. 训练问题：\n   - 没训练够？→ 增加epoch\n   - 学习率不对？→ 调整学习率\n\n建议：先检查数据，再调整模型。"
        },
        {
            "instruction": "PyTorch和TensorFlow选哪个？",
            "input": "",
            "output": "两个框架都很优秀，选择建议：\n\nPyTorch：\n✅ 动态图，调试方便\n✅ 代码更Pythonic\n✅ 学术研究首选\n✅ 社区活跃\n\nTensorFlow：\n✅ 生产部署成熟\n✅ 移动端支持好\n✅ Google生态\n✅ 工业界常用\n\n建议：\n- 学习/研究 → PyTorch\n- 生产部署 → TensorFlow\n- 初学者 → PyTorch（更容易上手）\n\n其实两个都学最好，很多概念相通。"
        }
    ]
    
    output_dir = Path('data/external')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'sharegpt_sample.jsonl'
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in sample_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"✅ ShareGPT样例已保存: {output_file}")
    print(f"   数量: {len(sample_data)}条")
    
    return len(sample_data)


def download_full_datasets():
    """
    下载完整数据集（需要Hugging Face访问）
    """
    print("\n📥 下载完整数据集说明:")
    print("=" * 60)
    
    datasets = [
        {
            "name": "COIG-CQIA",
            "source": "m-a-p/COIG-CQIA",
            "size": "~100万条",
            "description": "中文高质量指令数据集"
        },
        {
            "name": "alpaca-zh",
            "source": "shibing624/alpaca-zh",
            "size": "~5万条",
            "description": "Alpaca中文翻译版"
        },
        {
            "name": "ShareGPT-Chinese-English-90k",
            "source": "shibing624/ShareGPT-Chinese-English-90k",
            "size": "~9万条",
            "description": "真实用户对话数据"
        }
    ]
    
    for ds in datasets:
        print(f"\n{ds['name']}:")
        print(f"  来源: huggingface.co/datasets/{ds['source']}")
        print(f"  规模: {ds['size']}")
        print(f"  说明: {ds['description']}")
    
    print("\n" + "=" * 60)
    print("下载命令:")
    print("  pip install datasets")
    print("  python -c \"from datasets import load_dataset; ds = load_dataset('m-a-p/COIG-CQIA')\"")


if __name__ == "__main__":
    print("=" * 60)
    print("下载高质量微调数据集")
    print("=" * 60)
    
    print("\n[1] 下载Alpaca中文样例...")
    count1 = download_alpaca_zh_sample()
    
    print("\n[2] 下载COIG-CQIA样例...")
    count2 = download_coig_cqia_sample()
    
    print("\n[3] 下载ShareGPT样例...")
    count3 = download_sharegpt_sample()
    
    print("\n[4] 完整数据集下载说明...")
    download_full_datasets()
    
    print("\n" + "=" * 60)
    print(f"✅ 样例数据已准备: {count1 + count2 + count3}条")
    print("   位置: data/external/")
    print("=" * 60)