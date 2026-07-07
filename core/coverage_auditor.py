"""
覆盖率审计器 (Coverage Auditor)

元认知闭环第一步：让系统"能看见"自己的覆盖率

核心使命：
  - 扫描后端所有API端点
  - 扫描前端已调用的API端点
  - 交叉比对生成覆盖率报告
  - 集成到self_assessment作为第六维评估

设计哲学：
  - 不依赖硬编码的端点列表，从FastAPI app动态获取
  - 不依赖硬编码的前端调用，从JS源码正则提取
  - 报告不只是"覆盖率数字"，而是"哪些端点未覆盖+为什么重要"
"""
import re
import os
from typing import Dict, List, Set, Tuple, Optional
from pathlib import Path
from loguru import logger


class CoverageAuditor:
    PRIORITY_MAP = {
        "chat": "P0",
        "health": "P1",
        "tools": "P0",
        "agent": "P0",
        "defense": "P1",
        "memory": "P1",
        "facts": "P2",
        "knowledge": "P2",
        "truths": "P1",
        "skills": "P2",
        "genes": "P2",
        "trajectory": "P2",
        "assessment": "P1",
        "alignment": "P2",
        "introspection": "P2",
        "proactivity": "P1",
        "presence": "P2",
        "relationship": "P2",
        "forgetting": "P2",
        "reorganization": "P2",
        "reflection": "P2",
        "weights": "P2",
        "probability": "P2",
        "delta": "P2",
        "attribution": "P2",
        "events": "P2",
        "scheduled": "P2",
        "models": "P1",
        "config": "P2",
        "folder": "P2",
        "file": "P2",
        "input-processor": "P2",
        "knowledge-graph": "P2",
        "closed-loop": "P1",
        "optimize": "P2",
        "induction": "P2",
        "recent_learning": "P2",
        "module": "P2",
        "evolution": "P2",
    }

    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir)
        self._backend_endpoints: List[dict] = []
        self._frontend_endpoints: Set[str] = set()
        self._last_report: Optional[dict] = None

    def scan_backend_endpoints(self, app=None) -> List[dict]:
        if app is not None:
            self._backend_endpoints = self._scan_from_app(app)
        else:
            self._backend_endpoints = self._scan_from_source()
        return self._backend_endpoints

    def _scan_from_app(self, app) -> List[dict]:
        endpoints = []
        for route in app.routes:
            if hasattr(route, "methods") and hasattr(route, "path"):
                for method in route.methods:
                    if method in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                        path = route.path
                        if path.startswith("/api") or path == "/":
                            priority = self._infer_priority(path)
                            category = self._infer_category(path)
                            endpoints.append({
                                "method": method,
                                "path": path,
                                "priority": priority,
                                "category": category,
                            })
        return endpoints

    def _scan_from_source(self) -> List[dict]:
        main_fast = self.root_dir / "backend" / "main_fast.py"
        if not main_fast.exists():
            return []
        content = main_fast.read_text(encoding="utf-8")
        pattern = r'@(app|router)\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']'
        endpoints = []
        for match in re.finditer(pattern, content):
            method = match.group(2).upper()
            path = match.group(3)
            priority = self._infer_priority(path)
            category = self._infer_category(path)
            endpoints.append({
                "method": method,
                "path": path,
                "priority": priority,
                "category": category,
            })
        return endpoints

    def scan_frontend_endpoints(self) -> Set[str]:
        app_js = self.root_dir / "frontend" / "app.js"
        if not app_js.exists():
            self._frontend_endpoints = set()
            return self._frontend_endpoints
        content = app_js.read_text(encoding="utf-8")
        patterns = [
            r"fetch\(['\"`]([^'\"`]+)['\"`]",
            r"fetch\(`([^`]+)`\)",
            r"EventSource\(['\"`]([^'\"`]+)['\"`]",
            r"EventSource\(`([^`]+)`\)",
            r"['\"`](/api/[a-zA-Z0-9_/\-]+)['\"`]",
        ]
        endpoints = set()
        for pattern in patterns:
            for match in re.finditer(pattern, content):
                url = match.group(1)
                url = re.sub(r"\$\{API_BASE\}", "", url)
                url = re.sub(r"\$\{[^}]+\}", "{param}", url)
                if url.startswith("/api") or url.startswith("api/"):
                    if not url.startswith("/"):
                        url = "/" + url
                    clean = url.split("?")[0]
                    clean = re.sub(r"/\{param\}", "/{param}", clean)
                    endpoints.add(clean)
        self._frontend_endpoints = endpoints
        endpoints.add("/")
        return endpoints

    def _infer_priority(self, path: str) -> str:
        for keyword, priority in self.PRIORITY_MAP.items():
            if keyword in path.lower():
                return priority
        return "P3"

    def _infer_category(self, path: str) -> str:
        parts = path.strip("/").split("/")
        if len(parts) >= 3:
            return parts[2]
        if len(parts) == 2:
            return parts[1]
        return "root"

    def generate_report(self, app=None) -> dict:
        self.scan_backend_endpoints(app)
        self.scan_frontend_endpoints()

        backend_paths = {}
        for ep in self._backend_endpoints:
            key = f"{ep['method']}:{ep['path']}"
            backend_paths[key] = ep

        frontend_path_set = set()
        for fe in self._frontend_endpoints:
            fe_normalized = fe.rstrip("/")
            frontend_path_set.add(fe_normalized)
            fe_no_param = re.sub(r"/\{param\}.*$", "", fe_normalized)
            if fe_no_param != fe_normalized:
                frontend_path_set.add(fe_no_param)

        covered = []
        uncovered = []
        for key, ep in backend_paths.items():
            path_normalized = ep["path"].rstrip("/")
            path_no_param = re.sub(r"/\{[^}]+\}.*$", "", path_normalized)
            is_covered = (
                path_normalized in frontend_path_set
                or path_no_param in frontend_path_set
                or ep["path"] in self._frontend_endpoints
            )
            if not is_covered:
                for fe in frontend_path_set:
                    if path_normalized.startswith(fe) and len(path_normalized) > len(fe):
                        is_covered = True
                        break
            entry = {
                "method": ep["method"],
                "path": ep["path"],
                "priority": ep["priority"],
                "category": ep["category"],
                "covered": is_covered,
            }
            if is_covered:
                covered.append(entry)
            else:
                uncovered.append(entry)

        total = len(backend_paths)
        covered_count = len(covered)
        coverage_rate = covered_count / max(total, 1)

        by_priority = {}
        for entry in covered + uncovered:
            p = entry["priority"]
            if p not in by_priority:
                by_priority[p] = {"total": 0, "covered": 0}
            by_priority[p]["total"] += 1
            if entry["covered"]:
                by_priority[p]["covered"] += 1

        by_category = {}
        for entry in covered + uncovered:
            c = entry["category"]
            if c not in by_category:
                by_category[c] = {"total": 0, "covered": 0}
            by_category[c]["total"] += 1
            if entry["covered"]:
                by_category[c]["covered"] += 1

        high_priority_uncovered = [
            e for e in uncovered if e["priority"] in ("P0", "P1")
        ]

        report = {
            "total_endpoints": total,
            "covered_endpoints": covered_count,
            "uncovered_endpoints": len(uncovered),
            "coverage_rate": round(coverage_rate, 3),
            "by_priority": by_priority,
            "by_category": by_category,
            "covered": covered,
            "uncovered": uncovered,
            "high_priority_gaps": high_priority_uncovered,
            "score": self._calculate_score(coverage_rate, by_priority),
        }
        self._last_report = report
        return report

    def _calculate_score(self, coverage_rate: float, by_priority: dict) -> float:
        p0_rate = 0.0
        p1_rate = 0.0
        if "P0" in by_priority:
            p0_rate = by_priority["P0"]["covered"] / max(by_priority["P0"]["total"], 1)
        if "P1" in by_priority:
            p1_rate = by_priority["P1"]["covered"] / max(by_priority["P1"]["total"], 1)
        score = coverage_rate * 0.4 + p0_rate * 0.35 + p1_rate * 0.25
        return round(score, 3)

    def get_latest(self) -> Optional[dict]:
        return self._last_report

    def get_gaps_summary(self) -> str:
        if not self._last_report:
            return "尚未生成覆盖率报告"
        report = self._last_report
        lines = [
            f"前端API覆盖率: {report['coverage_rate']:.1%} ({report['covered_endpoints']}/{report['total_endpoints']})",
            f"高优先级缺口: {len(report['high_priority_gaps'])}个",
        ]
        for gap in report["high_priority_gaps"][:5]:
            lines.append(f"  [{gap['priority']}] {gap['method']} {gap['path']}")
        return "\n".join(lines)

    def generate_suggestions(self) -> List[dict]:
        if not self._last_report:
            self.generate_report()
        if not self._last_report:
            return []
        report = self._last_report
        suggestions = []
        component_map = {
            "tools": {"tab": "工具", "description": "在工具Tab中添加执行面板"},
            "agent": {"tab": "Agent", "description": "在Agent Tab中添加协作触发"},
            "defense": {"tab": "防御", "description": "在防御Tab中添加操作按钮和详情"},
            "truths": {"tab": "认知", "description": "在认知Tab中添加重组操作"},
            "assessment": {"tab": "评估", "description": "在评估Tab中添加历史趋势"},
            "proactivity": {"tab": "存在层", "description": "在存在层Tab中添加评估按钮"},
            "closed-loop": {"tab": "存在层", "description": "在存在层Tab中添加编排按钮"},
            "memory": {"tab": "记忆", "description": "在记忆Tab中添加搜索和详情"},
            "facts": {"tab": "事实", "description": "在事实Tab中添加搜索和添加"},
            "knowledge-graph": {"tab": "图谱", "description": "在图谱Tab中添加搜索"},
            "events": {"tab": "系统", "description": "在系统Tab中添加事件历史"},
            "trajectory": {"tab": "系统", "description": "在系统Tab中添加轨迹搜索"},
            "forgetting": {"tab": "记忆", "description": "在记忆Tab中添加遗忘评估"},
            "reorganization": {"tab": "认知", "description": "在认知Tab中添加重组操作"},
            "relationship": {"tab": "关系", "description": "在关系Tab中添加指标详情"},
            "presence": {"tab": "存在层", "description": "在存在层Tab中添加信号和状态操作"},
            "attributions": {"tab": "认知", "description": "在认知Tab中添加归因详情"},
            "delta": {"tab": "认知", "description": "在认知Tab中添加增量统计"},
            "module": {"tab": "防御", "description": "在防御Tab中添加模块健康"},
            "evolution": {"tab": "基因", "description": "在基因Tab中添加演化触发"},
            "input-processor": {"tab": "系统", "description": "在系统Tab中添加输入处理演示"},
            "reflection": {"tab": "系统", "description": "在系统Tab中添加反思统计"},
            "background-tasks": {"tab": "系统", "description": "在系统Tab中添加后台任务详情"},
        }
        for gap in report.get("uncovered", []):
            cat = gap.get("category", "")
            comp = component_map.get(cat, {"tab": "全景", "description": f"在全景Tab中添加{cat}相关功能"})
            suggestions.append({
                "endpoint": f"{gap['method']} {gap['path']}",
                "priority": gap["priority"],
                "category": cat,
                "suggested_tab": comp["tab"],
                "suggested_component": comp["description"],
                "effort": "S" if gap["method"] == "GET" else "M",
            })
        suggestions.sort(key=lambda s: 0 if s["priority"] == "P0" else 1 if s["priority"] == "P1" else 2)
        return suggestions

    def auto_generate(self, max_endpoints: int = 10) -> dict:
        """
        元认知闭环第三步：自动生成前端代码补全缺口
        
        R3保障：只生成代码片段，不自动写入文件，需人类审批
        """
        if not self._last_report:
            self.generate_report()
        if not self._last_report:
            return {"error": "无法生成覆盖率报告", "snippets": []}

        uncovered = self._last_report.get("uncovered", [])
        if not uncovered:
            return {"message": "所有端点已覆盖，无需生成", "snippets": []}

        snippets = []
        for gap in uncovered[:max_endpoints]:
            method = gap.get("method", "GET")
            path = gap.get("path", "")
            cat = gap.get("category", "")
            priority = gap.get("priority", "P3")

            snippet = self._generate_snippet(method, path, cat)
            if snippet:
                snippets.append({
                    "endpoint": f"{method} {path}",
                    "priority": priority,
                    "category": cat,
                    "code": snippet,
                    "status": "pending_approval",
                })

        return {
            "total_gaps": len(uncovered),
            "generated": len(snippets),
            "snippets": snippets,
            "warning": "R3: 以下代码需人类审批后方可写入前端文件",
        }

    def _generate_snippet(self, method: str, path: str, category: str) -> str:
        """为单个端点生成前端调用代码片段"""
        func_name = self._path_to_func(method, path)
        
        if method == "GET":
            return (
                f"async function {func_name}() {{\n"
                f"    try {{\n"
                f"        const resp = await fetch('{path}');\n"
                f"        const data = await resp.json();\n"
                f"        if (data.error) {{\n"
                f"            console.warn('{func_name} failed:', data.error);\n"
                f"            return null;\n"
                f"        }}\n"
                f"        return data;\n"
                f"    }} catch (e) {{\n"
                f"        console.warn('{func_name} error:', e);\n"
                f"        return null;\n"
                f"    }}\n"
                f"}}"
            )
        else:
            return (
                f"async function {func_name}(body) {{\n"
                f"    try {{\n"
                f"        const resp = await fetch('{path}', {{\n"
                f"            method: '{method}',\n"
                f"            headers: {{'Content-Type': 'application/json'}},\n"
                f"            body: JSON.stringify(body)\n"
                f"        }});\n"
                f"        const data = await resp.json();\n"
                f"        if (data.error) {{\n"
                f"            console.warn('{func_name} failed:', data.error);\n"
                f"            return null;\n"
                f"        }}\n"
                f"        return data;\n"
                f"    }} catch (e) {{\n"
                f"        console.warn('{func_name} error:', e);\n"
                f"        return null;\n"
                f"    }}\n"
                f"}}"
            )

    def _path_to_func(self, method: str, path: str) -> str:
        """将API路径转换为JavaScript函数名"""
        parts = path.strip("/").replace("api/", "").split("/")
        func_parts = [method.lower()]
        for p in parts:
            if p.startswith("{"):
                p = "by" + p.strip("{}").replace("-", "_").title().replace("_", "")
            func_parts.append(p.replace("-", "_"))
        return "_".join(func_parts)


coverage_auditor = CoverageAuditor()