import re


def has_science_domain_signatures(response: str) -> bool:
    science_structural_patterns = [
        r'(?:常数|定律|定理|公式|方程|原理|效应|现象|理论)',
        r'(?:实验|测量|观测|证伪|可重复)',
        r'(?:约为|等于|约|大约)\s*\d+\.?\d*\s*(?:×|10\^|km|m|kg|Hz|Pa|J|W|V|A|N|°)',
        r'(?:物理|化学|生物|天文|医学|数学|地质).{0,5}(?:中|上|里|领域)',
    ]
    return any(re.search(p, response[:2000]) for p in science_structural_patterns)


def infer_domain_from_content(query: str, response: str, entities: list) -> str:
    domain_signatures = {
        "天文": ["观测", "轨道", "光年", "星等", "望远镜", "探测器"],
        "物理": ["实验", "测量", "定律", "公式", "常数", "量子态", "波函数"],
        "化学": ["反应", "化合物", "元素", "化学键", "催化", "分子式"],
        "生物": ["细胞", "基因", "进化", "物种", "生态", "蛋白质折叠"],
        "医学": ["临床", "诊断", "治疗", "药物", "病理", "免疫"],
        "数学": ["证明", "定理", "公理", "推导", "反例", "充要条件"],
    }

    domain_refs = {
        "天文": "天文台观测数据、天文学教科书、NASA/ESA等航天机构",
        "物理": "物理学教科书、物理学会期刊、实验物理数据库",
        "化学": "化学教科书、化学学会期刊、元素周期表权威数据",
        "生物": "生物学教科书、Nature/Science等学术期刊、生物数据库",
        "医学": "医学教科书、WHO/CDC等卫生机构、医学期刊",
        "数学": "数学教科书、数学定理证明文献",
    }

    best_domain = None
    best_score = 0
    text = response[:2000]
    for domain, signatures in domain_signatures.items():
        score = sum(1 for s in signatures if s in text)
        if score > best_score:
            best_score = score
            best_domain = domain

    if best_domain and best_score >= 2:
        return domain_refs.get(best_domain, "权威教科书、学术期刊等可靠来源")

    if any(e in ["数学", "物理", "化学", "生物"] for e in entities):
        return "相关学科教科书、学术期刊"

    return "权威教科书、学术期刊等可靠来源"


