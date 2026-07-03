"""
系统自我审核员 (System Auditor) - 负空间感知能力

让系统能够：
1. 读取README中的功能声明
2. 扫描代码中的实际实现
3. 对比两者，发现"应该存在但缺失"的差距
4. 生成结构化的差距分析报告

灵感来源：用户感悟——"为什么系统不能自己构建如此详细的自我审核机制？"
"""
import re
import os
import json
import sqlite3
from typing import Dict, List, Any
from loguru import logger
from datetime import datetime


class SystemAuditor:
    """系统自我审核员——负空间感知：发现"应该存在但缺失"的东西"""

    def __init__(self, root_dir: str = "."):
        self.root_dir = root_dir

    def audit(self) -> dict:
        """执行全面系统审核"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "api_endpoints": self._audit_api_endpoints(),
            "core_modules": self._audit_core_modules(),
            "data_health": self._audit_data_health(),
            "config_consistency": self._audit_config_consistency(),
            "gene_consistency": self._audit_gene_consistency(),
        }

        gaps = []
        gaps.extend(report["api_endpoints"].get("gaps", []))
        gaps.extend(report["core_modules"].get("gaps", []))
        gaps.extend(report["data_health"].get("gaps", []))
        gaps.extend(report["config_consistency"].get("gaps", []))
        gaps.extend(report["gene_consistency"].get("gaps", []))

        report["summary"] = {
            "total_gaps": len(gaps),
            "high_priority": len([g for g in gaps if g.get("severity") == "high"]),
            "medium_priority": len([g for g in gaps if g.get("severity") == "medium"]),
            "low_priority": len([g for g in gaps if g.get("severity") == "low"]),
            "gaps": gaps[:20],
        }

        return report

    def _audit_api_endpoints(self) -> dict:
        """审核API端点：文档声称的 vs 代码实际实现的"""
        result = {"documented": [], "implemented": [], "gaps": []}

        try:
            main_fast_path = os.path.join(self.root_dir, "backend", "main_fast.py")
            if os.path.exists(main_fast_path):
                with open(main_fast_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                implemented = re.findall(r'@app\.(get|post|put|delete)\("(.*?)["\']', content)
                result["implemented"] = [ep[1] for ep in implemented]

            readme_path = os.path.join(self.root_dir, "README.md")
            if os.path.exists(readme_path):
                with open(readme_path, 'r', encoding='utf-8-sig') as f:
                    content = f.read()
                documented = re.findall(r'`(?:GET|POST|PUT|DELETE)\s+(/api/[^`]+)`', content)
                result["documented"] = documented

            for doc_ep in result["documented"]:
                if doc_ep not in result["implemented"]:
                    result["gaps"].append({
                        "type": "api_missing",
                        "severity": "high",
                        "description": f"文档声称有{doc_ep}但代码未实现",
                        "endpoint": doc_ep,
                    })

        except Exception as e:
            logger.debug(f"API端点审核失败: {e}")

        return result

    def _audit_core_modules(self) -> dict:
        """审核核心模块：休眠模块检测"""
        result = {"active": [], "dormant": [], "gaps": []}

        dormant_modules = [
            ("立体记忆", "core/memory/stereo_memory.py"),
            ("关系模型", "core/relationship/model.py"),
            ("存在层", "core/presence/existence_layer.py"),
            ("自我感知", "core/presence/self_perception.py"),
            ("间隙生长", "core/presence/gap_growth.py"),
            ("睡眠整合", "core/presence/sleep_consolidation.py"),
            ("自我评估", "core/presence/self_assessment.py"),
            ("主动性引擎", "core/presence/proactivity.py"),
            ("信号集成", "core/presence/signal_integration.py"),
            ("自适应进化目标", "core/evolution/adaptive_goal.py"),
            ("向量检索", "infrastructure/vector_retriever.py"),
            ("事实库", "infrastructure/fact_store.py"),
            ("适应度评估", "infrastructure/fitness_evaluator.py"),
            ("注入验证", "infrastructure/injection_verifier.py"),
            ("版本化事实库", "infrastructure/versioned_fact_store.py"),
            ("外部学习器", "infrastructure/external_learners.py"),
        ]

        main_fast_path = os.path.join(self.root_dir, "backend", "main_fast.py")
        chat_stream_path = os.path.join(self.root_dir, "backend", "chat_stream.py")

        main_fast_content = ""
        chat_stream_content = ""
        try:
            if os.path.exists(main_fast_path):
                with open(main_fast_path, 'r', encoding='utf-8') as f:
                    main_fast_content = f.read()
            if os.path.exists(chat_stream_path):
                with open(chat_stream_path, 'r', encoding='utf-8') as f:
                    chat_stream_content = f.read()
        except:
            pass

        for name, path in dormant_modules:
            full_path = os.path.join(self.root_dir, path)
            exists = os.path.exists(full_path)
            module_name = path.replace("/", ".").replace(".py", "")
            imported = module_name in main_fast_content or module_name in chat_stream_content

            if exists and not imported:
                result["dormant"].append({"name": name, "path": path, "exists": True, "imported": False})
                result["gaps"].append({
                    "type": "dormant_module",
                    "severity": "medium",
                    "description": f"{name}({path})存在但未被主流程加载",
                    "module": name,
                })
            elif exists and imported:
                result["active"].append({"name": name, "path": path, "exists": True, "imported": True})

        return result

    def _audit_data_health(self) -> dict:
        """审核数据健康：经验池success率、规则置信度等"""
        result = {"stats": {}, "gaps": []}

        try:
            conn = sqlite3.connect(os.path.join(self.root_dir, "data", "experience_pool.db"))
            c = conn.cursor()
            c.execute("SELECT success, COUNT(*) FROM experiences GROUP BY success")
            success_dist = {str(r[0]): r[1] for r in c.fetchall()}
            total = sum(success_dist.values())
            success_1 = success_dist.get("1", 0)
            success_rate = success_1 / max(total, 1)
            result["stats"]["experience_success_rate"] = round(success_rate, 3)
            if success_rate < 0.5:
                result["gaps"].append({
                    "type": "low_success_rate",
                    "severity": "high",
                    "description": f"经验池success率仅{success_rate:.0%}，学习闭环可能失效",
                })
            conn.close()
        except:
            pass

        try:
            conn = sqlite3.connect(os.path.join(self.root_dir, "data", "learning_rules.db"))
            c = conn.cursor()
            c.execute("SELECT AVG(confidence) FROM learning_rules WHERE status='active'")
            avg_conf = c.fetchone()[0] or 0.5
            result["stats"]["avg_rule_confidence"] = round(avg_conf, 3)
            if avg_conf <= 0.5:
                result["gaps"].append({
                    "type": "undifferentiated_confidence",
                    "severity": "medium",
                    "description": f"活跃规则平均置信度{avg_conf:.2f}，未分化（大部分=0.5）",
                })
            conn.close()
        except:
            pass

        return result

    def _audit_config_consistency(self) -> dict:
        """审核配置一致性：版本号等"""
        result = {"checks": [], "gaps": []}

        versions = set()
        try:
            main_fast_path = os.path.join(self.root_dir, "backend", "main_fast.py")
            if os.path.exists(main_fast_path):
                with open(main_fast_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                v = re.search(r'version["\s:=]+["\']?(\d+\.\d+\.\d+)', content)
                if v:
                    versions.add(("main_fast.py", v.group(1)))
        except:
            pass

        if len(versions) > 1:
            result["gaps"].append({
                "type": "version_mismatch",
                "severity": "low",
                "description": f"版本号不一致: {versions}",
            })

        return result

    def _audit_gene_consistency(self) -> dict:
        """审核基因参数一致性"""
        result = {"gene_sources": {}, "gaps": []}

        try:
            task_queue_path = os.path.join(self.root_dir, "core", "task_queue.py")
            if os.path.exists(task_queue_path):
                with open(task_queue_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                genes = re.findall(r'"(\w+)":\s*[\d.]+', content[:3000])
                result["gene_sources"]["task_queue"] = genes[:15]
        except:
            pass

        return result


system_auditor = SystemAuditor()