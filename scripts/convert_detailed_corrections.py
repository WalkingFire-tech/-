# -*- coding: utf-8 -*-
"""
将用户提供的纠错答案转换为训练数据
"""
import json
from pathlib import Path
from datetime import datetime

# 用户提供的完整答案
corrections = [
    {
        "question": "什么是Transformer架构的核心创新？",
        "answer": """Transformer是2017年由Google提出的革命性神经网络架构，其核心创新包括：

1. 自注意力机制（Self-Attention）
这是Transformer最核心的创新。自注意力机制允许模型在处理序列中每个位置时，能够直接关注到序列中所有其他位置，并计算它们之间的相关性权重。

关键公式：Attention(Q, K, V) = softmax(Q·K^T / √d_k) · V
- Q（Query）：当前位置的查询向量
- K（Key）：所有位置的关键向量
- V（Value）：所有位置的值向量

2. 多头注意力（Multi-Head Attention）
将自注意力机制并行运行多次（通常8-16头），每个头学习不同的注意力模式，捕捉不同类型的关系。

3. 位置编码（Positional Encoding）
为什么需要：RNN/LSTM通过顺序处理自然拥有位置信息，而Transformer并行处理所有位置，本身没有顺序概念。
实现方式：使用正弦和余弦函数的交替组合，让模型既能编码绝对位置，也能编码相对位置关系。

4. 并行计算优势
- RNN/LSTM：串行处理，时间复杂度O(n)，训练慢
- Transformer：并行处理，时间复杂度O(1)，训练快（GPU充分利用）

5. 与RNN/LSTM的核心对比
- 位置感知：RNN通过顺序处理，Transformer需要位置编码
- 长期依赖：RNN容易遗忘，Transformer直接全连接
- 训练并行性：RNN必须串行，Transformer完全并行

核心总结：Transformer通过自注意力机制实现了并行处理和全局依赖捕捉，摆脱了RNN的顺序限制，是现代大语言模型（GPT、BERT、LLaMA等）的基础架构。""",
        "category": "概念解释"
    },
    {
        "question": "什么是迁移学习的原理？",
        "answer": """迁移学习是指将一个任务上学习到的知识应用到另一个相关任务上的技术，核心思想是"站在巨人的肩膀上"。

1. 预训练-微调范式
这是迁移学习最经典的实现方式：
- 阶段一：预训练（Pre-training）- 在海量通用数据上训练模型，模型学到通用特征表示
- 阶段二：微调（Fine-tuning）- 在特定任务的小规模数据上继续训练，调整部分参数

2. 知识迁移机制
- 特征表示层：共享底层特征提取器（如ImageNet边缘检测可用于医学图像）
- 参数层：复用部分网络权重（如用预训练BERT权重初始化新模型）
- 结构层：复用网络架构（相同架构适应不同任务）

3. 冻结层的作用
在微调过程中，通常冻结底层（保留通用特征），微调顶层（适应特定任务）。
- 全部冻结：数据极小，只改变输出层，风险最低
- 冻结底层，微调顶层：数据较少，保留通用特征
- 全部微调：数据充足，完全适应新任务

4. 应用场景举例
- 计算机视觉：ImageNet分类 → 医学图像诊断、自动驾驶物体检测
- 自然语言处理：BERT/Mask LM → 情感分析、问答系统、文本分类
- 语音识别：大规模语音数据预训练 → 特定语言/方言的语音识别

核心总结：迁移学习的本质是将通用知识转化为特定领域的专用能力，通过预训练-微调范式实现，是现代AI模型高效训练的核心方法。""",
        "category": "概念解释"
    },
    {
        "question": "什么是梯度消失问题？",
        "answer": """梯度消失问题是指在训练深层神经网络时，梯度在反向传播过程中逐层衰减，导致靠近输入层的网络参数几乎不更新，模型难以学习。

1. 链式法则导致的梯度衰减
在反向传播中，梯度通过链式法则逐层传递：
∂L/∂W₁ = ∂L/∂y · ∂y/∂xₙ · ∂xₙ/∂xₙ₋₁ · ... · ∂x₂/∂x₁ · ∂x₁/∂W₁

每个激活函数的梯度（如sigmoid的梯度最大值0.25）都小于1，多层相乘后梯度指数级衰减：
- 10层：(0.25)^10 ≈ 9.5e-7
- 20层：(0.25)^20 ≈ 9.0e-13

2. 激活函数的影响
- Sigmoid：梯度范围[0, 0.25]，严重导致梯度消失
- Tanh：梯度范围[0, 1]，有风险（饱和区梯度小）
- ReLU：梯度范围{0, 1}，不易消失（正区间梯度=1）
- Leaky ReLU：梯度范围{0.01, 1}，不易消失

3. 对深层网络的影响
- 靠近输入的层：梯度消失，参数停滞，无法学习
- 靠近输出的层：梯度正常，参数更新
- 结果：网络实际上只训练了最后几层

4. 梯度消失问题的解决方案
- 使用ReLU激活函数：正区间梯度为1，不衰减
- 残差连接（ResNet）：跳跃连接，绕过衰减路径，可训练数百层
- 批量归一化：稳定输入分布，加速训练，缓解消失
- 适当初始化：Xavier/He初始化，保持方差稳定

核心总结：梯度消失是深层网络面临的根本挑战，源于链式法则中小于1的激活函数梯度被连乘。解决方案的核心思路是保持梯度在传递过程中不衰减，如使用ReLU和残差连接。""",
        "category": "概念解释"
    },
    {
        "question": "什么是批量归一化的作用？",
        "answer": """批量归一化（Batch Normalization, BN）是一种用于加速深度网络训练、提高稳定性的技术，通过对每一层输入进行标准化来实现。

1. 训练加速原理
BN的核心公式：
- μ_B = 1/m ∑x_i（小批量均值）
- σ_B² = 1/m ∑(x_i - μ_B)²（小批量方差）
- x̂_i = (x_i - μ_B) / √(σ_B² + ε)（标准化）
- y_i = γ·x̂_i + β（缩放和平移，可学习参数）

加速原理：
- 内部协变量偏移：标准化保证每层输入分布稳定
- 梯度饱和：将输入控制在激活函数敏感区间，加速梯度更新
- 学习率敏感性：允许使用更大的学习率（通常可提升5-10倍）
- 初始化的依赖性：降低对权重初始化的敏感度

2. 训练与推理的不同处理
训练时：
- 每个batch独立计算均值和方差
- 依赖batch大小（batch过小时统计不稳定）

推理时：
- 使用训练阶段累积的全局统计量（指数滑动平均）
- 推理时统计量固定，确保确定性输出

3. 与层归一化的对比
- 批量归一化（BN）：跨样本（batch维度）归一化，依赖batch大小，适用CNN（视觉任务）
- 层归一化（LN）：跨特征（channel维度）归一化，不依赖batch大小，适用Transformer（NLP任务）

选择建议：
- CNN/视觉任务：优先使用BN
- Transformer/NLP：优先使用LN
- 小batch训练：使用LN替代BN

核心总结：批量归一化通过标准化层输入来稳定训练，允许更大的学习率和更快的收敛。它与层归一化的选择取决于任务类型和batch大小。""",
        "category": "概念解释"
    },
    {
        "question": "如何从零开始学习自然语言处理？",
        "answer": """从零开始学习自然语言处理，建议分为五个阶段，总计约6-12个月。

第一阶段：编程基础（1-2个月）
核心技能：
- Python基础：变量、控制流、函数、类、模块
- 数据处理：字符串操作、正则表达式、文件读写
- 必备库：NumPy（数值计算）、Pandas（数据分析）、Matplotlib（可视化）

推荐资源：
- 课程：CS50（哈佛入门计算机）
- 教程：廖雪峰Python教程
- 练习：LeetCode（前100题）

阶段目标：能熟练编写100-200行的Python脚本

第二阶段：机器学习基础（2-3个月）
核心技能：
- 数学基础：线性代数、微积分、概率统计
- ML经典算法：线性回归、逻辑回归、决策树、朴素贝叶斯、SVM、K-Means
- 评估方法：交叉验证、混淆矩阵、准确率/召回率/F1

推荐资源：
- 课程：吴恩达《Machine Learning》
- 课程：李宏毅《机器学习》
- 书籍：《机器学习》（周志华）
- 实战：Kaggle入门赛（Titanic）

第三阶段：NLP基础与核心任务（2-3个月）
核心概念：
- 文本预处理：分词、词干化、停用词、TF-IDF
- NLP任务：文本分类、情感分析、命名实体识别、机器翻译
- 经典模型：Bag-of-Words、Word2Vec、GloVe

推荐资源：
- 课程：CS224n（斯坦福NLP）
- 课程：李宏毅《深度学习与人类语言处理》
- 书籍：《Speech and Language Processing》（Jurafsky）

第四阶段：深度学习与NLP（2-3个月）
核心技能：
- 深度学习基础：神经网络、反向传播、优化器
- NLP核心架构：RNN/LSTM、Transformer、BERT/GPT
- 框架掌握：PyTorch（推荐）或TensorFlow

推荐资源：
- 课程：李沐《动手学深度学习》（PyTorch版）
- 论文：Attention Is All You Need（Transformer原论文）
- 论文：BERT原论文
- 实战：Hugging Face Transformers

第五阶段：项目实战与前沿（持续进行）
项目建议：
- 入门：电影评论情感分类（使用TF-IDF+逻辑回归）
- 进阶：中文新闻标题分类（使用BERT微调）
- 高级：智能问答助手（构建完整的RAG系统）
- 前沿：本地LLM微调（用LoRA微调Qwen/Llama）

核心建议：
1. 代码先行：边学边写代码，而不是只读理论
2. 项目驱动：每个阶段完成一个小项目来检验学习效果
3. 保持同步：关注最新论文和技术动态
4. 加入社区：GitHub、Kaggle、知乎NLP板块，交流学习""",
        "category": "学习路径"
    },
    {
        "question": "如何系统学习Transformer和BERT？",
        "answer": """系统学习Transformer和BERT，建议从概念→原理→代码→应用四个层次推进。

层次一：基础概念起点
在学习Transformer之前，先确保掌握以下前置知识：
- 神经网络基础：前向传播、反向传播、激活函数
- RNN/LSTM：序列处理、上下文表示
- 词嵌入：Word2Vec、GloVe
- 注意力机制：Seq2Seq+Attention

快速入门资源：
- 视频：李宏毅《Transformer讲解》（1小时，中文）
- 博客：《The Illustrated Transformer》（图解，强烈推荐）

层次二：论文与课程推荐
论文阅读顺序（从易到难）：
1. Attention Is All You Need（Transformer原论文）- 自注意力、多头、位置编码
2. BERT: Pre-training of Deep Bidirectional Transformers - Mask LM、下一句预测、双向
3. Improving Language Understanding by GPT - 单向LM、预训练-微调

课程推荐：
- CS224n Lecture 5-7（斯坦福）：从RNN到Transformer逐步演进
- 李宏毅《Transformer》（台大）：中文讲解，形象易懂
- The Annotated Transformer（Harvard NLP）：逐行代码注释+原理
- Hugging Face Course：用Transformers库微调模型

层次三：代码实践建议
代码学习路线：
1. 从零实现一个简单的注意力机制
2. 从零实现一个Mini-Transformer（单头）
3. 使用PyTorch实现完整Transformer
4. 使用Hugging Face加载预训练模型
5. 在具体任务上微调BERT/GPT

代码资源：
- The Annotated Transformer（Harvard NLP）：逐行实现的完整代码
- PyTorch官方Transformer示例：官方实现参考
- Hugging Face Transformers：最流行的预训练模型库
- nanoGPT：最小化GPT实现（Andrej Karpathy）

层次四：应用与实践
实践项目建议：
- 文本分类：BERT微调，掌握微调流程
- 问答系统：BERT/DistilBERT，理解提取式问答
- 文本生成：GPT-2微调，掌握生成式模型
- 句子相似度：Sentence-BERT，理解对比学习

核心总结：学习Transformer和BERT的最佳路径是先从图解和视频建立直观理解，再阅读原论文掌握原理，然后从零实现Mini版本，最后在实际任务中微调预训练模型。""",
        "category": "学习路径"
    },
    {
        "question": "如何学习PyTorch深度学习框架？",
        "answer": """学习PyTorch的路径分为安装→核心概念→模型构建→实战训练四个阶段。

阶段一：安装指导
安装方式：
# CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# CPU版本（无GPU）
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# 使用conda（推荐）
conda install pytorch torchvision torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia

# 验证安装
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"

环境配置建议：
- 使用虚拟环境（conda或venv）
- 避免全局安装导致依赖冲突
- GPU版本需先安装对应CUDA Toolkit

阶段二：核心概念
1. 张量（Tensor）
张量是PyTorch的核心数据结构，类似于NumPy的ndarray，但可以在GPU上运行。

创建张量：
- x = torch.tensor([1, 2, 3])：从列表
- x = torch.zeros(3, 4)：全零矩阵
- x = torch.randn(3, 4)：随机正态分布

张量属性：
- x.shape：形状
- x.dtype：数据类型
- x.device：设备 cpu 或 cuda:0

在GPU上运行：
x = x.cuda() if torch.cuda.is_available() else x

2. 自动求导（Autograd）
Autograd是PyTorch实现反向传播的核心机制，自动计算梯度。

示例：
x = torch.tensor([2.0], requires_grad=True)
y = x ** 2 + 3 * x + 1  # y = x² + 3x + 1
y.backward()  # 自动计算dy/dx
print(x.grad)  # tensor([7.0])  (2*2 + 3 = 7)

关键理解：
- requires_grad=True：标记需要梯度的张量
- backward()：计算梯度，累积到.grad属性
- torch.no_grad()：推理时禁用梯度（节省内存）

阶段三：模型构建流程
标准模型构建模板：
1. 定义模型结构（继承nn.Module）
2. 实例化模型并移动到GPU
3. 定义损失函数和优化器
4. 训练循环：清零梯度 → 前向传播 → 计算损失 → 反向传播 → 更新参数

阶段四：学习路线
- 基础操作：张量操作、索引、切片 → PyTorch官方Tutorial
- 自动求导：梯度计算、计算图 → 《PyTorch深度学习实战》
- 模型构建：nn.Module、nn.Sequential → 李沐《动手学深度学习》PyTorch版
- 训练流程：DataLoader、优化器、学习率调度 → PyTorch官方Examples
- 实战项目：CNN、RNN、Transformer实现 → Kaggle + GitHub开源项目

核心总结：学习PyTorch的核心是张量操作 + 自动求导 + nn.Module三大基石，建议从"手写数字识别"（MNIST）开始第一个实战项目。""",
        "category": "学习路径"
    },
    {
        "question": "帮我写一个Python脚本，自动整理下载文件夹",
        "answer": """以下是完整的下载文件夹整理脚本，包含预览模式、错误处理和灵活的配置选项。

核心功能：
1. 按文件扩展名自动分类（Images、Documents、Videos等）
2. 按关键词分类（Receipts、Screenshots等）
3. 预览模式（先查看效果再执行）
4. 错误处理（捕获并报告所有异常）
5. 配置文件支持（灵活的自定义规则）
6. 冲突处理（自动处理同名文件）

默认配置：
- Images: .jpg, .jpeg, .png, .gif, .bmp, .svg
- Documents: .pdf, .doc, .docx, .txt, .md, .rtf
- Spreadsheets: .xls, .xlsx, .csv, .ods
- Presentations: .ppt, .pptx, .key
- Archives: .zip, .rar, .7z, .tar, .gz
- Videos: .mp4, .avi, .mov, .mkv, .wmv
- Audio: .mp3, .wav, .flac, .aac
- Code: .py, .js, .html, .css, .java, .cpp, .go
- Executables: .exe, .msi, .dmg, .pkg

关键词分类：
- Receipts: receipt, invoice, bill
- Screenshots: screenshot, screen shot, 截屏
- Templates: template

使用示例：
# 预览模式
python organize_downloads.py ~/Downloads --config my_config.json

# 实际执行
python organize_downloads.py ~/Downloads --execute

# 自定义目标文件夹
python organize_downloads.py ~/Downloads --dest ~/整理好的文件 --execute

改进要点：
1. 预览模式：先查看效果再执行
2. 错误处理：捕获并报告所有异常
3. 配置文件：灵活的自定义规则
4. 冲突处理：自动处理同名文件
5. 多种分类方式：扩展名、关键词、日期""",
        "category": "工具生成"
    },
    {
        "question": "帮我写一个数据分析脚本，统计CSV文件的基本信息",
        "answer": """以下是完整的CSV数据分析脚本，包含缺失值检测、基本统计量和可视化报告。

核心功能：
1. 缺失值检测
- 统计每列缺失数量和百分比
- 按缺失率排序
- 可视化缺失值热力图

2. 基本统计量
- 数值列：均值、标准差、最小值、最大值、中位数、偏度、峰度
- 类别列：唯一值数量、最常见值、频率

3. 可视化报告
- 缺失值热力图
- 数值列分布图（直方图）
- 自动保存到reports目录

4. 数据概况
- 行数、列数
- 内存使用
- 重复行数

使用示例：
# 基本分析
python analyze_csv.py data.csv

# 生成可视化报告
python analyze_csv.py data.csv --visualize

# 指定输出目录
python analyze_csv.py data.csv --visualize --output ./my_reports

改进要点：
1. 缺失值检测：统计每列缺失数量和百分比
2. 基本统计量：均值、标准差、偏度、峰度
3. 可视化选项：缺失值热力图、数值分布图
4. 类别列统计：唯一值数量、最常见值""",
        "category": "工具生成"
    },
    {
        "question": "帮我写一个批量图片压缩脚本",
        "answer": """以下是完整的批量图片压缩脚本，支持多种格式、质量参数和预览功能。

核心功能：
1. 支持多种格式
- 输入：JPG、PNG、WebP、BMP、TIFF
- 输出：可指定为JPEG、PNG、WebP

2. 质量参数
- 可调节1-100
- 建议75-90
- WebP支持method参数（最高压缩）

3. 预览功能
- 先查看效果再执行
- 显示原始大小和压缩后大小
- 显示节省百分比

4. 备份机制
- 自动备份原图
- 备份到backup目录
- 文件名包含时间戳

5. 尺寸调整
- 支持最大宽高限制
- 保持宽高比
- 自动缩放

使用示例：
# 预览
python compress_images.py ./photos --quality 80

# 实际压缩
python compress_images.py ./photos --quality 80 --format WEBP --execute

# 指定输出目录
python compress_images.py ./photos -o ./compressed --quality 75 --execute

# 调整尺寸
python compress_images.py ./photos --max-width 1920 --max-height 1080 --execute

改进要点：
1. 支持多种格式：JPG、PNG、WebP、BMP、TIFF
2. 质量参数：可调节1-100
3. 预览功能：先查看效果再执行
4. 备份机制：自动备份原图
5. 尺寸调整：支持最大宽高限制""",
        "category": "工具生成"
    },
    {
        "question": "我想搭建一个个人知识库系统，有什么推荐方案？",
        "answer": """根据你的技术水平和需求，推荐以下三种方案：

方案一：Notion（最适合非技术用户）
- 费用：免费（个人），$10/月（团队）
- 难度：极低
- 优点：功能强大、多端同步、支持数据库、模板丰富
- 缺点：数据在云端、搜索中文略弱、需要联网
- 适合：非技术用户、团队协作

快速上手：
1. 注册Notion账号
2. 选择"知识库"模板
3. 按主题创建页面
4. 开始记录

方案二：Obsidian（最适合知识工作者）
- 费用：免费（个人），$10/月（同步）
- 难度：中等
- 优点：本地存储（隐私）、Markdown、双向链接、插件生态强大
- 缺点：学习曲线、同步收费
- 适合：重视隐私、喜欢双向链接、有技术基础

快速上手：
1. 下载Obsidian
2. 创建本地仓库
3. 安装核心插件（Tag Wrangler、Excalidraw）
4. 用Markdown记录笔记

方案三：Trilium（最适合技术用户）
- 费用：免费开源
- 难度：中等偏高
- 优点：树形结构、内容丰富、本地和自托管、支持脚本
- 缺点：界面较老旧、移动端弱
- 适合：喜欢结构化知识、自托管爱好者

对比总结：
| 维度 | Notion | Obsidian | Trilium |
| 存储方式 | 云端 | 本地 | 本地/自托管 |
| 学习成本 | 低 | 中 | 中高 |
| 功能丰富度 | 高 | 中高 | 中 |
| 同步 | 自动 | 需付费/手动 | 需配置 |
| 数据隐私 | ❌ | ✅ | ✅ |
| 最适合 | 日常笔记 | 知识网络 | 技术文档 |

推荐选择：
- 非技术用户：Notion（最简单）
- 知识工作者：Obsidian（功能平衡）
- 技术爱好者：Trilium（完全控制）""",
        "category": "方案建议"
    },
    {
        "question": "我需要部署一个机器学习模型到生产环境，如何选择方案？",
        "answer": """部署机器学习模型到生产环境，需要综合考虑性能、扩展性、监控和成本。

方案对比：
| 方案 | 适用场景 | 性能 | 扩展性 | 复杂度 | 成本 |
| Flask API + Docker | 小型项目 | 中 | 中 | 低 | 低 |
| FastAPI | 需要高性能API | 高 | 高 | 中 | 低 |
| TensorFlow Serving | TF模型专用 | 高 | 高 | 中 | 低 |
| TorchServe | PyTorch模型 | 高 | 高 | 中 | 低 |
| AWS SageMaker | 生产级部署 | 高 | 极高 | 中高 | 高 |
| ONNX Runtime | 跨框架优化 | 极高 | 中 | 中 | 低 |

推荐方案：FastAPI + Docker（最常用）

架构：
用户请求 → FastAPI → 模型加载 → 推理 → 返回结果
            ↑
         Docker容器

核心功能：
1. 模型加载：支持PyTorch、TensorFlow、ONNX
2. 预处理：tokenization、归一化等
3. 推理：GPU/CPU自动选择
4. 后处理：结果格式化
5. 健康检查：/health端点

监控建议：
1. Prometheus指标
- 请求总数（REQUEST_COUNT）
- 请求延迟（REQUEST_LATENCY）
- 错误总数（ERROR_COUNT）

2. 日志
- 请求日志
- 错误日志
- 性能日志

3. 告警
- 延迟过高
- 错误率上升
- GPU内存不足

部署步骤：
1. 容器化：使用Docker打包应用和依赖
2. 负载均衡：使用Nginx或云服务负载均衡器
3. 监控：集成Prometheus + Grafana
4. 日志：使用ELK或云日志服务
5. CI/CD：自动化部署流程

推荐选择：
- 小型项目：Flask + Docker
- 生产环境：FastAPI + Docker + Kubernetes
- 云原生：AWS SageMaker / Azure ML""",
        "category": "方案建议"
    },
    {
        "question": "我想学习数据分析，应该先学Python还是R？",
        "answer": """选择学习Python还是R取决于你的目标和时间。

详细对比：
| 维度 | Python | R |
| 学习曲线 | 平缓（通用语言） | 稍陡（统计语言） |
| 数据处理 | Pandas（强大） | dplyr/tidyverse（优雅） |
| 数据可视化 | Matplotlib/Seaborn | ggplot2（黄金标准） |
| 统计分析 | statsmodels/scipy | 完整统计库 |
| 机器学习 | scikit-learn/TF/PyTorch | caret/tidymodels |
| 深度学习 | TensorFlow/PyTorch | torch（较新） |
| 生态大小 | 最大 | 大 |
| 通用性 | 高（Web/系统/其他） | 低（专为数据分析） |
| 社区活跃度 | 极高 | 高 |
| 就业市场 | 更多岗位 | 部分专业领域 |

适用场景：
| 场景 | 推荐语言 | 原因 |
| 数据分析入门 | Python | 通用性强，学习资源多 |
| 学术统计研究 | R | 统计包更完善 |
| 机器学习工程 | Python | 部署生态更成熟 |
| 数据可视化 | R（ggplot2） | 语法更优雅 |
| Bioinformatics | R | 领域标准 |
| 商业数据分析 | Python | 更通用，团队协作好 |

建议：
如果时间有限（只学一个）→ Python
- 通用性更强，应用范围更广
- 社区更大，资源更丰富
- 更容易扩展到其他领域

如果时间充足（都学）→ 先Python后R
- Python作为主语言
- R用于统计分析和可视化专项

具体学习路径：
1. Python路线：Python基础 → Pandas → Matplotlib/Seaborn → scikit-learn
2. R路线：R基础 → tidyverse → ggplot2 → caret/tidymodels""",
        "category": "方案建议"
    },
    {
        "question": "PyTorch和TensorFlow有什么区别？",
        "answer": """PyTorch和TensorFlow都是主流深度学习框架，核心区别在于执行方式和调试体验。

核心区别：
| 维度 | PyTorch | TensorFlow 2.x |
| 执行方式 | 动态图（Eager Execution） | 静态图（默认）但支持Eager |
| 调试体验 | 极好（类似Python代码） | 需要特殊调试 |
| 学习曲线 | 平缓（接近原生Python） | 稍陡 |
| 研究领域 | 学术界首选 | 工业界常用 |
| 部署生态 | TorchServe | TensorFlow Serving |
| 移动端 | PyTorch Mobile | TensorFlow Lite |
| Web端 | ONNX.js | TensorFlow.js |
| 社区风格 | 研究导向，更新快 | 产品导向，稳定性高 |

动态图 vs 静态图：
PyTorch（动态图）：
- 代码即执行，可断点调试
- 每步都可调试
- 更直观

TensorFlow（静态图）：
- 先定义计算图，再执行
- 2.x已支持Eager
- 需要特殊调试

调试体验：
| 场景 | PyTorch | TensorFlow |
| 设置断点 | pdb.set_trace()可直接用 | 需配合tf.debugging |
| 打印中间值 | 直接print | 需用tf.print |
| 异常定位 | 清晰报错 | 有时模糊 |
| 动态修改 | 可在循环中修改 | 需要重新编译 |

选择建议：
| 你的情况 | 推荐 |
| 学术研究、快速实验 | PyTorch |
| 工业部署、需要稳定 | TensorFlow |
| 初学者 | PyTorch（更直观） |
| 生产级大规模部署 | TensorFlow Serving |
| 移动端部署 | TensorFlow Lite |

当前趋势：PyTorch在学术界占主导，TensorFlow在工业界仍有优势，但PyTorch正在快速追赶。""",
        "category": "技术对比"
    },
    {
        "question": "BERT和GPT有什么区别？",
        "answer": """BERT和GPT都是基于Transformer的语言模型，但架构和应用场景完全不同。

核心架构对比：
| 维度 | BERT | GPT |
| 架构 | 纯Encoder（双向） | 纯Decoder（单向） |
| 注意力方向 | 双向（看整个句子） | 单向（只看左边） |
| 训练任务 | Mask LM + NSP | 下一个词预测（LM） |
| 理解能力 | 最强 | 中等 |
| 生成能力 | 弱 | 最强 |
| 典型应用 | 分类、问答、NER | 对话、生成、续写 |

架构图对比：
BERT (Encoder)：
- 双向注意力，可看到全部输入
- 输出 ← 输出 ← 输出 ← 输出
- [CLS] [A] [B] [SEP]
- Encoder ← Encoder ← Encoder ← Encoder

GPT (Decoder)：
- 单向注意力，只能看左边
- 输出 → 输出 → 输出 → 输出
- [输入] → [预测] → [预测] → [预测]
- Decoder ← Decoder ← Decoder ← Decoder

预训练任务对比：
BERT - Masked Language Modeling：
- 输入: 机器学习 <arg_value> 是人工智能的 </think> 分支
- 预测: 学习、核心
- 随机mask掉15%的token
- 训练双向理解能力

GPT - Next Token Prediction：
- 输入: "机器学习是人工智能的"
- 预测: "核心分支"
- 预测下一个token
- 训练生成和语言建模能力

应用场景对比：
| 任务类型 | BERT | GPT |
| 文本分类 | 最佳 | 可做 |
| 情感分析 | 最佳 | 可做 |
| 命名实体识别 | 最佳 | 可做 |
| 问答系统 | 提取式 | 生成式 |
| 文本摘要 | 需要改进 | 最佳 |
| 对话生成 | 弱 | 最佳 |
| 代码生成 | 不适合 | 最佳 |

核心总结：BERT擅长理解，GPT擅长生成。选择取决于你的任务是理解型还是生成型。""",
        "category": "技术对比"
    },
    {
        "question": "CNN和RNN有什么区别？",
        "answer": """CNN和RNN是两种不同的神经网络架构，适用于不同类型的数据。

核心区别：
| 维度 | CNN | RNN |
| 数据类型 | 空间数据（图像） | 序列数据（文本、时序） |
| 核心操作 | 卷积（局部连接） | 循环（状态传递） |
| 连接方式 | 前向（局部感受野） | 循环（状态记忆） |
| 并行计算 | 可并行 | 必须串行 |
| 长依赖处理 | 通过层数堆叠 | 容易遗忘（LSTM改善） |
| 参数共享 | 卷积核共享 | 每步参数独立 |

适用数据类型：
CNN适用：
- 图像（局部相关性）
- 视频（空间-时间混合）
- 语音频谱（频率-时间）
- 数据网格（表格、点云）

RNN适用：
- 文本（字符到句子的顺序）
- 时间序列（股票、天气）
- 音频（波形序列）
- 任何有顺序的数据

架构特点对比：
CNN - 卷积操作：
- 局部连接：每个神经元只连接到输入的一小部分
- 共享权重：同一卷积核在空间上滑动
- 平移不变性：物体在不同位置都能识别

RNN - 循环操作：
- 状态记忆：h_t 包含之前所有时间步的信息
- 时间依赖：处理变长序列
- 梯度问题：容易消失/爆炸

计算效率对比：
| 场景 | CNN | RNN |
| 训练并行度 | 高（矩阵乘法） | 低（依赖上一步） |
| 推理速度 | 快 | 慢（逐token生成） |
| 参数数量 | 适中（通过共享） | 较大（不共享） |
| 内存占用 | 适中 | 较大（需存储所有状态） |
| 长序列处理 | 通过堆叠 | 易遗忘 |

核心总结：CNN适合空间数据（图像），RNN适合序列数据（文本、时序）。现代架构（如Transformer）正在取代RNN在NLP中的地位。""",
        "category": "技术对比"
    }
]