def understand_response_content(query: str, response: str, cbnr_ctx: dict = None) -> dict:
    """
    语义级内容理解——不是检索关键词，而是理解回复在做什么断言

    返回：
    {
        "makes_factual_claims": bool,
        "claim_type": str,
        "has_numerical_assertions": bool,
        "has_causal_assertions": bool,
        "has_mechanism_descriptions": bool,
        "confidence_level": str,
        "domain": str,
        "needs_verification": bool,
        "reasoning": str,
    }
    """
    has_numerical = bool(re.search(r'\d+\.?\d*\s*(?:%|度|米|秒|千克|焦|伏|安|赫|帕|牛顿|km|m|kg|Hz|Pa|J|W|V|A|N|°|℃|K)', response)) or bool(re.search(r'(?:等于|为|是|约有)\s*\d+\.?\d*', response))

    causal_patterns = [
        r'因为.{1,30}所以', r'由于.{1,30}导致', r'引起了?', r'造成了?',
        r'原因是', r'结果就是', r'从而导致', r'因此产生',
        r'因果', r'causes?', r'leads? to', r'results? in',
        r'因为.{1,40}(?:效应|现象|原理|机制|作用|影响|结果|导致|使得|引起|造成)',
        r'(?:由于|因为).{1,30}(?:散射|折射|反射|吸收|辐射|传导|对流)',
    ]
    has_causal = any(re.search(p, response) for p in causal_patterns)

    mechanism_patterns = [
        r'(?:原理|机制|机理|过程|方式|途径|路径|步骤|流程)是',
        r'(?:通过|利用|借助|依靠|基于).{1,20}(?:实现|完成|达到|产生)',
        r'(?:works?|functions?|operates?) by',
        r'其(?:原理|机制|本质)是',
        r'(?:效应|现象|定律|定理|原理).{0,10}(?:是|为|导致|引起|造成)',
        r'(?:更容易|更难|倾向于|偏好于).{1,20}(?:被|发生|出现)',
    ]
    has_mechanism = any(re.search(p, response) for p in mechanism_patterns)

    absolute_assertion_patterns = [
        r'(?:一定|必然|绝对|肯定|毫无疑问).{0,10}(?:是|对|正确|成立)',
        r'(?:等于|约为|大约|约|接近)\s*\d',
        r'(?:速度|温度|质量|密度|压力|频率|能量|功率|电压|电流).{0,5}\d',
    ]
    has_absolute = any(re.search(p, response) for p in absolute_assertion_patterns)

    l2_topic = (cbnr_ctx or {}).get("l2_topic", "")
    l2_entities = (cbnr_ctx or {}).get("l2_entities", [])
    l2_question_type = (cbnr_ctx or {}).get("l2_question_type", "")

    scientific_entity_types = {"物理", "化学", "生物", "天文", "医学", "数学", "地质", "气象"}
    tech_entity_types = {"架构", "框架", "模型", "系统", "引擎", "API", "协议", "算法", "组件", "接口", "配置", "部署"}

    has_scientific_entities = any(e in scientific_entity_types or any(s in e for s in scientific_entity_types) for e in l2_entities)
    has_tech_entities = any(e in tech_entity_types or any(t in e for t in tech_entity_types) for e in l2_entities)

    is_descriptive_only = not has_numerical and not has_causal and not has_mechanism and not has_absolute

    if is_descriptive_only and not has_scientific_entities:
        claim_type = "descriptive"
        needs_verification = False
        domain = "general"
    elif has_tech_entities and not has_numerical and not has_scientific_entities:
        claim_type = "technical"
        needs_verification = False
        domain = "技术"
    elif has_numerical and (has_causal or has_mechanism) and (has_scientific_entities or has_science_domain_signatures(response)):
        claim_type = "scientific"
        needs_verification = True
        domain = infer_domain_from_content(query, response, l2_entities)
    elif has_numerical or has_causal or has_mechanism:
        if has_scientific_entities or has_science_domain_signatures(response):
            claim_type = "scientific"
            needs_verification = True
            domain = infer_domain_from_content(query, response, l2_entities)
        elif has_numerical and has_absolute:
            claim_type = "factual"
            needs_verification = True
            domain = infer_domain_from_content(query, response, l2_entities)
        else:
            claim_type = "factual"
            needs_verification = has_numerical
            domain = infer_domain_from_content(query, response, l2_entities)
    else:
        claim_type = "opinion"
        needs_verification = False
        domain = "general"

    confidence = "high" if has_numerical and has_causal else "medium" if has_causal or has_numerical else "low"

    reasoning_parts = []
    if has_numerical: reasoning_parts.append("包含数值断言")
    if has_causal: reasoning_parts.append("包含因果断言")
    if has_mechanism: reasoning_parts.append("描述了机制原理")
    if has_absolute: reasoning_parts.append("包含绝对化陈述")
    if has_scientific_entities: reasoning_parts.append(f"L2识别科学实体({l2_entities[:3]})")
    if has_tech_entities: reasoning_parts.append(f"L2识别技术实体")
    if is_descriptive_only: reasoning_parts.append("纯描述性内容")

    return {
        "makes_factual_claims": has_numerical or has_causal or has_mechanism,
        "claim_type": claim_type,
        "has_numerical_assertions": has_numerical,
        "has_causal_assertions": has_causal,
        "has_mechanism_descriptions": has_mechanism,
        "confidence_level": confidence,
        "domain": domain,
        "needs_verification": needs_verification,
        "reasoning": "; ".join(reasoning_parts) if reasoning_parts else "无显著断言",
    }


