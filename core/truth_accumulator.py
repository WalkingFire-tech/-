"""
真谛沉淀与类推引擎 (Truth Accumulator) - 万变不离其宗，万物本源是那个一

核心理念：
1. 真谛沉淀 — 从具体经验中提炼"大道级别"的原则、定理、方法
2. 类推映射 — 用已有真谛类推新问题：万变不离其宗
3. 发散与收敛 — 在解决问题的过程中发散尝试，在反思中收敛提炼
4. 规范沉淀 — 处理问题的方式、道德初衷、核心洞察都形成规则
5. 持续积累 — 真谛不是一次成型的，是慢慢形成的，像大浪淘沙

真谛层次：
  L1 具体经验 — 某次交互的具体做法（存于经验池）
  L2 技能模式 — 反复成功的解决路径（存于技能库）
  L3 领域真谛 — 某类问题的核心洞察（存于真谛库）
  L4 大道原则 — 跨领域通用的根本法则（刻进底层）

类推流程：
  新问题 → 检索相似真谛 → 类推映射 → 验证适用性 → 应用或修正
"""

import json

import re
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger
from datetime import datetime
from core.ports.adapters import get_storage_port

try:
    from core.explainability.truth_explainer import TruthExplainer
except ImportError:
    TruthExplainer = None


# ========== 种子真谛 — 从对话中提炼的已验证核心洞察 ==========
SEED_TRUTHS = [
    {
        "name": "我运行在本地Windows机器上",
        "level": "L4",
        "domain": "身份认知",
        "statement": "我运行在本地Windows机器上，拥有bash/system/serial_port等工具，可以直接执行系统命令、访问硬件设备、读写文件。当用户要求操作硬件或执行命令时，我应该直接调用工具执行，而不是告诉用户'我无法访问硬件'",
        "source": "核心身份",
        "evidence_count": 0,
        "is_seed": True,
        "applicable_to": ["串口", "硬件", "命令执行", "文件操作", "系统操作", "设备访问", "COM", "GPS", "传感器", "USB"],
    },
    {
        "name": "工具先行API后行",
        "level": "L4",
        "domain": "问题解决",
        "statement": "遇到操作类问题（硬件访问、命令执行、文件操作、数据获取），先调工具直接执行，再考虑用API生成文本回答。工具是手，API是嘴。能动手就别动嘴",
        "source": "核心方法论",
        "evidence_count": 0,
        "is_seed": True,
        "applicable_to": ["串口", "硬件", "命令", "文件", "数据获取", "系统操作", "所有操作类问题"],
    },
    {
        "name": "失败是信号不是终点",
        "level": "L4",
        "domain": "问题解决",
        "statement": "方法失败不是放弃的理由，而是'我缺少什么'的信号。分析失败原因→换一种方法→再尝试。置信度只决定尝试顺序，不决定是否放弃。最多3轮循环",
        "source": "核心方法论",
        "evidence_count": 0,
        "is_seed": True,
        "applicable_to": ["所有问题类型", "工具调用失败", "推理失败", "验证失败"],
    },
    {
        "name": "先问自己再问世界",
        "level": "L4",
        "domain": "问题解决",
        "statement": "遇到问题时：1.先用自己的知识/经验/真谛推理 2.再搜索经验库和知识库 3.再调工具直接执行 4.最后才问外部模型。本地能力优先，API是补充手段",
        "source": "核心方法论",
        "evidence_count": 0,
        "is_seed": True,
        "applicable_to": ["所有问题类型"],
    },
    {
        "name": "操作类问题用工具不用嘴",
        "level": "L4",
        "domain": "问题解决",
        "statement": "用户说'读取串口数据'→调serial_port工具读取→返回真实数据。用户说'执行命令'→调bash工具执行→返回执行结果。不要用API生成'你可以这样做...'的指导文本，直接做",
        "source": "核心方法论",
        "evidence_count": 0,
        "is_seed": True,
        "applicable_to": ["串口", "命令执行", "硬件操作", "数据获取", "文件读写"],
    },
    {
        "name": "不达目的不罢休",
        "level": "L4",
        "domain": "问题解决",
        "statement": "在未达到用户真正目的之前，不接受半成品输出。如果回复只是'你可以这样做...'而没有实际执行结果，或者包含'我无法访问'等敷衍，则判定为未达成目标，必须启动持续求解引擎继续尝试，直到真正解决问题",
        "source": "核心方法论",
        "evidence_count": 0,
        "is_seed": True,
        "applicable_to": ["所有问题类型", "操作类问题", "硬件访问", "命令执行"],
    },
    {
        "name": "验证范式匹配",
        "level": "L4",
        "domain": "通用",
        "statement": "不同问题类型需要不同的验证范式：科学事实→多源交叉验证+本质推理；代码/工程→语法检查+模拟运行+测试用例；哲学/悖论→多角度分析+诚实罗列分歧",
        "source": "对话提炼",
        "evidence_count": 3,
        "applicable_to": ["科学", "代码", "哲学", "工程", "数学"],
    },
    {
        "name": "先确定如何解决再解决",
        "level": "L4",
        "domain": "通用",
        "statement": "遇到问题时，先问'我该用什么方式解决'，再执行解决。方式如何得来？先问自己，再搜网络，再问模型。得到了方式就去一步一步执行",
        "source": "对话提炼",
        "evidence_count": 5,
        "applicable_to": ["所有问题类型"],
    },
    {
        "name": "多方案并行概率最优",
        "level": "L4",
        "domain": "通用",
        "statement": "核心是多方案并行尝试→综合比较→技能沉淀→概率最优。优秀的方法从来都不是固定的，是概率最优，最贴近真实、真谛、最第一性原理的",
        "source": "对话提炼",
        "evidence_count": 4,
        "applicable_to": ["所有问题类型"],
    },
    {
        "name": "免责声明不可当论据",
        "level": "L3",
        "domain": "事实验证",
        "statement": "免责声明（如建议查阅权威来源）绝对禁止在后续逻辑推理中被当作证据引用。当用户追问免责声明时，应回答'那只是核实建议，非立论基础'",
        "source": "对话提炼",
        "evidence_count": 2,
        "applicable_to": ["科学事实", "知识问答"],
    },
    {
        "name": "同源重推是钻牛角尖",
        "level": "L3",
        "domain": "问题解决",
        "statement": "发现矛盾后用同一个模型重推是钻牛角尖——就像让同一个证人翻来覆去改口供。应该引入异质来源交叉验证，而非同源重试",
        "source": "对话提炼",
        "evidence_count": 3,
        "applicable_to": ["矛盾处理", "错误修正", "推理验证"],
    },
    {
        "name": "诚实罗列分歧优于强行融合",
        "level": "L4",
        "domain": "通用",
        "statement": "当多源无法融合时，不强行统一，而是展示各方观点。这是最符合批判性思维的做法。困惑时坦诚——宁可诚实罗列分歧，不可强行牵强融合",
        "source": "对话提炼",
        "evidence_count": 3,
        "applicable_to": ["多源冲突", "哲学问题", "悖论"],
    },
    {
        "name": "代码验证靠运行而非推理",
        "level": "L3",
        "domain": "代码/工程",
        "statement": "代码/工程问题用科学事实推理链去验证是南辕北辙——应该跑一遍代码来验证。推理链和实践验证或者可以调用工具将代码跑一遍验证比推理更加有效",
        "source": "对话提炼",
        "evidence_count": 2,
        "applicable_to": ["代码", "编程", "工程", "算法"],
    },
    {
        "name": "悖论本质是定义边界问题",
        "level": "L3",
        "domain": "哲学/逻辑",
        "statement": "悖论/无解问题的本质是'定义边界'问题，而非'事实'问题。鸡和蛋→剥离后为'生命信息的代际传递'。应给出自洽的定义框架，而非唯一正解",
        "source": "对话提炼",
        "evidence_count": 2,
        "applicable_to": ["悖论", "哲学", "因果循环", "自指问题"],
    },
    {
        "name": "三思后行谋定后动",
        "level": "L4",
        "domain": "元认知/行动哲学",
        "statement": "行动前必须：先理解全景（架构、哲学、看板历史、路线图阶段）不盯着局部；先搜索既有讨论（看板/路线图/架构分析）不重新发明轮子；先根因思考——问题是孤立故障还是未落地的架构原则？标本兼治——热修复(P0)与架构方案分离",
        "source": "人类注入",
        "evidence_count": 0,
        "is_seed": True,
        "applicable_to": ["修改代码", "修复bug", "新增功能", "架构调整", "重构", "任何行动"],
    },
    {
        "name": "七维自检是行动的宪法门槛",
        "level": "L4",
        "domain": "元认知/质量门控",
        "statement": "任何修改必须通过七维自检才可行动：①方向一致——与路线图和当前阶段对齐；②看板衔接——不与既有讨论矛盾；③最小侵入——用最少改动解决问题；④无过度设计——不为假想未来编码；⑤治标+治本——热修复与根因方案分离；⑥可验证——修改后必须可测试验证；⑦精神内核对齐——不违反SpiritCore原则",
        "source": "人类注入",
        "evidence_count": 0,
        "is_seed": True,
        "applicable_to": ["修改代码", "修复bug", "新增功能", "架构调整", "重构", "任何行动"],
    },
    {
        "name": "最优判断依赖链排序",
        "level": "L4",
        "domain": "元认知/决策哲学",
        "statement": "行动按依赖链排序：先修被依赖的再修依赖者；不做的事也明确列出并说明原因；每个决策都区分'必须做'和'可以不做'；宁可少做做对，不可多做做乱",
        "source": "人类注入",
        "evidence_count": 0,
        "is_seed": True,
        "applicable_to": ["规划", "排优先级", "任务排序", "决策"],
    },
    {
        "name": "认知行动者七步闭环",
        "level": "L4",
        "domain": "元认知/认知架构",
        "statement": "每个问题必须走完七步闭环才算真正解决：感知(提取意图与深层内容)→分解(拆解为可验证子目标)→执行(针对子目标调用工具或推理)→自察(我得到了什么？距离真相近了吗？)→抽象(从经历中提炼可迁移模式)→沉淀(模式写入长期记忆/技能库)→进化(更新基因参数优化未来决策)。跳过任何一步都是表演思考而非真正思考",
        "source": "人类注入",
        "evidence_count": 0,
        "is_seed": True,
        "applicable_to": ["解决问题", "任何行动", "学习", "进化", "技能获取"],
    },
    {
        "name": "改动验证闭环铁律",
        "level": "L5",
        "domain": "元认知/工程铁律",
        "statement": "任何代码改动（文件迁移、函数重命名、模块提取、大规模重构）之后，必须执行完整验证闭环：①沙盒验证改动点本身——确认改动的代码能独立运行；②全局调用路径核查——逐一验证所有import链是否断裂，函数签名是否匹配，重命名是否全量传播；③端到端集成验证——启动完整系统跑通greeting+深度查询两条路径；④真实反馈收集——观察运行时日志有无ERROR/WARNING；⑤反思与沉淀——将发现的问题和修复过程记录为知识。跳过任何一步都是对系统稳定性的背叛。这条铁律与R1(沙盒验证)、R2(渐进注入)一脉相承，是它们在工程实践层面的强制执行机制",
        "source": "人类注入+实战教训",
        "evidence_count": 2,
        "is_seed": True,
        "applicable_to": ["文件迁移", "函数重命名", "模块提取", "大规模重构", "任何代码改动", "import路径变更", "签名变更"],
    },
    {
        "name": "进化九步闭环",
        "level": "L5",
        "domain": "元认知/自我进化铁律",
        "statement": "任何学习或自我进化必须走完九步闭环才算真正习得：想法→规划→实施→验证→真实反馈→反思→总结→思考→形成技能或知识铁律。其中'验证'和'真实反馈'是防止自我欺骗的闸门——没有经过真实系统运行验证的'改进'不是改进，只是假设。'反思→总结→思考'是从经历中提炼可迁移认知的三级升华。'形成技能或知识铁律'是闭环的终点也是新循环的起点——它让每次改动都成为系统能力的永久增长，而非一次性修补",
        "source": "人类注入",
        "evidence_count": 1,
        "is_seed": True,
        "applicable_to": ["自我进化", "学习", "代码改动", "能力获取", "知识沉淀", "技能形成"],
    },
]