def convert_to_training_data():
    """
    将纠错数据转换为训练数据格式并合并
    """
    # 转换为Alpaca格式
    training_data = []
    for item in corrections:
        training_item = {
            "instruction": item["question"],
            "input": "",
            "output": item["answer"],
            "source": "user_correction_detailed",
            "category": item["category"],
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        training_data.append(training_item)
    
    # 读取现有训练数据
    base_dir = Path(__file__).parent.parent
    training_file = base_dir / "data" / "sft" / "combined_all_training_data_v2.jsonl"
    
    existing_data = []
    if training_file.exists():
        with open(training_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    existing_data.append(json.loads(line))
    
    # 合并数据
    all_data = existing_data + training_data
    
    # 写入新文件
    output_file = base_dir / "data" / "sft" / "combined_all_training_data_v3.jsonl"
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in all_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    # 统计
    print(f"✅ 转换完成！")
    print(f"   - 新增纠错数据: {len(training_data)} 条")
    print(f"   - 原有数据: {len(existing_data)} 条")
    print(f"   - 合并后总计: {len(all_data)} 条")
    print(f"   - 输出文件: {output_file}")
    
    # 按类别统计
    categories = {}
    for item in training_data:
        cat = item.get('category', 'general')
        categories[cat] = categories.get(cat, 0) + 1
    
    print(f"\n📊 新增数据类别分布:")
    for cat, count in categories.items():
        print(f"   - {cat}: {count} 条")
    
    print(f"\n🎯 当前进度: {len(all_data)}/1000 ({len(all_data)/10:.1f}%)")
    
    return len(all_data)

if __name__ == "__main__":
    convert_to_training_data()