def get_domain_reference(query: str, response: str) -> str:
    text = (query + " " + response).lower()
    domain_refs = {
        "天文": "天文台观测数据、天文学教科书、NASA/ESA等航天机构",
        "物理": "物理学教科书、物理学会期刊、实验物理数据库",
        "化学": "化学教科书、化学学会期刊、元素周期表权威数据",
        "生物": "生物学教科书、Nature/Science等学术期刊、生物数据库",
        "医学": "医学教科书、WHO/CDC等卫生机构、医学期刊",
        "数学": "数学教科书、数学定理证明文献",
    }
    domain_keywords = {
        "天文": ["天文", "星", "宇宙", "行星", "恒星", "银河", "太阳系", "轨道", "引力波", "黑洞", "火星", "木星", "土星", "金星", "水星", "月球", "大气成分", "大气层", "探测器", "望远镜", "航天"],
        "物理": ["物理", "力", "能量", "量子", "相对论", "电磁", "散射", "折射", "波长", "光", "天空", "蓝色", "颜色", "光谱", "频率", "波动"],
        "化学": ["化学", "原子", "分子", "元素", "化合物", "反应", "化学键", "催化"],
        "生物": ["生物", "细胞", "基因", "DNA", "进化", "物种", "鸡", "蛋", "卵生", "繁殖", "遗传"],
        "医学": ["医学", "疾病", "药物", "治疗", "诊断", "免疫", "疫苗"],
        "数学": ["数学", "证明", "定理", "公式", "函数", "方程", "概率"],
    }
    best_domain = None
    best_count = 0
    for domain, keywords in domain_keywords.items():
        count = sum(1 for kw in keywords if kw in text)
        if count > best_count:
            best_count = count
            best_domain = domain
    if best_domain:
        return domain_refs[best_domain]
    return "权威教科书、学术期刊等可靠来源"


def discover_methodology(query: str, intent_type: str) -> dict:
    query_lower = query.lower()
    result = {
        "strategy": "多源并行验证",
        "source_priority": ["经验池", "知识库", "Ollama", "外部API", "规则推理"],
        "verification": "本质推理+自洽验证",
        "need_essence_reasoning": True
    }

    try:
        from core.skill_emergence import skill_emergence
        applicable_skills = skill_emergence.get_applicable_skills(query)
        if applicable_skills:
            best_skill = applicable_skills[0]
            if best_skill["success_rate"] >= 0.7 and best_skill["success_count"] >= 3:
                result["strategy"] = f"技能驱动({best_skill['skill_name']})+多源验证"
                result["skill_path"] = best_skill["solution_path"]
    except Exception:
        pass

    if any(kw in query_lower for kw in ["代码", "编程", "函数", "程序", "算法", "单片机", "stm32", "arduino", "嵌入式", "写一段", "实现"]):
        result["strategy"] = "代码生成+语法检查+模拟验证"
        result["source_priority"] = ["Ollama", "外部API", "规则推理", "知识库", "经验池"]
        result["need_essence_reasoning"] = False
        return result

    if any(kw in query_lower for kw in ["为什么", "是什么", "原理", "原因", "机制", "本质"]):
        result["strategy"] = "第一性原理推理+多源交叉验证"
        result["source_priority"] = ["外部API", "知识库", "Ollama", "经验池", "规则推理"]
        result["need_essence_reasoning"] = True

    elif any(kw in query_lower for kw in ["天文", "物理", "化学", "生物", "医学", "数学", "科学"]):
        result["strategy"] = "科学事实多源验证+跨域一致性检查"
        result["source_priority"] = ["外部API", "知识库", "Ollama", "经验池", "规则推理"]
        result["need_essence_reasoning"] = True

    elif any(kw in query_lower for kw in ["命运", "意义", "哲学", "悖论", "鸡和蛋", "先有"]):
        result["strategy"] = "多角度分析+诚实罗列分歧"
        result["source_priority"] = ["Ollama", "外部API", "知识库", "经验池", "规则推理"]
        result["need_essence_reasoning"] = True

    elif any(kw in query_lower for kw in ["如何", "怎么", "怎样", "方法"]):
        result["strategy"] = "经验检索+多源方法对比"
        result["source_priority"] = ["经验池", "知识库", "Ollama", "外部API", "规则推理"]
        result["need_essence_reasoning"] = False

    return result