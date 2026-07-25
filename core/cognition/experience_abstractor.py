"""
经验抽象器——从具体经历中提炼可迁移模式。
补全认知七步闭环中缺失的"抽象"层。

感知→分解→执行→自察→【抽象】→沉淀→进化

气味特征(scent): 统一描述问题的传感器/动作/目标维度，
使骨架匹配从"阶段名相似"升级为"问题结构同构"。
例如: 串口读取→NMEA解析→地图标记 和 麦克风→语音识别→字幕显示
骨架都是 acquire→parse→visualize，但scent区分了:
  前者: sensor=serial, action=parse_protocol, target=map
  后者: sensor=audio, action=parse_speech, target=subtitle
"""

import re
from typing import Dict, Any, List, Optional
from loguru import logger
from core.ports.adapters import get_storage_port
try:
    from core.spirit_core import spirit_core
    SPIRIT_CORE_AVAILABLE = True
except ImportError:
    SPIRIT_CORE_AVAILABLE = False
    spirit_core = None


class ExperienceAbstractor:
    """
    从一次完整的认知经历中提取可迁移模式。
    这是"学会学习"的关键——不是记住答案，而是记住"怎么找到答案"。
    """

    SCENT_VOCAB = {
        "sensor": {
            "serial": ["串口", "com", "端口", "波特率", "usb-serial", "ch340", "cp210"],
            "audio": ["麦克风", "录音", "声音", "语音", "音频", "mic"],
            "network": ["网络", "http", "api", "请求", "url", "下载", "爬虫"],
            "file": ["文件", "读取文件", "csv", "json", "xml", "导入"],
            "camera": ["摄像头", "图像", "拍照", "视频", "相机"],
            "gpio": ["引脚", "gpio", "io口", "继电器", "led", "舵机"],
            "gps": ["gps", "定位", "坐标", "经纬度", "nmea"],
            "env": ["温度", "湿度", "气压", "光照", "环境"],
        },
        "action": {
            "parse_protocol": ["nmea", "协议", "解析协议", "解码", "帧"],
            "parse_speech": ["语音识别", "转文字", "stt", "asr"],
            "parse_text": ["分词", "nlp", "语义", "文本分析", "关键词"],
            "parse_image": ["ocr", "识别", "检测", "分类", "目标检测"],
            "transform": ["转换", "换算", "映射", "编码", "格式化"],
            "compute": ["计算", "统计", "聚合", "求和", "平均"],
            "query": ["查询", "搜索", "检索", "查找", "匹配"],
        },
        "target": {
            "map": ["地图", "标记", "定位", "坐标", "位置"],
            "chart": ["图表", "曲线", "折线", "柱状", "可视化"],
            "alert": ["报警", "预警", "通知", "提醒", "告警"],
            "control": ["控制", "操作", "开关", "调节", "执行"],
            "report": ["报告", "总结", "汇总", "输出", "展示"],
            "subtitle": ["字幕", "文本", "显示", "标注"],
            "database": ["存储", "保存", "入库", "记录", "持久化"],
        },
    }

    @classmethod
    def extract_scent(cls, query: str) -> Dict[str, str]:
        """
        从查询中提取气味特征——问题的传感器/动作/目标维度。
        这是骨架匹配的增强：不仅匹配"acquire→parse→visualize"，
        还要匹配"serial→parse_protocol→map"这种更精细的结构。
        """
        scent = {"sensor": "unknown", "action": "unknown", "target": "unknown"}
        query_lower = query.lower()

        for dim, vocab in cls.SCENT_VOCAB.items():
            best_key = "unknown"
            best_count = 0
            for key, keywords in vocab.items():
                count = sum(1 for kw in keywords if kw in query_lower)
                if count > best_count:
                    best_count = count
                    best_key = key
            if best_count > 0:
                scent[dim] = best_key

        return scent

    @classmethod
    def scent_signature(cls, scent: Dict[str, str]) -> str:
        """将气味特征转为可比较的签名字符串"""
        return f"{scent.get('sensor', '?')}:{scent.get('action', '?')}:{scent.get('target', '?')}"

    @classmethod
    def scent_similarity(cls, scent_a: Dict[str, str], scent_b: Dict[str, str],
                         query_a: str = "", query_b: str = "") -> float:
        """
        计算两个气味特征的相似度。
        三维度关键词匹配 + 语义向量距离，加权融合。
        keyword_weight=0.5, semantic_weight=0.5
        """
        keyword_score = 0.0
        for dim in ("sensor", "action", "target"):
            a_val = scent_a.get(dim, "unknown")
            b_val = scent_b.get(dim, "unknown")
            if a_val != "unknown" and b_val != "unknown":
                if a_val == b_val:
                    keyword_score += 1.0 / 3
                elif a_val == "unknown" or b_val == "unknown":
                    pass
                else:
                    keyword_score += 0.1 / 3

        if not query_a or not query_b:
            return keyword_score

        semantic_score = cls._semantic_scent_score(query_a, query_b)
        if semantic_score is None:
            return keyword_score

        return keyword_score * 0.5 + semantic_score * 0.5

    @classmethod
    def _semantic_scent_score(cls, text_a: str, text_b: str) -> Optional[float]:
        """用共享嵌入计算语义向量距离，降级返回None"""
        try:
            from core.shared_embedding import similarity as emb_similarity
            score = emb_similarity(text_a, text_b)
            if score > 0.0:
                return score
        except Exception as e:
            logger.warning(f"操作降级跳过: {e}")
        return None

    @classmethod
    def abstract(cls, user_query: str, intent_type: str, steps: List[Dict],
                 final_success: bool, failure_reason: str = "") -> Dict[str, Any]:
        """
        从经历中提炼可迁移模式。

        Args:
            user_query: 用户原始问题
            intent_type: 意图类型
            steps: 执行步骤列表 [{"action": str, "result_preview": str, "success": bool}]
            final_success: 最终是否成功
            failure_reason: 失败原因（如果失败）

        Returns:
            {"key_insights": [...], "transferable_patterns": {...}, "success": bool}
        """
        insights = []
        transferable = {}
        
        # 精神共振检测：记录与经验相关的原则触发
        spirit_resonances = []
        if SPIRIT_CORE_AVAILABLE and user_query:
            try:
                resonances = spirit_core.resonate(user_query, context_type="reasoning")
                for r in resonances[:2]:  # 只记录前2个共振原则
                    spirit_resonances.append({
                        "principle": r.get("principle"),
                        "strength": r.get("strength"),
                        "drive_direction": r.get("drive_direction")
                    })
            except Exception as e:
                logger.debug(f"经验抽象精神共振检测失败: {e}")

        if re.search(r'串口\d+|端口\d+|com\d+', user_query, re.IGNORECASE):
            insights.append("用户使用中文别名引用硬件编号，需映射为标准标识符")
            transferable["alias_mapping"] = {
                "trigger": "中文前缀+数字 或 COM+数字",
                "action": "提取数字，加上标准前缀(如COM)",
                "domain": "hardware",
                "confidence": 0.9,
            }

        if len(steps) >= 3 and final_success:
            successful_actions = [s["action"] for s in steps if s.get("success")]
            insights.append(f"复杂问题需要分步验证，有效路径: {'→'.join(successful_actions)}")
            transferable["multi_step_reasoning"] = {
                "trigger": "用户要求'读取并分析'或'获取并处理'",
                "workflow": successful_actions,
                "domain": intent_type,
                "confidence": 0.85,
            }

        if not final_success and failure_reason:
            insights.append(f"失败模式: {failure_reason}")
            transferable["failure_pattern"] = {
                "trigger": user_query[:50],
                "failure_reason": failure_reason,
                "domain": intent_type,
                "confidence": 0.7,
            }

        if not insights:
            if final_success:
                insights.append("完成了一次标准的信息获取任务")
            else:
                insights.append("任务未完成，需进一步分析原因")

        skeleton = cls._extract_skeleton(user_query, steps, final_success)
        if skeleton:
            transferable["skeleton"] = skeleton

        scent = cls.extract_scent(user_query)
        scent_sig = cls.scent_signature(scent)

        return {
            "key_insights": insights,
            "transferable_patterns": transferable,
            "success": final_success,
            "skeleton": skeleton,
            "scent": scent,
            "scent_signature": scent_sig,
            "spirit_resonances": spirit_resonances,
        }

    @classmethod
    def _extract_skeleton(cls, query: str, steps: List[Dict], success: bool) -> str:
        """
        从经历中提取抽象骨架——问题结构而非具体实现。
        这是"触类旁通"的基础：串口→NMEA→地图 和 麦克风→语音→地图 共享骨架 sensors→parse→visualize
        """
        stage_keywords = {
            "acquire": ["读取", "获取", "扫描", "检测", "采集", "接收", "下载", "导入"],
            "parse": ["解析", "分析", "理解", "识别", "翻译", "转换", "提取", "解码"],
            "visualize": ["标记", "显示", "渲染", "绘制", "呈现", "展示", "可视化"],
            "verify": ["验证", "确认", "检查", "校验", "核实"],
            "reason": ["推理", "思考", "推断", "判断", "总结"],
            "actuate": ["执行", "运行", "操作", "控制", "发送", "写入"],
        }
        
        query_stages = []
        for stage, keywords in stage_keywords.items():
            if any(kw in query for kw in keywords) and stage not in query_stages:
                query_stages.append(stage)
        
        step_stages = []
        for step in steps:
            action = step.get("action", "")
            for stage, keywords in stage_keywords.items():
                if any(kw in action for kw in keywords) and stage not in step_stages:
                    step_stages.append(stage)
        
        skeleton = "→".join(query_stages or step_stages or ["acquire", "parse", "output"])
        return skeleton

    @classmethod
    def find_analogous(cls, new_query: str, threshold: float = 0.6) -> Optional[Dict]:
        """
        为新问题查找骨架相似的历史经验（触类旁通）。
        不仅匹配阶段名相似，还匹配气味特征（传感器/动作/目标）。
        综合得分 = 骨架相似度 * 0.6 + 气味相似度 * 0.4
        """
        try:
            new_skeleton = cls._extract_skeleton(new_query, [], True)
            new_stages = set(new_skeleton.split("→"))
            new_scent = cls.extract_scent(new_query)
            
            db = get_storage_port("data/skills.db")
            rows = db.query(
                "SELECT skill_name, trigger_patterns, solution_path, skeleton, confidence, success_count FROM skills WHERE is_active=1 AND skeleton != ''"
            )
            
            best_match = None
            best_score = 0.0
            
            for row in rows:
                existing_skeleton = row[3] if len(row) > 3 else ""
                if not existing_skeleton:
                    continue
                existing_stages = set(existing_skeleton.split("→"))
                
                if not new_stages or not existing_stages:
                    continue
                
                overlap = new_stages & existing_stages
                union = new_stages | existing_stages
                skeleton_sim = len(overlap) / len(union) if union else 0

                existing_scent = {"sensor": "unknown", "action": "unknown", "target": "unknown"}
                trigger_parts = (row[1] or "").split("|")
                trigger_text = " ".join(trigger_parts)
                if trigger_text:
                    existing_scent = cls.extract_scent(trigger_text)
                scent_sim = cls.scent_similarity(new_scent, existing_scent,
                                                  query_a=new_query, query_b=trigger_text)

                combined_score = skeleton_sim * 0.6 + scent_sim * 0.4
                
                if combined_score > best_score:
                    best_score = combined_score
                    best_match = {
                        "skill_name": row[0],
                        "skeleton": existing_skeleton,
                        "skeleton_similarity": skeleton_sim,
                        "scent_similarity": scent_sim,
                        "similarity": combined_score,
                        "solution_path": row[2],
                        "confidence": row[4] if len(row) > 4 else 0.5,
                        "new_scent": new_scent,
                        "existing_scent": existing_scent,
                    }
            
            if best_match and best_score >= threshold:
                logger.info(f"🧠 骨架联想: {best_match['skill_name']} (综合{best_score:.2f}=骨架{best_match['skeleton_similarity']:.2f}+气味{best_match['scent_similarity']:.2f}, 骨架{best_match['skeleton']})")
                return best_match
        except Exception as e:
            logger.error(f"骨架联想失败: {e}")
        return None

    @classmethod
    def settle_to_skill_db(cls, abstracted: Dict, user_query: str, intent_type: str):
        """将抽象出的模式沉淀到skill_emergence技能表"""
        try:
            db = get_storage_port("data/skill_emergence.db")
            patterns = abstracted.get("transferable_patterns", {})
            for pattern_name, pattern_data in patterns.items():
                skill_name = f"abstracted_{pattern_name}"
                existing = db.query_one(
                    'SELECT skill_name FROM skills WHERE skill_name=?', (skill_name,)
                )
                if not existing:
                    from datetime import datetime
                    db.execute(
                        'INSERT OR REPLACE INTO skills (skill_name, skill_type, trigger_pattern, solution_path, success_count, fail_count, success_rate, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)',
                        (skill_name, pattern_data.get("domain", "abstracted"),
                         pattern_data.get("trigger", user_query[:50]),
                         pattern_data.get("action", ""), 1 if abstracted["success"] else 0,
                         0 if abstracted["success"] else 1,
                         1.0 if abstracted["success"] else 0.0,
                         datetime.now().isoformat()),
                        commit=True
                    )
                    logger.info(f"🧬 经验抽象: 新模式入库 {skill_name}")
                else:
                    if abstracted["success"]:
                        db.execute(
                            'UPDATE skills SET success_count=success_count+1, success_rate=CAST(success_count AS FLOAT)/(success_count+fail_count) WHERE skill_name=?',
                            (skill_name,), commit=True
                        )
                    else:
                        db.execute(
                            'UPDATE skills SET fail_count=fail_count+1, success_rate=CAST(success_count AS FLOAT)/(success_count+fail_count) WHERE skill_name=?',
                            (skill_name,), commit=True
                        )
        except Exception as e:
            logger.warning(f"经验抽象沉淀跳过: {e}")