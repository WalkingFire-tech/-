"""
本质推理器 (Essence Reasoner) - 追求本源、证自洽、跨域一致性

核心理念：
1. 第一性原理推理 — 从最基本的事实出发，一步步推导，不允许跳步
2. 自洽性验证 — 结论不能与前提矛盾，同一回答内部不能有逻辑冲突
3. 跨域一致性 — 无论从哪个学科视角看，结论都不应有悖论
4. 事实交叉校验 — 关键事实声明必须经过多源验证
5. 反向归谬 — 尝试推翻自己的结论，如果推翻不了才站得住

推理流程：
  原始回答 → 事实提取 → 第一性原理重推 → 自洽性检查 → 跨域一致性 → 反向归谬 → 最终结论
"""

import re
import json
import sqlite3
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger
from datetime import datetime


class EssenceReasoner:
    """本质推理器 — 确保回答从本质出发、逻辑自洽、跨域无悖"""

    SCIENCE_DOMAINS = {
        "天文": ["恒星", "行星", "星系", "黑洞", "星云", "银河", "太阳系", "轨道", "光年", "火星", "木星", "土星", "卫星", "彗星"],
        "物理": ["力", "能量", "质量", "速度", "光速", "量子", "相对论", "电磁", "散射", "折射", "波长", "频率", "温度", "压力", "密度", "加速度", "光", "光子", "光谱", "波动", "蓝色", "颜色", "大气", "引力", "宇宙", "涨落", "不确定性", "粒子", "场", "真空", "湮灭", "虚粒子", "暴胀", "大爆炸", "核聚变"],
        "化学": ["原子", "分子", "元素", "化合物", "反应", "化学键", "离子", "氧化", "还原", "催化"],
        "生物": ["细胞", "基因", "DNA", "RNA", "蛋白质", "进化", "物种", "光合作用", "病毒", "疫苗"],
        "数学": ["证明", "定理", "公式", "函数", "方程", "概率", "统计", "几何", "代数", "微积分"],
        "医学": ["疾病", "症状", "治疗", "药物", "诊断", "手术", "免疫", "感染", "临床"],
    }

    LOGICAL_FALLACIES = {
        "循环论证": r"(因为.*所以.*因此.*因为|A因为B.*B因为A)",
        "以偏概全": r"(所有\S+都|每个\S+总是|永远\S+不会)",
        "因果倒置": r"(因为.*结果.*导致.*原因)",
        "自相矛盾": r"(既是.*又不是|既.*又.*但.*不)",
        "滑坡谬误": r"(如果.*那么.*最终.*导致.*灾难)",
    }

    def __init__(self):
        self._init_db()

    def _init_db(self):
        try:
            conn = sqlite3.connect("data/essence_reasoning.db")
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reasoning_chains (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT,
                    original_response TEXT,
                    facts_extracted TEXT,
                    reasoning_chain TEXT,
                    consistency_check TEXT,
                    final_verdict TEXT,
                    confidence REAL,
                    timestamp TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fact_verifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fact_claim TEXT,
                    domain TEXT,
                    verified BOOLEAN,
                    evidence TEXT,
                    source TEXT,
                    timestamp TEXT
                )
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"本质推理器数据库初始化失败: {e}")

    HISTORY_PHILOSOPHY_KEYWORDS = [
        "古文明", "文明", "历史", "朝代", "帝国", "王朝", "古代", "近代",
        "考古", "遗址", "文物", "文献", "史料", "编年",
        "哲学", "思想", "意义", "价值", "伦理", "道德", "存在", "本质",
        "思辨", "辩证", "逻辑", "理性", "感性", "意识", "认知",
        "文化", "传统", "传承", "民俗", "信仰", "宗教", "神话",
        "社会", "制度", "政治", "经济", "法律", "治理", "组织",
        "人类", "人性", "心理", "行为", "动机", "进步", "发展",
        "演化", "变迁", "兴衰", "崩溃", "复兴",
    ]

    EDUCATION_KEYWORDS = [
        "建议", "暑假", "寒假", "学习计划", "复习", "预习", "升学",
        "中考", "高考", "课程", "作业", "考试", "成绩", "教育",
        "教学", "老师", "学生", "家长", "孩子", "小学", "初中", "高中",
    ]

    def reason(self, query: str, response: str, conversation_context: str = "") -> Dict[str, Any]:
        """
        核心推理流程：对回答进行本质推理与自洽验证
        """
        result = {
            "passed": True,
            "confidence": 0.8,
            "facts": [],
            "reasoning_chain": [],
            "consistency_issues": [],
            "cross_domain_check": {},
            "refutation_result": {},
            "web_verification": {},
            "enhanced_response": response,
            "verdict": "通过"
        }

        if not response or len(response) < 20:
            result["passed"] = False
            result["verdict"] = "回答过短，无法推理"
            return result

        is_history_philosophy = any(kw in query for kw in self.HISTORY_PHILOSOPHY_KEYWORDS)
        is_education = any(kw in query for kw in self.EDUCATION_KEYWORDS)
        self._query_is_humanities = is_history_philosophy or is_education

        paradox_patterns = [
            "鸡和蛋", "先有鸡", "先有蛋", "悖论", "矛盾", "无解",
            "无穷", "无限", "循环论证", "自我指涉", "说谎者",
            "祖父悖论", "薛定谔", "不可判定"
        ]
        is_paradox = any(p in query.lower() for p in paradox_patterns)

        engineering_patterns = [
            "esp32", "stm32", "arduino", "单片机", "mcu", "嵌入式",
            "电路", "电压", "电流", "供电", "引脚", "gpio", "串口",
            "焊接", "杜邦线", "万用表", "示波器", "电容", "电阻",
            "上拉", "下拉", "复位", "烧录", "固件", "波特率",
            "不工作", "不启动", "无法启动", "无法工作", "不亮",
            "硬件", "pcb", "原理图", "芯片", "模块", "传感器"
        ]
        is_engineering = any(p in query.lower() for p in engineering_patterns)

        facts = self._extract_facts(response)
        result["facts"] = facts

        chain = self._first_principles_reasoning(query, facts, response)
        result["reasoning_chain"] = chain

        consistency = self._check_consistency(query, response, facts, chain, is_paradox or is_engineering)
        result["consistency_issues"] = consistency["issues"]

        if is_paradox:
            result["passed"] = True
            result["confidence"] = 0.7
            result["verdict"] = "悖论/定义边界问题，不适用基本原理追溯"
            self._save_reasoning(query, response, result)
            return result

        if is_engineering:
            result["passed"] = True
            result["confidence"] = 0.75
            result["verdict"] = "工程/硬件问题，适用实验验证而非基本原理追溯"
            self._save_reasoning(query, response, result)
            return result

        cross_domain = self._cross_domain_consistency(query, response, facts)
        result["cross_domain_check"] = cross_domain

        refutation = self._refutation_test(query, response, facts)
        result["refutation_result"] = refutation

        web_result = self._web_fact_check(query, facts)
        result["web_verification"] = web_result

        # 综合判定
        all_issues = consistency["issues"] + cross_domain.get("issues", [])
        if refutation.get("refuted"):
            all_issues.append(f"反向归谬发现：{refutation.get('reason', '')}")
        if web_result.get("contradictions"):
            for c in web_result["contradictions"][:2]:
                all_issues.append(f"网络校验冲突：{c}")

        if all_issues:
            result["passed"] = False
            result["confidence"] = max(0.1, 0.8 - len(all_issues) * 0.15)
            result["verdict"] = f"发现{len(all_issues)}个问题：{'；'.join(all_issues[:3])}"

            # 尝试增强回答
            enhanced = self._enhance_response(query, response, all_issues, chain)
            if enhanced and len(enhanced) > len(response):
                result["enhanced_response"] = enhanced
        else:
            result["confidence"] = 0.9
            result["verdict"] = "推理自洽，跨域无悖"

        # 持久化
        self._save_reasoning(query, response, result)

        return result

    CODE_INDICATORS = [
        "代码", "编程", "函数", "程序", "算法", "单片机", "stm32", "arduino",
        "嵌入式", "写一段", "实现", "编译", "调试", "运行", "#include",
        "int ", "void ", "return ", "for(", "while(", "if(",
        "uint8_t", "uint16_t", "uint32_t", "HAL_", "GPIO"
    ]

    def _extract_facts(self, response: str) -> List[Dict]:
        """从回答中提取事实声明（代码内容不提取）"""
        # 代码块检测：如果回答主要是代码，跳过事实提取
        code_block_count = response.count("```") // 2
        code_line_count = sum(1 for line in response.split("\n") if line.strip().startswith(("#", "//", "/*", "*/", "int ", "void ", "return ", "uint", "HAL_")))
        total_lines = max(len(response.split("\n")), 1)
        if code_block_count >= 1 or code_line_count / total_lines > 0.4:
            return []

        facts = []
        sentences = re.split(r'[。！？\n]', response)
        for i, sent in enumerate(sentences):
            sent = sent.strip()
            if not sent or len(sent) < 5:
                continue

            is_factual = False
            domain = "通用"

            skip_science_domain = getattr(self, '_query_is_humanities', False)

            best_domain = None
            best_count = 0
            domain_priority = {"物理": 1, "化学": 2, "生物": 3, "天文": 4, "数学": 5, "医学": 6, "通用": 99}
            if not skip_science_domain:
                for dom, keywords in self.SCIENCE_DOMAINS.items():
                    count = sum(1 for kw in keywords if kw in sent)
                    if count > best_count or (count == best_count and count > 0 and domain_priority.get(dom, 99) < domain_priority.get(best_domain, 99)):
                        best_count = count
                        best_domain = dom
                if best_domain and best_count > 0:
                    is_factual = True
                    domain = best_domain

            factual_patterns = [
                r"是(\w+)的", r"因为.*所以", r"由于.*导致",
                r"(\d+\.?\d*)%", r"(\d+\.?\d*)倍", r"大约(\d+)",
                r"由(\w+)组成", r"被称为", r"属于", r"产生",
            ]
            if not is_factual:
                for pat in factual_patterns:
                    if re.search(pat, sent):
                        is_factual = True
                        break

            if is_factual:
                facts.append({
                    "index": i,
                    "statement": sent,
                    "domain": domain,
                    "type": "scientific" if domain != "通用" else "factual"
                })

        return facts

    def _first_principles_reasoning(self, query: str, facts: List[Dict], response: str) -> List[Dict]:
        """
        第一性原理推理：从基本事实出发，逐步推导

        检查回答中的每个事实声明是否可以追溯到基本原理
        """
        chain = []

        for fact in facts:
            stmt = fact["statement"]
            domain = fact["domain"]

            step = {
                "fact": stmt[:100],
                "domain": domain,
                "traceable": False,
                "reasoning": "",
                "gap": ""
            }

            known_truths = self._get_known_truths(domain)
            matched = False
            for truth in known_truths:
                if any(kw in stmt for kw in truth.get("keywords", [])):
                    step["traceable"] = True
                    step["reasoning"] = truth.get("reasoning", "")
                    matched = True
                    break

            if not matched:
                if domain == "通用":
                    step["traceable"] = False
                    step["gap"] = "无法从通用基本原理直接追溯，需要进一步验证"
                else:
                    step["traceable"] = None
                    step["gap"] = f"已知真理库未覆盖此观点，建议多源交叉验证"

            chain.append(step)

        return chain

    def _get_known_truths(self, domain: str) -> List[Dict]:
        """获取已知的基本真理（硬编码核心知识 + 从知识库检索）"""
        base_truths = {
            "天文": [
                {"keywords": ["地球", "蓝"], "reasoning": "地球看起来是蓝色的，因为大气层中氮气和氧气分子对短波长光（蓝光）的瑞利散射", "verified": True},
                {"keywords": ["火星", "红"], "reasoning": "火星看起来是红色的，因为表面富含氧化铁（铁锈）", "verified": True},
                {"keywords": ["恒星", "发光"], "reasoning": "恒星通过核聚变反应产生能量并发光", "verified": True},
                {"keywords": ["行星", "发光"], "reasoning": "行星不自行发光，靠反射恒星的光", "verified": True},
                {"keywords": ["引力", "轨道"], "reasoning": "天体轨道运动由万有引力决定", "verified": True},
            ],
            "物理": [
                {"keywords": ["散射", "蓝"], "reasoning": "瑞利散射：短波长光比长波长光散射更强，所以天空是蓝色的", "verified": True},
                {"keywords": ["光速", "不变"], "reasoning": "真空中光速约为3×10^8 m/s，是物理学基本常数", "verified": True},
                {"keywords": ["能量", "守恒"], "reasoning": "能量守恒定律：孤立系统总能量不变", "verified": True},
                {"keywords": ["折射"], "reasoning": "光从一种介质进入另一种介质时方向改变，由折射定律描述", "verified": True},
            ],
            "化学": [
                {"keywords": ["水", "组成"], "reasoning": "水由氢和氧组成(H₂O)", "verified": True},
                {"keywords": ["原子", "结构"], "reasoning": "原子由原子核（质子+中子）和电子组成", "verified": True},
            ],
            "生物": [
                {"keywords": ["光合作用"], "reasoning": "植物利用光能将CO₂和H₂O转化为有机物和O₂", "verified": True},
                {"keywords": ["DNA", "遗传"], "reasoning": "DNA是遗传信息的载体，通过碱基配对进行复制", "verified": True},
            ],
        }

        truths = base_truths.get(domain, [])

        try:
            conn = sqlite3.connect("data/knowledge_store.db")
            cursor = conn.cursor()
            cursor.execute("SELECT content FROM knowledge WHERE content LIKE ? LIMIT 5", (f"%{domain}%",))
            rows = cursor.fetchall()
            conn.close()
            for row in rows:
                if row[0] and len(row[0]) > 20:
                    truths.append({"keywords": row[0][:10].split(), "reasoning": row[0][:200], "verified": True})
        except:
            pass

        return truths

    def _check_consistency(self, query: str, response: str, facts: List[Dict], chain: List[Dict], is_paradox: bool = False) -> Dict:
        """自洽性检查：回答内部不能有逻辑冲突"""
        issues = []

        is_humanities = getattr(self, '_query_is_humanities', False)

        if not is_humanities:
            for fallacy_name, pattern in self.LOGICAL_FALLACIES.items():
                if re.search(pattern, response):
                    issues.append(f"检测到可能的{fallacy_name}")

        # 检查2：事实声明之间的矛盾
        fact_statements = [f["statement"] for f in facts]
        for i, f1 in enumerate(fact_statements):
            for j, f2 in enumerate(fact_statements):
                if i >= j:
                    continue
                contradiction = self._detect_contradiction(f1, f2)
                if contradiction:
                    issues.append(f"事实矛盾：'{f1[:30]}...' 与 '{f2[:30]}...' {contradiction}")

        # 检查3：推理链断裂（悖论问题跳过此检查）
        if not is_paradox:
            untraceable = [s for s in chain if s.get("traceable") is False and s.get("domain") != "通用"]
            for s in untraceable:
                if s.get("gap"):
                    issues.append(f"推理链断裂：{s['gap'][:60]}")

        # 检查4：因果链完整性
        if any(kw in query for kw in ["为什么", "原因", "为什么"]):
            has_causal = any(kw in response for kw in ["因为", "由于", "原因是", "导致", "使得"])
            if not has_causal:
                issues.append("因果问题缺少因果链解释")

        return {"issues": issues, "fact_count": len(facts), "chain_length": len(chain)}

    def _detect_contradiction(self, s1: str, s2: str) -> str:
        """检测两个陈述之间的矛盾"""
        contradiction_patterns = [
            (r"不是", r"是"),
            (r"不能", r"能"),
            (r"没有", r"有"),
            (r"不会", r"会"),
            (r"不可能", r"可能"),
            (r"增加", r"减少"),
            (r"上升", r"下降"),
            (r"加速", r"减速"),
        ]
        rhetorical_patterns = ["而是", "而是要", "而是应该", "而是需要", "而是先"]
        for rp in rhetorical_patterns:
            if rp in s1 or rp in s2:
                return ""
        def _same_subject(st1: str, st2: str) -> bool:
            subjects1 = set()
            for marker in ["的", "是", "有", "在", "能", "会", "可以"]:
                idx = st1.find(marker)
                if idx > 0:
                    subjects1.add(st1[:idx].strip()[-4:])
            for marker in ["的", "是", "有", "在", "能", "会", "可以"]:
                idx = st2.find(marker)
                if idx > 0:
                    subj = st2[:idx].strip()[-4:]
                    for s in subjects1:
                        if s and subj and (s in subj or subj in s):
                            return True
            return False

        for neg, pos in contradiction_patterns:
            if neg in s1 and pos in s2:
                if _same_subject(s1, s2):
                    return f"否定词冲突（{neg} vs {pos}）"
            if pos in s1 and neg in s2:
                if _same_subject(s1, s2):
                    return f"否定词冲突（{pos} vs {neg}）"
        return ""

    def _cross_domain_consistency(self, query: str, response: str, facts: List[Dict]) -> Dict:
        """
        跨域一致性检查：从不同学科视角审视同一结论

        核心逻辑：如果一个结论在A学科成立但在B学科不成立，说明结论有误
        """
        result = {"domains_found": [], "issues": [], "consistent": True}

        domains_in_response = set()
        for fact in facts:
            if fact["domain"] != "通用":
                domains_in_response.add(fact["domain"])

        if len(domains_in_response) < 2:
            result["domains_found"] = list(domains_in_response)
            return result

        result["domains_found"] = list(domains_in_response)

        # 跨域一致性规则
        cross_rules = [
            {
                "domains": ["天文", "物理"],
                "rule": "天文学现象必须符合物理定律",
                "check": lambda q, r: self._check_astro_physics(q, r)
            },
            {
                "domains": ["化学", "物理"],
                "rule": "化学反应必须遵循能量守恒",
                "check": lambda q, r: self._check_chem_physics(q, r)
            },
            {
                "domains": ["生物", "化学"],
                "rule": "生物过程必须有化学机制支撑",
                "check": lambda q, r: self._check_bio_chem(q, r)
            },
        ]

        for rule in cross_rules:
            if set(rule["domains"]).issubset(domains_in_response):
                issue = rule["check"](query, response)
                if issue:
                    result["issues"].append(f"跨域冲突[{'+'.join(rule['domains'])}]：{issue}")
                    result["consistent"] = False

        return result

    def _check_astro_physics(self, query: str, response: str) -> str:
        """天文-物理跨域检查"""
        if "散射" in response and ("火星" in response or "木星" in response or "土星" in response):
            if "大气" not in response and "大气层" not in response:
                return "提到行星散射但未说明大气条件——只有有大气层的天体才有瑞利散射，火星大气极薄（仅地球1%），木星/土星大气成分与地球完全不同（氢氦为主），不能简单套用地球的蓝色散射机制"

        if "光速" in response and ("超光速" in response or "超过光速" in response):
            return "声称超光速与狭义相对论矛盾"

        return ""

    def _check_chem_physics(self, query: str, response: str) -> str:
        """化学-物理跨域检查"""
        if "永动机" in response and ("可以" in response or "能够" in response or "实现" in response):
            return "永动机违反热力学第二定律"

        return ""

    def _check_bio_chem(self, query: str, response: str) -> str:
        """生物-化学跨域检查"""
        if "DNA" in response and "蛋白质" in response:
            if "氨基酸" not in response and "核苷酸" not in response:
                return "提到DNA和蛋白质但未涉及基本化学组成（核苷酸/氨基酸）"

        return ""

    def _refutation_test(self, query: str, response: str, facts: List[Dict]) -> Dict:
        """
        反向归谬：尝试推翻自己的结论

        如果能找到反例或逻辑漏洞，说明结论不够坚实
        """
        result = {"refuted": False, "reason": "", "counter_examples": []}

        for fact in facts:
            stmt = fact["statement"]
            domain = fact["domain"]

            counter = self._find_counter_example(stmt, domain)
            if counter:
                result["refuted"] = True
                result["counter_examples"].append(counter)
                if not result["reason"]:
                    result["reason"] = counter

        absolute_claims = re.findall(r"(所有|全部|任何|永远|从不|一定|必然|绝对|不可能)\S*(?:都|是|会|能)", response)
        if absolute_claims:
            for claim in absolute_claims[:2]:
                result["counter_examples"].append(f"绝对化声明「{claim}...」可能存在例外情况")

        return result

    def _find_counter_example(self, statement: str, domain: str) -> str:
        """为事实声明寻找反例"""
        counter_rules = {
            "天文": [
                {"pattern": r"所有行星.*都有大气", "counter": "水星几乎没有大气层"},
                {"pattern": r"行星.*散射.*蓝色", "counter": "只有有大气层的行星才有散射，且散射颜色取决于大气成分"},
                {"pattern": r"火星.*蓝色", "counter": "火星大气极薄且含尘埃，天空呈黄褐色而非蓝色"},
                {"pattern": r"木星.*蓝色散射", "counter": "木星大气以氢氦为主，其蓝色部分来自氨云层反射而非瑞利散射"},
            ],
            "物理": [
                {"pattern": r"光.*总是.*直线", "counter": "光在引力场中会弯曲（广义相对论）"},
                {"pattern": r"温度.*只能.*上升", "counter": "温度可以降低，存在绝对零度限制"},
            ],
            "生物": [
                {"pattern": r"所有生物.*都需要氧气", "counter": "厌氧菌不需要氧气，甚至氧气对它们有毒"},
                {"pattern": r"进化.*总是.*进步", "counter": "进化没有方向性，适应环境即可，寄生虫甚至退化了复杂器官"},
            ],
        }

        domain_counters = counter_rules.get(domain, [])
        for rule in domain_counters:
            if re.search(rule["pattern"], statement):
                return rule["counter"]

        return ""

    def _enhance_response(self, query: str, response: str, issues: List[str], chain: List[Dict]) -> str:
        """
        基于推理结果增强回答

        在回答中附加推理过程和修正说明
        """
        if not issues:
            return response

        enhancement_parts = []

        untraceable = [s for s in chain if s.get("traceable") is False and s.get("domain") != "通用"]
        uncovered = [s for s in chain if s.get("traceable") is None]
        if untraceable:
            enhancement_parts.append("🔍 **推理链审视**：")
            for s in untraceable[:2]:
                enhancement_parts.append(f"  - 「{s['fact'][:40]}」— {s.get('gap', '需要进一步验证')}")
        if uncovered:
            enhancement_parts.append("💡 **交叉验证建议**：")
            for s in uncovered[:2]:
                enhancement_parts.append(f"  - 「{s['fact'][:40]}」— {s.get('gap', '建议多源验证')}")

        consistency_issues = [i for i in issues if "矛盾" in i or "冲突" in i or "谬误" in i]
        if consistency_issues:
            enhancement_parts.append("⚠️ **自洽性提示**：")
            for issue in consistency_issues[:2]:
                enhancement_parts.append(f"  - {issue}")

        if enhancement_parts:
            enhancement = "\n\n" + "\n".join(enhancement_parts)
            if "交叉验证建议" not in response:
                return response + enhancement
            return response

        return response

    def build_essence_prompt(self, query: str, conversation_context: str = "") -> str:
        """
        构建本质推理prompt——注入到Ollama/外部API调用中

        强制模型进行第一性原理推理，不允许跳步
        """
        prompt = f"""请用第一性原理来回答以下问题。要求：

1. **从基本事实出发** — 先确认最基本、最无可争议的事实前提
2. **逐步推导** — 每一步推理都必须有依据，不允许跳步
3. **标注确定性** — 对每个声明标注确定程度（确定/很可能/可能/推测）
4. **反面论证** — 考虑可能的反面观点，说明为什么你的结论仍然成立
5. **跨域检查** — 如果涉及多个学科，确保结论在所有相关学科中都成立
6. **区分事实与推论** — 明确区分哪些是已知事实，哪些是你的推理

"""

        if conversation_context:
            prompt += f"""
【对话上下文】
{conversation_context}

"""

        prompt += f"""【问题】
{query}

请按以下格式回答：

**基本事实**：（列出无可争议的前提）
**推理链**：（从基本事实一步步推导）
**结论**：（基于推理链得出的结论）
**确定性**：（确定/很可能/可能/推测）
**反面考虑**：（可能的反面观点及回应）"""

        return prompt

    def _web_fact_check(self, query: str, facts: List[Dict]) -> Dict:
        result = {"checked": [], "contradictions": [], "confirmed": [], "unverifiable": []}

        high_risk_facts = [f for f in facts if f.get("domain") != "通用" and f.get("type") == "scientific"]
        if not high_risk_facts:
            return result

        for fact in high_risk_facts[:2]:
            stmt = fact["statement"]
            domain = fact["domain"]

            check_entry = {"statement": stmt[:80], "domain": domain, "result": "unverifiable"}

            try:
                import requests
                search_query = f"{domain} {stmt[:40]}"
                resp = requests.get(
                    "https://api.duckduckgo.com/",
                    params={"q": search_query, "format": "json", "no_html": 1},
                    timeout=2
                )
                if resp.status_code == 200:
                    data = resp.json()
                    abstract = data.get("Abstract", "")
                    related = data.get("RelatedTopics", [])

                    if abstract:
                        check_entry["source"] = abstract[:200]
                        contradiction = self._check_web_contradiction(stmt, abstract, domain)
                        if contradiction:
                            check_entry["result"] = "contradicted"
                            result["contradictions"].append(f"「{stmt[:40]}」与权威来源冲突：{contradiction}")
                        else:
                            check_entry["result"] = "confirmed"
                            result["confirmed"].append(stmt[:60])
                    else:
                        check_entry["result"] = "unverifiable"
                        result["unverifiable"].append(stmt[:60])

                    for topic in related[:3]:
                        if isinstance(topic, dict) and topic.get("Text"):
                            text = topic["Text"]
                            c = self._check_web_contradiction(stmt, text, domain)
                            if c and c not in result["contradictions"]:
                                result["contradictions"].append(f"「{stmt[:40]}」与搜索结果冲突：{c}")
                                check_entry["result"] = "contradicted"
            except Exception as e:
                logger.debug(f"web事实校验跳过: {str(e)[:60]}")
                check_entry["result"] = "skipped"
                break

            result["checked"].append(check_entry)

        return result

    def _check_web_contradiction(self, statement: str, web_text: str, domain: str) -> str:
        """检查声明与web来源是否矛盾"""
        stmt_lower = statement.lower()

        if domain == "天文":
            if "火星" in stmt_lower and "蓝" in stmt_lower:
                if "红" in web_text and "氧化铁" in web_text:
                    return "火星因表面氧化铁呈红色，不是蓝色"
            if "木星" in stmt_lower and "散射" in stmt_lower and "蓝" in stmt_lower:
                if "氢" in web_text and "氦" in web_text and "氨" in web_text:
                    return "木星大气以氢氦为主，蓝色来自氨云而非瑞利散射"

        if domain == "物理":
            if "超光速" in stmt_lower or "超过光速" in stmt_lower:
                if "光速" in web_text and "不变" in web_text:
                    return "与光速不变原理矛盾"

        return ""

    def _save_reasoning(self, query: str, response: str, result: Dict):
        """持久化推理结果"""
        try:
            conn = sqlite3.connect("data/essence_reasoning.db")
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO reasoning_chains 
                   (query, original_response, facts_extracted, reasoning_chain, consistency_check, final_verdict, confidence, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    query[:200],
                    response[:500],
                    json.dumps(result.get("facts", []), ensure_ascii=False)[:2000],
                    json.dumps(result.get("reasoning_chain", []), ensure_ascii=False)[:2000],
                    json.dumps(result.get("consistency_issues", []), ensure_ascii=False),
                    result.get("verdict", ""),
                    result.get("confidence", 0.0),
                    datetime.now().isoformat()
                )
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"推理结果持久化失败: {e}")

    def essence_gate(self, query: str) -> Dict[str, Any]:
        """
        本质闸门（Essence Gate）— 在解决问题之前，先确定问题的本质

        强制自问自答三个问题：
        1. 剥离表象：这个问题在物理/哲学/数学上的最小不可分单元是什么？
        2. 定义真谛标准：如何判定找到了"本质"？
        3. 设定无知红线：如果无法得到高置信度答案，是否准备好展示"概率云"？

        返回：
        {
            "essence_unit": str,      # 问题的最小不可分单元
            "truth_criteria": str,    # 真谛判定标准
            "ignorance_line": str,    # 无知红线
            "domain": str,            # 主要学科领域
            "sub_domains": list,      # 涉及的子领域
            "is_paradox": bool,       # 是否为悖论/无解问题
            "dispatch_strategy": str  # 调度策略建议
        }
        """
        result = {
            "essence_unit": "",
            "truth_criteria": "",
            "ignorance_line": "",
            "domain": "通用",
            "sub_domains": [],
            "is_paradox": False,
            "dispatch_strategy": "多源并行验证"
        }

        query_lower = query.lower()

        # 代码/工程问题检测：不走科学事实推理链，走代码验证
        is_code = any(kw in query_lower for kw in self.CODE_INDICATORS)
        if is_code:
            result["domain"] = "工程"
            result["essence_unit"] = "算法正确性与工程可行性——本质是'代码能否正确运行'"
            result["truth_criteria"] = "代码能否通过编译和测试用例验证"
            result["ignorance_line"] = "如果无法运行验证，标注为'未经验证代码'并建议用户编译测试"
            result["dispatch_strategy"] = "代码生成+语法检查+模拟验证"
            return result

        # 识别主要领域
        for domain, keywords in self.SCIENCE_DOMAINS.items():
            if any(kw in query for kw in keywords):
                result["domain"] = domain
                result["sub_domains"].append(domain)
                break

        # 跨域检测
        for domain, keywords in self.SCIENCE_DOMAINS.items():
            if domain != result["domain"] and any(kw in query for kw in keywords):
                result["sub_domains"].append(domain)

        # 悖论/无解问题检测
        paradox_patterns = [
            "鸡和蛋", "先有鸡", "先有蛋", "悖论", "矛盾", "无解",
            "无穷", "无限", "循环论证", "自我指涉", "说谎者",
            "祖父悖论", "薛定谔", "不可判定"
        ]
        result["is_paradox"] = any(p in query_lower for p in paradox_patterns)

        # 剥离表象：确定最小不可分单元
        essence_map = {
            "天文": "天体运动的物理规律与观测事实",
            "物理": "基本物理定律与实验验证",
            "化学": "原子/分子层面的相互作用机制",
            "生物": "生命信息的代际传递与自然选择机制",
            "医学": "病理机制与治疗原理",
            "数学": "公理体系与逻辑推导",
        }

        if result["is_paradox"]:
            result["essence_unit"] = "逻辑自指或因果循环——本质是'定义边界'问题，而非'事实'问题"
            result["truth_criteria"] = "能否给出自洽的定义框架，而非唯一正解"
            result["ignorance_line"] = "如果无法消解悖论，诚实呈现多种定义框架下的不同结论"
            result["dispatch_strategy"] = "多角度分析+诚实罗列分歧"
        elif result["domain"] != "通用":
            result["essence_unit"] = essence_map.get(result["domain"], "该领域的基本原理与事实")
            result["truth_criteria"] = f"是否与{result['domain']}基本原理一致且可追溯"
            result["ignorance_line"] = "如果无法从基本原理追溯，标注为'推测'并建议参考权威来源"
            result["dispatch_strategy"] = "第一性原理推理+多源交叉验证"
        else:
            # 哲学/通用问题
            if any(kw in query_lower for kw in ["命运", "意义", "存在", "为什么"]):
                result["essence_unit"] = "因果关系的本质——区分事实因果与价值判断"
                result["truth_criteria"] = "逻辑自洽性+与已知事实的一致性"
                result["ignorance_line"] = "如果涉及价值判断，明确标注为'观点'而非'事实'"
                result["dispatch_strategy"] = "多角度分析+区分事实与观点"
            else:
                result["essence_unit"] = "问题的核心变量与因果关系"
                result["truth_criteria"] = "逻辑自洽+可验证"
                result["ignorance_line"] = "如果无法验证，标注为'推测'并给出验证方向"
                result["dispatch_strategy"] = "多源并行验证"

        return result


essence_reasoner = EssenceReasoner()