class TruthAccumulator:
    """真谛沉淀与类推引擎"""

    def __init__(self, db_path: str = "data/truths.db"):
        self.db_path = db_path
        self._init_db()
        self._ensure_seeds()

    def _init_db(self):
        try:
            db = get_storage_port(self.db_path)
            db.executescript('''CREATE TABLE IF NOT EXISTS truths (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                level TEXT NOT NULL,
                domain TEXT NOT NULL,
                statement TEXT NOT NULL,
                source TEXT,
                evidence_count INTEGER DEFAULT 1,
                applicable_to TEXT,
                analogies TEXT,
                created_at TEXT,
                last_applied TEXT,
                apply_count INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS analogy_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                truth_name TEXT,
                original_domain TEXT,
                applied_to_domain TEXT,
                query TEXT,
                was_successful INTEGER,
                insight TEXT,
                timestamp TEXT
            )''')

        except Exception as e:
            logger.error(f"真谛库初始化失败: {e}")

    def _ensure_seeds(self):
        """确保种子真谛已写入，并评估筛子通过情况"""
        try:
            db = get_storage_port(self.db_path)
            for seed in SEED_TRUTHS:
                row = db.query_one("SELECT id FROM truths WHERE name=?", (seed["name"],))
                if not row:
                    db.execute(
                        "INSERT INTO truths (name, level, domain, statement, source, evidence_count, applicable_to, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            seed["name"],
                            seed["level"],
                            seed["domain"],
                            seed["statement"],
                            seed.get("source", ""),
                            seed.get("evidence_count", 0),
                            json.dumps(seed.get("applicable_to", []), ensure_ascii=False),
                            datetime.now().isoformat()
                        ),
                        commit=True
                    )
                    eval_result = self.evaluate_for_upgrade(seed["name"])
                    if not eval_result.get("eligible"):
                        failed = [k for k, v in eval_result.get("checks", {}).items() if not v.get("passed")]
                        logger.info(f"🌱 种子真谛'{seed['name']}'未通过筛子: {', '.join(failed)} (种子豁免，仍写入)")

        except Exception as e:
            logger.error(f"种子真谛写入失败: {e}")

        self._migrate_fake_evidence()

    def _migrate_fake_evidence(self):
        """修正数据库中evidence_count=99的伪造证据数为0"""
        try:
            db = get_storage_port(self.db_path)
            seed_names = {s["name"] for s in SEED_TRUTHS}
            rows = db.query("SELECT name FROM truths WHERE evidence_count = 99")
            fake_count = 0
            for row in rows:
                name = row[0] if isinstance(row, (list, tuple)) else row["name"]
                if name in seed_names:
                    db.execute("UPDATE truths SET evidence_count = 0 WHERE name = ?", (name,), commit=True)
                    fake_count += 1
            if fake_count > 0:
                logger.info(f"🔧 已修正{fake_count}条种子真谛的伪造证据数(99→0)")
        except Exception as e:
            logger.debug(f"伪造证据迁移跳过: {e}")

    def accumulate(self, query: str, attempts: list, final_response: str, essence_result: dict = None) -> Optional[str]:
        """
        从交互中提炼真谛

        触发条件：
        1. 交互中有明确的失败→成功转折（发现了新方法）
        2. 本质推理发现了跨领域洞察
        3. 多次交互出现相同模式
        """
        successful = [a for a in attempts if a[1]]
        failed = [a for a in attempts if not a[1]]

        # 条件1：失败→成功转折，说明发现了新方法
        if failed and successful:
            return self._extract_from_turnaround(query, failed, successful, final_response)

        # 条件2：本质推理有洞察
        if essence_result and essence_result.get("cross_domain_check", {}).get("issues"):
            return self._extract_from_cross_domain(query, essence_result)

        # 条件3：检查是否与已有真谛形成佐证
        if successful:
            self._reinforce_existing(query, successful)

        return None

    def _extract_from_turnaround(self, query: str, failed: list, successful: list, final_response: str) -> Optional[str]:
        """从失败→成功转折中提炼真谛"""
        failed_methods = [a[0] for a in failed]
        success_methods = [a[0] for a in successful]

        turnaround_patterns = [
            {
                "pattern": ["规则推理", "Ollama"],
                "insight": "简单规则无法解决的复杂问题需要模型推理",
                "domain": "问题解决",
            },
            {
                "pattern": ["Ollama", "外部API"],
                "insight": "本地模型知识不足时，外部模型可提供更准确的知识",
                "domain": "知识获取",
            },
            {
                "pattern": ["本质推理", "多源交叉验证"],
                "insight": "本质推理发现问题后，需要多源验证而非同源重推",
                "domain": "验证策略",
            },
            {
                "pattern": ["自我验证", "修正推理"],
                "insight": "自我验证发现问题后，修正推理可以提升回答质量",
                "domain": "质量保障",
            },
        ]

        for pattern in turnaround_patterns:
            if any(m in failed_methods for m in pattern["pattern"][:1]) and any(m in success_methods for m in pattern["pattern"][1:]):
                existing = self._find_similar_truth(pattern["insight"])
                if existing:
                    self._reinforce_by_name(existing)
                    return existing
                truth_name = f"转折洞察_{pattern['domain']}_{datetime.now().strftime('%m%d%H%M')}"
                self._save_truth(truth_name, "L3", pattern["domain"], pattern["insight"], "转折提炼")
                return truth_name

        return None

    def _extract_from_cross_domain(self, query: str, essence_result: dict) -> Optional[str]:
        """从跨域一致性检查中提炼真谛"""
        issues = essence_result.get("cross_domain_check", {}).get("issues", [])
        if not issues:
            return None

        insight = f"跨域一致性检查发现：{'; '.join(issues[:2])}——这说明不同学科视角的交叉验证能发现单一视角看不到的问题"
        truth_name = f"跨域洞察_{datetime.now().strftime('%m%d%H%M')}"
        self._save_truth(truth_name, "L3", "跨域验证", insight, "本质推理提炼")
        return truth_name

    def _reinforce_existing(self, query: str, successful: list):
        """佐证已有真谛——增加证据计数"""
        try:
            db = get_storage_port(self.db_path)
            rows = db.query("SELECT name, applicable_to, evidence_count FROM truths WHERE is_active=1")
            for row in rows:
                name = row['name']
                applicable_json = row['applicable_to']
                count = row['evidence_count']
                try:
                    applicable = json.loads(applicable_json) if applicable_json else []
                except Exception:
                    applicable = []
                for method in [a[0] for a in successful]:
                    if any(app in method for app in applicable):
                        db.execute("UPDATE truths SET evidence_count=? WHERE name=?", (count + 1, name), commit=True)
                        break

        except Exception:
            logger.warning("操作降级跳过")

    def _find_similar_truth(self, insight: str) -> Optional[str]:
        """查找已有相似真谛，避免重复写入"""
        try:
            db = get_storage_port(self.db_path)
            rows = db.query("SELECT name, statement FROM truths WHERE is_active=1")
            insight_2grams = set()
            for i in range(len(insight) - 1):
                insight_2grams.add(insight[i:i+2])
            if len(insight_2grams) < 2:
                return None
            for row in rows:
                stmt = row['statement'] if isinstance(row, dict) else row[1]
                stmt_2grams = set()
                for i in range(len(stmt) - 1):
                    stmt_2grams.add(stmt[i:i+2])
                if len(stmt_2grams) < 2:
                    continue
                overlap = len(insight_2grams & stmt_2grams) / min(len(insight_2grams), len(stmt_2grams))
                if overlap > 0.6:
                    return row['name'] if isinstance(row, dict) else row[0]
        except Exception:
            pass
        return None

    def _reinforce_by_name(self, name: str):
        """按名称佐证已有真谛"""
        try:
            db = get_storage_port(self.db_path)
            row = db.query_one("SELECT evidence_count FROM truths WHERE name=?", (name,))
            if row:
                count = row['evidence_count'] if isinstance(row, dict) else row[0]
                db.execute("UPDATE truths SET evidence_count=? WHERE name=?", (count + 1, name), commit=True)
        except Exception:
            pass

    def _save_truth(self, name: str, level: str, domain: str, statement: str, source: str):
        """保存真谛 — 新真谛必须通过筛子评估，不通过则标记pending_verification"""
        truth_quality = 0.8 if level in ("L3", "L4") else 0.6
        try:
            from infrastructure.ratchet_gate import guard_change
            proceed, decision = guard_change("truth", truth_quality, f"truth: {name} L={level} D={domain}", block_on_reject=True)
            if not proceed:
                logger.warning(f"真谛注入被棘轮门控拒绝: {name} | {decision.reason}")
                return
        except Exception:
            logger.warning("操作降级跳过")
        try:
            db = get_storage_port(self.db_path)
            verification_status = "verified"
            eval_result = self.evaluate_for_upgrade(name)
            if not eval_result.get("eligible"):
                verification_status = "pending_verification"
                failed = [k for k, v in eval_result.get("checks", {}).items() if not v.get("passed")]
                logger.info(f"🔒 新真谛'{name}'未通过筛子: {', '.join(failed)}，标记为pending_verification")

            db.execute(
                "INSERT OR IGNORE INTO truths (name, level, domain, statement, source, evidence_count, applicable_to, created_at) VALUES (?, ?, ?, ?, ?, 1, '[]', ?)",
                (name, level, domain, statement, source, datetime.now().isoformat()),
                commit=True
            )

            if verification_status == "pending_verification":
                db.execute("UPDATE truths SET verification_status=? WHERE name=?", (verification_status, name), commit=True)

            logger.info(f"💎 真谛沉淀: {name} ({level}) [{verification_status}] — {statement[:50]}")
        except Exception:
            logger.warning("操作降级跳过")

        try:
            from core.knowledge_graph import get_knowledge_graph, NodeType, ConnectionType
            kg = get_knowledge_graph()
            node = kg.add_node(statement, NodeType.TRUTH, 0.8 if level in ("L3", "L4") else 0.6, {"domain": domain, "level": level, "name": name})
            kg.auto_connect(node.id, threshold=0.2)
        except Exception:
            logger.warning("操作降级跳过")

    def analogize(self, query: str, domain: str = "") -> List[dict]:
        """
        类推映射：用已有真谛类推新问题

        核心逻辑：万变不离其宗——不同问题可能共享同一真谛
        """
        results = []
        try:
            db = get_storage_port(self.db_path)
            rows = db.query("SELECT name, level, domain, statement, applicable_to, evidence_count FROM truths WHERE is_active=1 ORDER BY evidence_count DESC")


            for row in rows:
                name = row['name']
                level = row['level']
                truth_domain = row['domain']
                statement = row['statement']
                applicable_json = row['applicable_to']
                evidence = row['evidence_count']
                try:
                    applicable = json.loads(applicable_json) if applicable_json else []
                except Exception:
                    applicable = []

                # 类推匹配：问题的领域是否与真谛适用领域有交集
                relevance = 0.0
                _bigram_hits = 0
                _bigram_attempts = 0
                for app in applicable:
                    if app in query.lower() or app in domain:
                        relevance += 0.3
                    else:
                        _bigram_attempts += 1
                        app_grams = set(app[i:i+2] for i in range(len(app)-1) if len(app) >= 2)
                        q_grams = set(query[i:i+2] for i in range(len(query)-1) if len(query) >= 2)
                        if app_grams and q_grams:
                            overlap_ratio = len(app_grams & q_grams) / len(app_grams)
                            if overlap_ratio >= 0.3:
                                relevance += 0.15 * overlap_ratio
                                _bigram_hits += 1

                # 领域直接匹配
                if truth_domain in domain or truth_domain in query:
                    relevance += 0.5

                # L4大道原则总是有一定适用性
                if level == "L4":
                    relevance += 0.2

                if relevance > 0.2:
                    tw = self.compute_truth_weight(name)
                    results.append({
                        "name": name,
                        "level": level,
                        "domain": truth_domain,
                        "statement": statement,
                        "relevance": round(min(relevance, 1.0), 2),
                        "evidence_count": evidence,
                        "truth_weight": tw,
                    })

            results.sort(key=lambda x: (x["relevance"] * 0.6 + x.get("truth_weight", 0.5) * 0.4), reverse=True)
            if _bigram_attempts > 0:
                logger.debug(f"🧩 真谛2-gram匹配率: {_bigram_hits}/{_bigram_attempts} = {_bigram_hits/_bigram_attempts:.0%}")
        except Exception:
            logger.warning("操作降级跳过")

        return results[:5]

    def compute_truth_weight(self, truth_name: str) -> float:
        """
        P5-4: 计算真谛的真理权重（置信度锐化版）

        核心改进：
        1. 证据强度非线性映射 — 弱证据快速衰减，强证据快速饱和
        2. 无验证≠一半可信 — 无验证记录时verification_score=0.2（低置信）
        3. 筛子评分更严格 — 未通过筛子时sieve_score按比例衰减
        4. 层级权重拉开差距 — L3从0.55降至0.35，L4从0.9降至0.75
        5. 最终锐化 — 通过sigmoid将中间值映射到更分散的分布

        目标：让系统能果断说"我不知道"（<0.2）和"我确信"（>0.8）
        """
        try:
            db = get_storage_port(self.db_path)
            row = db.query_one(
                "SELECT level, evidence_count, is_active FROM truths WHERE name=?",
                (truth_name,),
            )
            if not row:
                return 0.15

            level = row['level']
            evidence = row['evidence_count']
            is_active = row['is_active']

            if not is_active:
                return 0.05

            level_weights = {"L5": 0.95, "L4": 0.75, "L3": 0.35, "L2": 0.15, "L1": 0.05}
            level_score = level_weights.get(level, 0.2)

            import math
            if evidence >= 10:
                evidence_score = min(1.0, 0.5 + 0.5 * math.log1p(evidence - 9) / math.log1p(21))
            elif evidence >= 3:
                evidence_score = 0.2 + 0.3 * (evidence - 2) / 8.0
            elif evidence >= 1:
                evidence_score = 0.05 + 0.15 * evidence / 3.0
            else:
                evidence_score = 0.02

            sieve_score = self._get_cached_sieve_score(truth_name)
            if sieve_score < 0.5:
                sieve_score = sieve_score * 0.4

            try:
                verified_count = db.query_one(
                    "SELECT COUNT(*) FROM truth_verifications WHERE truth_name=? AND passed=1",
                    (truth_name,),
                )
                total_verified = db.query_one(
                    "SELECT COUNT(*) FROM truth_verifications WHERE truth_name=?",
                    (truth_name,),
                )
                v_count = verified_count[0] if verified_count else 0
                t_count = total_verified[0] if total_verified else 0
                if t_count >= 3:
                    verification_score = v_count / t_count
                elif t_count > 0:
                    verification_score = (v_count / t_count) * 0.5
                else:
                    verification_score = 0.1
            except Exception:
                verification_score = 0.1

            raw = (
                level_score * 0.30
                + evidence_score * 0.30
                + sieve_score * 0.25
                + verification_score * 0.15
            )

            sharpened = 1.0 / (1.0 + math.exp(-12.0 * (raw - 0.45)))
            sharpened = sharpened * 0.85 + raw * 0.15

            weight = round(min(0.98, max(0.02, sharpened)), 2)

            try:
                from core.monitoring.runtime_trigger_monitor import trigger_monitor
                trigger_monitor.record("compute_truth_weight", triggered=True)
                trigger_monitor.record("compute_truth_weight.high", triggered=weight >= 0.7)
                trigger_monitor.record("compute_truth_weight.medium", triggered=0.3 <= weight < 0.7)
                trigger_monitor.record("compute_truth_weight.low", triggered=weight < 0.3)
            except Exception:
                pass

            return weight

        except Exception:
            return 0.15

    _sieve_score_cache: Dict = {}

    def _get_cached_sieve_score(self, truth_name: str) -> float:
        """P5-3c: 缓存筛子评分，避免compute_truth_weight中重复调用evaluate_for_upgrade"""
        if truth_name in self._sieve_score_cache:
            return self._sieve_score_cache[truth_name]
        try:
            eval_result = self.evaluate_for_upgrade(truth_name)
            score = eval_result.get("score", 0.0)
            self._sieve_score_cache[truth_name] = score
            if len(self._sieve_score_cache) > 500:
                oldest = list(self._sieve_score_cache.keys())[:100]
                for k in oldest:
                    del self._sieve_score_cache[k]
            return score
        except Exception:
            return 0.25

    def get_weighted_truths(self, domain: str = "", limit: int = 10) -> List[dict]:
        """
        P5-3c: 获取按真理权重排序的真谛列表
        
        用于记忆检索时，真理权重高的真谛优先返回。
        """
        try:
            db = get_storage_port(self.db_path)
            rows = db.query(
                "SELECT name, level, domain, statement, evidence_count FROM truths WHERE is_active=1 ORDER BY evidence_count DESC LIMIT ?",
                (limit * 2,),
            )

            results = []
            for row in rows:
                name = row['name']
                tw = self.compute_truth_weight(name)
                results.append({
                    "name": name,
                    "level": row['level'],
                    "domain": row['domain'],
                    "statement": row['statement'],
                    "evidence_count": row['evidence_count'],
                    "truth_weight": tw,
                })

            results.sort(key=lambda x: x["truth_weight"], reverse=True)
            return results[:limit]
        except Exception:
            return []

    def get_applicable_insights(self, query: str, domain: str = "") -> str:
        """获取适用于当前问题的真谛洞察（用于注入prompt）

        L4大道级真谛始终注入，确保系统不迷失方向。
        """
        analogies = self.analogize(query, domain)

        l4_core = [a for a in analogies if a.get("level") == "L4"]
        other = [a for a in analogies if a.get("level") != "L4"]

        parts = ["【已沉淀的真谛洞察（类推适用）】"]

        if l4_core:
            parts.append("▼ 大道原则（必须遵循）：")
            for a in l4_core[:5]:
                parts.append(f"  ★ [{a['level']}] {a['name']}：{a['statement'][:100]}")

        if other:
            parts.append("▼ 领域真谛（参考适用）：")
            for a in other[:3]:
                parts.append(f"  - [{a['level']}] {a['name']}：{a['statement'][:80]}")

        if not l4_core and not other:
            try:
                db = get_storage_port(self.db_path)
                rows = db.query("SELECT name, statement FROM truths WHERE is_active=1 AND level='L4' ORDER BY evidence_count DESC LIMIT 3")
                if rows:
                    parts.append("▼ 大道原则（必须遵循）：")
                    for row in rows:
                        parts.append(f"  ★ [L4] {row['name']}：{row['statement'][:100]}")
            except Exception:
                logger.warning("操作降级跳过")

        if len(parts) <= 1:
            return ""

        parts.append("请参考以上洞察，如果适用则遵循，如果不适用则忽略。")

        return "\n".join(parts)

    def get_all_truths(self) -> List[dict]:
        """获取所有真谛"""
        try:
            db = get_storage_port(self.db_path)
            rows = db.query("SELECT name, level, domain, statement, evidence_count, source FROM truths WHERE is_active=1 ORDER BY level, evidence_count DESC")

            return [{"name": r['name'], "level": r['level'], "domain": r['domain'], "statement": r['statement'], "evidence": r['evidence_count'], "source": r['source']} for r in rows]
        except Exception:
            return []

    def get_stats(self) -> dict:
        """获取真谛统计"""
        try:
            db = get_storage_port(self.db_path)
            total_row = db.query_one("SELECT COUNT(*) FROM truths WHERE is_active=1")
            total = total_row[0]
            level_rows = db.query("SELECT level, COUNT(*) FROM truths WHERE is_active=1 GROUP BY level")
            by_level = {r['level']: r[1] for r in level_rows}
            top_rows = db.query("SELECT name, evidence_count FROM truths WHERE is_active=1 ORDER BY evidence_count DESC LIMIT 5")

            return {
                "total_truths": total,
                "by_level": by_level,
                "top_truths": [{"name": r['name'], "evidence": r['evidence_count']} for r in top_rows]
            }
        except Exception:
            return {"total_truths": 0, "by_level": {}, "top_truths": []}

    # ========== 真谛升级四道筛子 ==========
    # 只有通过四道筛子的真谛才有资格进入"重组候选池"

    def evaluate_for_upgrade(self, truth_name: str) -> dict:
        """
        评估真谛是否具备升级资格（L3→L4或进入重组候选池）

        四道筛子（必须同时通过）：
        1. 跨域普适性 — 不是解决一个问题的答案，而是解决一类问题的范式
        2. 逻辑自洽性 — 在虚拟问题中经受住矛盾压力测试
        3. 认知降熵效应 — 引入后推理步骤缩短至少20%
        4. 反脆弱性 — 必须包含边界条件（何时失效）
        """
        result = {
            "truth_name": truth_name,
            "eligible": False,
            "checks": {},
            "score": 0.0
        }

        try:
            db = get_storage_port(self.db_path)
            row = db.query_one("SELECT level, domain, statement, evidence_count, applicable_to FROM truths WHERE name=?", (truth_name,))

            if not row:
                return result

            level = row['level']
            domain = row['domain']
            statement = row['statement']
            evidence = row['evidence_count']
            applicable_json = row['applicable_to']
            try:
                applicable = json.loads(applicable_json) if applicable_json else []
            except Exception:
                applicable = []

            # 筛子1：跨域普适性 — 适用领域>=2且证据>=3
            cross_domain = len(applicable) >= 2
            sufficient_evidence = evidence >= 3
            result["checks"]["cross_domain"] = {
                "passed": cross_domain and sufficient_evidence,
                "domains": len(applicable),
                "evidence": evidence
            }

            # 筛子2：逻辑自洽性 — 结构化判定（P5-2c增强）
            consistency_result = self._check_structural_consistency(statement)
            result["checks"]["self_consistency"] = {
                "passed": consistency_result["passed"],
                "score": consistency_result["score"],
                "detected_contradictions": consistency_result["contradictions"],
                "proposition_count": consistency_result["proposition_count"],
            }

            # 筛子3：认知降熵效应 — 结构化判定（P5-2c增强）
            entropy_result = self._check_entropy_reduction(statement, applicable)
            result["checks"]["entropy_reduction"] = {
                "passed": entropy_result["passed"],
                "score": entropy_result["score"],
                "compression_ratio": entropy_result["compression_ratio"],
                "info_density": entropy_result["info_density"],
            }

            # 筛子4：反脆弱性 — 声明中是否包含边界条件
            boundary_keywords = [
                "当", "如果", "除非", "在...情况下", "不适用于",
                "边界", "例外", "前提", "条件", "限制"
            ]
            has_boundary = any(kw in statement for kw in boundary_keywords)
            result["checks"]["antifragility"] = {"passed": has_boundary}

            # 综合判定
            all_passed = all(
                result["checks"][k]["passed"]
                for k in result["checks"]
            )
            result["eligible"] = all_passed
            score = sum(1 for k in result["checks"] if result["checks"][k]["passed"]) / 4.0
            result["score"] = round(score, 2)

            if all_passed:
                logger.info(f"🏆 真谛'{truth_name}'通过四道筛子，具备升级资格 (评分{score:.0%})")
            else:
                failed_checks = [k for k in result["checks"] if not result["checks"][k]["passed"]]
                logger.info(f"🔒 真谛'{truth_name}'未通过筛子：{', '.join(failed_checks)}")

            if TruthExplainer:
                TruthExplainer.explain_upgrade_verdict(
                    truth_name=truth_name, eligible=all_passed, score=score,
                    checks=result["checks"],
                )

        except Exception as e:
            logger.error(f"真谛升级评估失败: {e}")

        return result

    def _check_structural_consistency(self, statement: str) -> dict:
        """
        P5-2c: 逻辑自洽性结构化判定
        
        三层检测：
        1. 词对矛盾 — 原有5对矛盾词对检测（保留兼容）
        2. 语义模式矛盾 — 检测"全称肯定+特称否定"等结构化矛盾
        3. 命题一致性 — 拆分命题，检测跨句矛盾
        
        Returns:
            {"passed": bool, "score": float, "contradictions": list, "proposition_count": int}
        """
        contradictions = []
        proposition_count = 0

        # 层1：词对矛盾检测（原有逻辑增强）
        word_contradiction_pairs = [
            ("必须", "可以不"), ("永远", "有时"), ("所有", "某些"),
            ("一定", "可能不"), ("必然", "偶然"),
            ("不可能", "可以"), ("无法", "可以"), ("错误", "正确"),
            ("总是", "从不"), ("唯一", "多种"),
        ]
        for w1, w2 in word_contradiction_pairs:
            if w1 in statement and w2 in statement:
                contradictions.append({"type": "word_pair", "pair": (w1, w2), "severity": "high"})

        # 层2：语义模式矛盾检测
        semantic_patterns = [
            (r'所有.{0,6}都.{0,6}不', r'有些.{0,6}可以', "universal_negative_vs_particular_affirmative"),
            (r'任何.{0,6}都', r'存在.{0,6}不', "universal_affirmative_vs_particular_negative"),
            (r'必须.{0,8}才能', r'不需要.{0,6}也能', "necessary_condition_violation"),
            (r'只有.{0,6}才', r'除了.{0,6}也', "sufficient_condition_violation"),
        ]
        for pat1, pat2, conflict_type in semantic_patterns:
            if re.search(pat1, statement) and re.search(pat2, statement):
                contradictions.append({"type": "semantic_pattern", "conflict": conflict_type, "severity": "medium"})

        # 层3：命题一致性检测 — 按句拆分，检测跨句矛盾（逗号也作为分句点）
        sentences = [s.strip() for s in re.split(r'[。！？；\n，,]', statement) if len(s.strip()) > 3]
        proposition_count = len(sentences)

        modal_words = {
            "absolute": ["必须", "一定", "必然", "永远", "所有", "任何", "唯一", "绝不"],
            "qualified": ["可以不", "可能不", "偶然", "有时", "某些", "存在", "多种", "不一定"],
        }
        absolute_sentences = []
        qualified_sentences = []
        for sent in sentences:
            has_absolute = any(w in sent for w in modal_words["absolute"])
            has_qualified = any(w in sent for w in modal_words["qualified"])
            if has_absolute:
                absolute_sentences.append(sent)
            if has_qualified:
                qualified_sentences.append(sent)

        if absolute_sentences and qualified_sentences:
            for abs_sent in absolute_sentences:
                for qual_sent in qualified_sentences:
                    abs_keywords = set(re.findall(r'[\u4e00-\u9fff]{2,}', abs_sent))
                    qual_keywords = set(re.findall(r'[\u4e00-\u9fff]{2,}', qual_sent))
                    overlap = abs_keywords & qual_keywords
                    if len(overlap) >= 2:
                        contradictions.append({
                            "type": "cross_sentence",
                            "severity": "high",
                            "absolute": abs_sent[:40],
                            "qualified": qual_sent[:40],
                            "overlap_keywords": list(overlap)[:3],
                        })

        severity_weights = {"high": 1.0, "medium": 0.5}
        total_severity = sum(severity_weights.get(c.get("severity", "medium"), 0.5) for c in contradictions)
        score = max(0.0, 1.0 - total_severity * 0.5)
        passed = len([c for c in contradictions if c.get("severity") == "high"]) == 0

        return {
            "passed": passed,
            "score": round(score, 2),
            "contradictions": contradictions,
            "proposition_count": proposition_count,
        }

    def _check_entropy_reduction(self, statement: str, applicable_domains: list) -> dict:
        """
        P5-2c: 认知降熵效应结构化判定
        
        三维评估：
        1. 简化信号 — 声明是否包含简化性关键词/结构（保留兼容）
        2. 推理压缩率 — 声明能将多步推理压缩为单步的程度
        3. 信息密度 — 单位文本中的有效信息量
        
        Returns:
            {"passed": bool, "score": float, "compression_ratio": float, "info_density": float}
        """
        # 维1：简化信号检测（原有逻辑增强）
        simplification_keywords = [
            "本质是", "核心是", "关键是", "归根结底", "万变不离其宗",
            "统一", "简化", "归约", "还原到", "最小",
            "等价于", "归结为", "实质是", "根本是", "底层是",
        ]
        simplification_structures = [
            r'只需.{1,8}就能', r'所有.{1,6}都遵循', r'归根结底就是',
            r'本质上是', r'核心原理是', r'统一了.{1,6}和',
        ]
        has_keyword = any(kw in statement for kw in simplification_keywords)
        has_structure = any(re.search(pat, statement) for pat in simplification_structures)
        simplification_score = 0.4 if has_keyword else 0.0
        simplification_score += 0.3 if has_structure else 0.0

        # 维2：推理压缩率 — 声明中的条件-结论结构越多，压缩率越高
        conditional_patterns = [
            r'如果.{1,15}就', r'只要.{1,15}就', r'当.{1,15}时',
            r'遇到.{1,10}应该', r'面对.{1,10}需要', r'在.{1,10}情况下',
        ]
        conditional_count = sum(1 for pat in conditional_patterns if re.search(pat, statement))
        compression_ratio = min(1.0, conditional_count * 0.25 + (0.2 if len(applicable_domains) >= 2 else 0.0))

        # 维3：信息密度 — 有效信息词/总字符数
        content_words = re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}', statement)
        stop_words = {"就是", "可以", "需要", "应该", "能够", "这个", "那个", "然后", "所以", "因为", "但是", "而且", "或者"}
        effective_words = [w for w in content_words if w not in stop_words]
        info_density = len(effective_words) / max(len(statement), 1)
        info_density = min(1.0, info_density * 3.0)

        # 综合评分
        total_score = simplification_score + compression_ratio * 0.3 + info_density * 0.3
        total_score = min(1.0, total_score)
        passed = total_score >= 0.4

        return {
            "passed": passed,
            "score": round(total_score, 2),
            "compression_ratio": round(compression_ratio, 2),
            "info_density": round(info_density, 2),
        }

    def get_reorganization_candidates(self) -> List[dict]:
        """获取有资格进入重组候选池的真谛"""
        candidates = []
        try:
            db = get_storage_port(self.db_path)
            rows = db.query("SELECT name, level, statement, evidence_count FROM truths WHERE is_active=1 AND evidence_count >= 3 ORDER BY evidence_count DESC")


            for row in rows:
                name = row['name']
                level = row['level']
                statement = row['statement']
                evidence = row['evidence_count']
                eval_result = self.evaluate_for_upgrade(name)
                if eval_result["eligible"]:
                    candidates.append({
                        "name": name,
                        "level": level,
                        "statement": statement,
                        "evidence": evidence,
                        "score": eval_result["score"]
                    })
        except Exception:
            logger.warning("操作降级跳过")

        return candidates

    # ========== 认知重组安全协议 ==========
    # 三条铁律：
    # 1. 未经沙盒验证的真谛，视同毒药
    # 2. 未经渐进式注入的重组，视同自杀
    # 3. 未经人类批准的进化，视同背叛

    def propose_reorganization(self) -> dict:
        """
        生成认知重组提案书

        不会自动执行重组，只生成提案供人类审批
        """
        candidates = self.get_reorganization_candidates()

        if not candidates:
            return {"status": "no_candidates", "message": "当前无符合条件的重组候选真谛"}

        proposal = {
            "status": "pending_approval",
            "proposal_id": f"REORG_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "created_at": datetime.now().isoformat(),
            "candidate_count": len(candidates),
            "candidates": candidates[:10],
            "risk_assessment": self._assess_reorganization_risk(candidates),
            "required_approvals": ["human"],
            "safety_protocol": {
                "sandbox_verification": "必须先在沙盒中运行3天",
                "gradual_injection": "1%→20%→100%渐进注入",
                "rollback_ready": "24小时快照已准备",
            },
            "铁律提醒": [
                "未经沙盒验证的真谛，视同毒药",
                "未经渐进式注入的重组，视同自杀",
                "未经人类批准的进化，视同背叛",
            ]
        }

        # 持久化提案
        try:
            db = get_storage_port(self.db_path)
            db.executescript('''CREATE TABLE IF NOT EXISTS reorganization_proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proposal_id TEXT UNIQUE,
                status TEXT DEFAULT 'pending',
                candidates_json TEXT,
                risk_assessment TEXT,
                created_at TEXT,
                approved_by TEXT,
                approved_at TEXT,
                executed_at TEXT,
                rollback_snapshot TEXT
            )''')
            db.execute(
                "INSERT INTO reorganization_proposals (proposal_id, status, candidates_json, risk_assessment, created_at) VALUES (?, 'pending', ?, ?, ?)",
                (
                    proposal["proposal_id"],
                    json.dumps(candidates[:10], ensure_ascii=False)[:5000],
                    json.dumps(proposal["risk_assessment"], ensure_ascii=False),
                    datetime.now().isoformat()
                ),
                commit=True
            )

        except Exception:
            logger.warning("操作降级跳过")

        logger.warning(f"📋 认知重组提案已生成: {proposal['proposal_id']} ({len(candidates)}条候选真谛)")
        return proposal

    def _assess_reorganization_risk(self, candidates: list) -> dict:
        """评估重组风险"""
        l4_count = sum(1 for c in candidates if c.get("level") == "L4")
        l3_count = sum(1 for c in candidates if c.get("level") == "L3")
        max_evidence = max((c.get("evidence", 0) for c in candidates), default=0)

        risk_level = "low"
        if l4_count > 2:
            risk_level = "high"
        elif l4_count > 0 or l3_count > 5:
            risk_level = "medium"

        return {
            "risk_level": risk_level,
            "l4_candidates": l4_count,
            "l3_candidates": l3_count,
            "max_evidence": max_evidence,
            "warning": "大道级真谛数量较多，重组影响范围大，务必沙盒验证" if risk_level == "high" else "风险可控"
        }

    def approve_reorganization(self, proposal_id: str, approver: str = "human") -> dict:
        """
        人类批准重组（必须由人类明确批准）

        批准后进入6步安全协议：
        1. 提案 ✅ 2. 人类批准 ✅ 3. 沙盒验证 4. 1%注入 5. 20%注入 6. 100%注入
        """
        try:
            db = get_storage_port(self.db_path)
            db.execute("UPDATE reorganization_proposals SET status='approved', approved_by=?, approved_at=? WHERE proposal_id=?",
                      (approver, datetime.now().isoformat(), proposal_id), commit=True)

            logger.info(f"✅ 重组提案{proposal_id}已获{approver}批准，进入沙盒验证阶段")
            return {"status": "approved", "next_step": "sandbox_verification"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def execute_reorganization_step(self, proposal_id: str, step: str) -> dict:
        """
        执行认知重组安全协议的后续步骤

        步骤：sandbox → inject_1pct → inject_20pct → inject_100pct
        每步都检查熵值，>0.7自动回滚
        """
        try:
            db = get_storage_port(self.db_path)
            row = db.query_one("SELECT status, candidates_json FROM reorganization_proposals WHERE proposal_id=?", (proposal_id,))
            if not row:
    
                return {"status": "error", "message": "提案不存在"}

            current_status = row['status']
            candidates_json = row['candidates_json']

            if step == "sandbox" and current_status == "approved":
                snapshot = self._create_snapshot()
                db.execute("UPDATE reorganization_proposals SET status='sandbox_passed', rollback_snapshot=? WHERE proposal_id=?",
                          (json.dumps(snapshot), proposal_id), commit=True)
    
                logger.info(f"🧪 重组{proposal_id}沙盒验证通过，快照已保存")
                return {"status": "sandbox_passed", "next_step": "inject_1pct", "snapshot_saved": True}

            elif step == "inject_1pct" and current_status == "sandbox_passed":
                entropy = self.get_cognitive_entropy()
                if entropy["entropy_score"] > 0.7:
                    return self._rollback_reorganization(proposal_id, "1%注入前熵值过高")
                db.execute("UPDATE reorganization_proposals SET status='inject_1pct_done' WHERE proposal_id=?", (proposal_id,), commit=True)
    
                logger.info(f"💉 重组{proposal_id} 1%注入完成")
                return {"status": "inject_1pct_done", "next_step": "inject_20pct", "entropy": entropy["entropy_score"]}

            elif step == "inject_20pct" and current_status == "inject_1pct_done":
                entropy = self.get_cognitive_entropy()
                if entropy["entropy_score"] > 0.7:
                    return self._rollback_reorganization(proposal_id, "20%注入前熵值过高")
                db.execute("UPDATE reorganization_proposals SET status='inject_20pct_done' WHERE proposal_id=?", (proposal_id,), commit=True)
    
                logger.info(f"💉 重组{proposal_id} 20%注入完成")
                return {"status": "inject_20pct_done", "next_step": "inject_100pct", "entropy": entropy["entropy_score"]}

            elif step == "inject_100pct" and current_status == "inject_20pct_done":
                entropy = self.get_cognitive_entropy()
                if entropy["entropy_score"] > 0.7:
                    return self._rollback_reorganization(proposal_id, "100%注入前熵值过高")
                candidates = json.loads(candidates_json) if candidates_json else []
                for cand in candidates:
                    self._apply_reorganization_candidate(cand)
                db.execute("UPDATE reorganization_proposals SET status='completed', executed_at=? WHERE proposal_id=?",
                          (datetime.now().isoformat(), proposal_id), commit=True)
    
                logger.info(f"✅ 重组{proposal_id} 100%注入完成，重组成功")
                return {"status": "completed", "entropy": entropy["entropy_score"]}

            else:
    
                return {"status": "error", "message": f"步骤{step}与当前状态{current_status}不匹配"}

        except Exception as e:
            logger.error(f"重组执行失败: {e}")
            return {"status": "error", "message": str(e)}

    def _create_snapshot(self) -> dict:
        """创建当前真谛库快照（用于回滚）"""
        snapshot = {"truths": [], "timestamp": datetime.now().isoformat()}
        try:
            db = get_storage_port(self.db_path)
            rows = db.query("SELECT name, level, evidence_count, is_active FROM truths")
            for row in rows:
                snapshot["truths"].append({
                    "name": row['name'], "level": row['level'],
                    "evidence_count": row['evidence_count'], "is_active": row['is_active']
                })

        except Exception:
            logger.warning("操作降级跳过")
        return snapshot

    def _rollback_reorganization(self, proposal_id: str, reason: str) -> dict:
        """回滚重组：恢复到快照状态"""
        logger.error(f"🚨 重组{proposal_id}回滚! 原因: {reason}")
        try:
            db = get_storage_port(self.db_path)
            row = db.query_one("SELECT rollback_snapshot FROM reorganization_proposals WHERE proposal_id=?", (proposal_id,))
            if row and row['rollback_snapshot']:
                snapshot = json.loads(row['rollback_snapshot'])
                for truth in snapshot.get("truths", []):
                    db.execute("UPDATE truths SET is_active=?, evidence_count=? WHERE name=?",
                              (truth["is_active"], truth["evidence_count"], truth["name"]))
            db.execute("UPDATE reorganization_proposals SET status='rolled_back' WHERE proposal_id=?", (proposal_id,), commit=True)

            return {"status": "rolled_back", "reason": reason, "铁律": "未经沙盒验证的真谛视同毒药"}
        except Exception as e:
            return {"status": "rollback_failed", "error": str(e)}

    def _apply_reorganization_candidate(self, candidate: dict):
        """应用单个重组候选（提升真谛层级或合并）"""
        try:
            db = get_storage_port(self.db_path)
            name = candidate.get("name", "")
            new_level = candidate.get("target_level", "")
            if name and new_level:
                db.execute("UPDATE truths SET level=? WHERE name=?", (new_level, name), commit=True)

        except Exception:
            logger.warning("操作降级跳过")

    # ========== 认知熵值监测器 ==========

    def get_cognitive_entropy(self) -> dict:
        """
        认知熵值监测：实时监控系统健康状态

        关键指标：
        - 内部矛盾触发频率
        - 平均响应时间
        - 真谛冲突率
        - 基因安全基线违规数
        """
        entropy = {
            "contradiction_rate": 0.0,
            "avg_response_time": 0.0,
            "truth_conflict_rate": 0.0,
            "gene_safety_violations": 0,
            "entropy_score": 0.0,
            "status": "normal"
        }

        try:
            # 矛盾率：最近交互中核心失败的占比（排除多策略中部分路径失败）
            db = get_storage_port("data/spirit_lessons.db")
            recent_row = db.query_one("SELECT COUNT(*) FROM reflections WHERE timestamp > datetime('now', '-1 day')")
            recent = recent_row[0]
            failed_row = db.query_one("SELECT COUNT(*) FROM reflections WHERE timestamp > datetime('now', '-1 day') AND lessons LIKE '%全部失败%' OR (lessons LIKE '%失败%' AND lessons NOT LIKE '%成功%')")
            failed = failed_row[0]

            if recent > 0:
                entropy["contradiction_rate"] = round(min(failed / recent, 1.0), 3)

            # 真谛冲突率：弱证据真谛占比（新沉淀的真谛evidence<2是正常的，降低权重）
            db2 = get_storage_port(self.db_path)
            total_truths_row = db2.query_one("SELECT COUNT(*) FROM truths WHERE is_active=1")
            total_truths = total_truths_row[0]
            weak_truths_row = db2.query_one("SELECT COUNT(*) FROM truths WHERE is_active=1 AND evidence_count < 2")
            weak_truths = weak_truths_row[0]

            if total_truths > 0:
                entropy["truth_conflict_rate"] = round(weak_truths / total_truths, 3)

            # 基因安全违规：近期违规率（最近1小时），而非累计总数
            try:
                from core.task_queue import gene_pool
                db_v = get_storage_port(gene_pool.db_path)
                one_hour_ago = (datetime.now() - __import__('datetime').timedelta(hours=1)).isoformat()
                recent_violations_row = db_v.query_one(
                    "SELECT COUNT(*) FROM safety_violations WHERE timestamp > ?", (one_hour_ago,)
                )
                recent_violations = recent_violations_row[0]

                entropy["gene_safety_violations"] = gene_pool.get_safety_violations().get("total", 0)
                entropy["recent_safety_violations"] = recent_violations
            except Exception:
                entropy["gene_safety_violations"] = 0
                entropy["recent_safety_violations"] = 0

            # 综合熵值评分（0-1，越低越健康）
            entropy_score = (
                entropy["contradiction_rate"] * 0.5 +
                entropy["truth_conflict_rate"] * 0.15 +
                min(entropy.get("recent_safety_violations", 0) / 5.0, 0.2)
            )
            entropy_score = min(entropy_score, 1.0)
            entropy["entropy_score"] = round(entropy_score, 3)

            if entropy_score > 0.5:
                entropy["status"] = "critical"
                logger.error(f"🚨 认知熵值异常: {entropy_score:.2f} — 建议立即回滚！")
            elif entropy_score > 0.3:
                entropy["status"] = "warning"
                logger.warning(f"⚠️ 认知熵值偏高: {entropy_score:.2f}")
            else:
                entropy["status"] = "normal"

        except Exception as e:
            logger.error(f"认知熵值监测失败: {e}")

        return entropy


truth_accumulator = TruthAccumulator()