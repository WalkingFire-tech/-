"""
系统深度诊断工具
检查所有功能模块、漏洞、异常处理、性能瓶颈
"""
import sys
import os
import sqlite3
import asyncio
import traceback
from pathlib import Path
from datetime import datetime
import json

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

class SystemDiagnostics:
    """系统诊断器"""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.info = []
        self.passed = []
    
    def add_issue(self, category, message, severity="high"):
        """添加问题"""
        self.issues.append({
            "category": category,
            "message": message,
            "severity": severity,
            "timestamp": datetime.now().isoformat()
        })
    
    def add_warning(self, category, message):
        """添加警告"""
        self.warnings.append({
            "category": category,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    
    def add_info(self, category, message):
        """添加信息"""
        self.info.append({
            "category": category,
            "message": message
        })
    
    def add_passed(self, category, message):
        """添加通过项"""
        self.passed.append({
            "category": category,
            "message": message
        })
    
    # ========== 1. 数据库完整性检查 ==========
    def check_databases(self):
        """检查数据库完整性"""
        print("\n" + "="*60)
        print("1. 数据库完整性检查")
        print("="*60)
        
        db_files = list(Path("data").glob("*.db"))
        
        for db_file in db_files:
            try:
                conn = sqlite3.connect(str(db_file))
                cursor = conn.cursor()
                
                # 检查完整性
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()[0]
                
                if result == "ok":
                    self.add_passed("数据库", f"{db_file.name}: 完整性检查通过")
                    print(f"  ✓ {db_file.name}: 完整性OK")
                else:
                    self.add_issue("数据库", f"{db_file.name}: 完整性检查失败 - {result}")
                    print(f"  ✗ {db_file.name}: 完整性失败 - {result}")
                
                # 检查表结构
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        self.add_info("数据库", f"{db_file.name}.{table}: {count}条记录")
                    except Exception as e:
                        self.add_issue("数据库", f"{db_file.name}.{table}: 无法查询 - {e}")
                
                conn.close()
                
            except Exception as e:
                self.add_issue("数据库", f"{db_file.name}: 无法连接 - {e}")
                print(f"  ✗ {db_file.name}: 连接失败 - {e}")
    
    # ========== 2. 核心模块导入检查 ==========
    def check_modules(self):
        """检查核心模块导入"""
        print("\n" + "="*60)
        print("2. 核心模块导入检查")
        print("="*60)
        
        critical_modules = [
            "core.services.planner",
            "core.services.intent_parser",
            "core.learning_engine",
            "core.folder_learner",
            "core.vector_retriever",
            "adapters.llm.ollama_adapter",
            "infrastructure.event_bus",
            "infrastructure.logger",
        ]
        
        for module_name in critical_modules:
            try:
                __import__(module_name)
                self.add_passed("模块", f"{module_name}: 导入成功")
                print(f"  ✓ {module_name}")
            except Exception as e:
                self.add_issue("模块", f"{module_name}: 导入失败 - {e}", severity="critical")
                print(f"  ✗ {module_name}: {e}")
    
    # ========== 3. 异常处理检查 ==========
    def check_exception_handling(self):
        """检查异常处理"""
        print("\n" + "="*60)
        print("3. 异常处理检查")
        print("="*60)
        
        # 检查关键文件中的异常处理
        critical_files = [
            "backend/main.py",
            "core/services/planner.py",
            "core/learning_engine.py",
            "adapters/llm/ollama_adapter.py",
        ]
        
        for file_path in critical_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 检查裸except
                bare_except_count = content.count("except:")
                if bare_except_count > 0:
                    self.add_warning("异常处理", f"{file_path}: 发现{bare_except_count}个裸except（应指定异常类型）")
                    print(f"  ⚠ {file_path}: {bare_except_count}个裸except")
                
                # 检查except pass
                except_pass_count = content.count("except") and content.count("pass")
                if except_pass_count:
                    self.add_warning("异常处理", f"{file_path}: 发现except pass（可能隐藏错误）")
                    print(f"  ⚠ {file_path}: 发现except pass")
                
                # 检查try块数量
                try_count = content.count("try:")
                self.add_info("异常处理", f"{file_path}: {try_count}个try块")
                
                if bare_except_count == 0:
                    self.add_passed("异常处理", f"{file_path}: 无裸except")
                
            except Exception as e:
                self.add_warning("异常处理", f"无法检查 {file_path}: {e}")
    
    # ========== 4. 安全漏洞检查 ==========
    def check_security(self):
        """检查安全漏洞"""
        print("\n" + "="*60)
        print("4. 安全漏洞检查")
        print("="*60)
        
        # 检查敏感信息泄露
        sensitive_patterns = [
            ("password", "密码硬编码"),
            ("api_key", "API密钥硬编码"),
            ("secret", "密钥硬编码"),
            ("token", "令牌硬编码"),
        ]
        
        python_files = list(Path(".").rglob("*.py"))
        
        for file_path in python_files[:50]:  # 限制检查数量
            if "test_" in str(file_path) or "__pycache__" in str(file_path):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                for pattern, desc in sensitive_patterns:
                    # 检查是否硬编码（排除环境变量读取）
                    if f'{pattern} = "' in content or f"{pattern} = '" in content:
                        if "os.environ" not in content and "getenv" not in content:
                            self.add_warning("安全", f"{file_path}: {desc}")
                            print(f"  ⚠ {file_path}: {desc}")
                
            except:
                pass
        
        # 检查SQL注入风险
        for file_path in python_files[:50]:
            if "test_" in str(file_path):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # 检查字符串拼接SQL
                if "execute(" in content and "f\"" in content:
                    if "SELECT" in content or "INSERT" in content or "UPDATE" in content:
                        self.add_warning("安全", f"{file_path}: 可能存在SQL注入风险（字符串拼接SQL）")
                        print(f"  ⚠ {file_path}: 可能SQL注入风险")
                
            except:
                pass
        
        self.add_passed("安全", "基础安全检查完成")
    
    # ========== 5. 性能瓶颈检查 ==========
    def check_performance(self):
        """检查性能瓶颈"""
        print("\n" + "="*60)
        print("5. 性能瓶颈检查")
        print("="*60)
        
        # 检查数据库索引
        db_path = Path("data/knowledge_store.db")
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # 检查knowledge表的索引
            cursor.execute("PRAGMA index_list(knowledge)")
            indexes = cursor.fetchall()
            
            if len(indexes) < 3:
                self.add_warning("性能", f"knowledge表索引不足（{len(indexes)}个），建议添加索引")
                print(f"  ⚠ knowledge表索引不足: {len(indexes)}个")
            else:
                self.add_passed("性能", f"knowledge表有{len(indexes)}个索引")
                print(f"  ✓ knowledge表索引: {len(indexes)}个")
            
            conn.close()
        
        # 检查大文件处理
        python_files = list(Path(".").rglob("*.py"))
        for file_path in python_files[:30]:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # 检查一次性读取大文件
                if ".read()" in content and "chunk" not in content:
                    self.add_warning("性能", f"{file_path}: 可能一次性读取大文件（建议分块读取）")
                
            except:
                pass
        
        self.add_passed("性能", "性能检查完成")
    
    # ========== 6. 配置检查 ==========
    def check_config(self):
        """检查配置"""
        print("\n" + "="*60)
        print("6. 配置检查")
        print("="*60)
        
        config_file = Path("config/settings.yaml")
        if config_file.exists():
            try:
                import yaml
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                # 检查超时设置
                if "timeout" in str(config):
                    timeout = config.get("timeout", {})
                    if timeout.get("default") == 0 or timeout.get("default") is None:
                        self.add_info("配置", "超时已禁用（支持长时间思考）")
                        print("  ℹ 超时已禁用")
                
                # 检查并发设置
                if "parallel" in str(config):
                    parallel = config.get("parallel", {})
                    max_workers = parallel.get("max_workers", 1)
                    if max_workers > 10:
                        self.add_warning("配置", f"并发数过高（{max_workers}），可能导致资源耗尽")
                        print(f"  ⚠ 并发数: {max_workers}")
                
                self.add_passed("配置", "配置文件正常")
                print("  ✓ 配置文件正常")
                
            except Exception as e:
                self.add_issue("配置", f"配置文件解析失败: {e}")
                print(f"  ✗ 配置解析失败: {e}")
        else:
            self.add_issue("配置", "配置文件不存在")
            print("  ✗ 配置文件不存在")
    
    # ========== 7. API端点检查 ==========
    def check_api_endpoints(self):
        """检查API端点"""
        print("\n" + "="*60)
        print("7. API端点检查")
        print("="*60)
        
        try:
            import requests
            
            # 测试关键端点
            endpoints = [
                ("/api/health", "GET", None, "健康检查"),
                ("/api/stats", "GET", None, "统计信息"),
                ("/api/models", "GET", None, "模型列表"),
                ("/api/knowledge/health", "GET", None, "知识健康度"),
            ]
            
            for endpoint, method, data, desc in endpoints:
                try:
                    if method == "GET":
                        response = requests.get(f"http://localhost:8000{endpoint}", timeout=5)
                    else:
                        response = requests.post(f"http://localhost:8000{endpoint}", json=data, timeout=5)
                    
                    if response.status_code == 200:
                        self.add_passed("API", f"{endpoint}: {desc}正常")
                        print(f"  ✓ {endpoint}: {desc}")
                    else:
                        self.add_warning("API", f"{endpoint}: 状态码{response.status_code}")
                        print(f"  ⚠ {endpoint}: {response.status_code}")
                
                except requests.exceptions.Timeout:
                    self.add_warning("API", f"{endpoint}: 超时")
                    print(f"  ⚠ {endpoint}: 超时")
                except Exception as e:
                    self.add_warning("API", f"{endpoint}: {e}")
                    print(f"  ⚠ {endpoint}: {e}")
        
        except ImportError:
            self.add_warning("API", "requests库未安装")
            print("  ⚠ requests库未安装")
    
    # ========== 8. 内存和资源检查 ==========
    def check_resources(self):
        """检查内存和资源"""
        print("\n" + "="*60)
        print("8. 内存和资源检查")
        print("="*60)
        
        try:
            import psutil
            
            # 内存使用
            memory = psutil.virtual_memory()
            if memory.percent > 80:
                self.add_warning("资源", f"内存使用率过高: {memory.percent}%")
                print(f"  ⚠ 内存使用: {memory.percent}%")
            else:
                self.add_passed("资源", f"内存使用正常: {memory.percent}%")
                print(f"  ✓ 内存使用: {memory.percent}%")
            
            # CPU使用
            cpu = psutil.cpu_percent(interval=1)
            if cpu > 80:
                self.add_warning("资源", f"CPU使用率过高: {cpu}%")
                print(f"  ⚠ CPU使用: {cpu}%")
            else:
                self.add_passed("资源", f"CPU使用正常: {cpu}%")
                print(f"  ✓ CPU使用: {cpu}%")
            
            # 磁盘使用
            disk = psutil.disk_usage('.')
            if disk.percent > 90:
                self.add_warning("资源", f"磁盘使用率过高: {disk.percent}%")
                print(f"  ⚠ 磁盘使用: {disk.percent}%")
            else:
                self.add_passed("资源", f"磁盘使用正常: {disk.percent}%")
                print(f"  ✓ 磁盘使用: {disk.percent}%")
        
        except ImportError:
            self.add_info("资源", "psutil库未安装，跳过资源检查")
            print("  ℹ psutil未安装")
    
    # ========== 9. 依赖检查 ==========
    def check_dependencies(self):
        """检查依赖"""
        print("\n" + "="*60)
        print("9. 依赖检查")
        print("="*60)
        
        required_packages = [
            "fastapi",
            "uvicorn",
            "loguru",
            "requests",
            "pyyaml",
            "fitz",  # PyMuPDF
            "numpy",
            "faiss",  # faiss-cpu
        ]
        
        for package in required_packages:
            try:
                __import__(package)
                self.add_passed("依赖", f"{package}: 已安装")
                print(f"  ✓ {package}")
            except ImportError:
                self.add_warning("依赖", f"{package}: 未安装")
                print(f"  ⚠ {package}: 未安装")
    
    # ========== 10. 日志检查 ==========
    def check_logs(self):
        """检查日志"""
        print("\n" + "="*60)
        print("10. 日志检查")
        print("="*60)
        
        log_file = Path("data/campfire_log.txt")
        if log_file.exists():
            try:
                # 检查最近的错误日志
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()[-100:]  # 最后100行
                
                error_count = sum(1 for line in lines if "ERROR" in line or "Exception" in line)
                warning_count = sum(1 for line in lines if "WARNING" in line)
                
                if error_count > 10:
                    self.add_warning("日志", f"最近有{error_count}个错误日志")
                    print(f"  ⚠ 错误日志: {error_count}个")
                else:
                    self.add_passed("日志", f"错误日志数量正常: {error_count}个")
                    print(f"  ✓ 错误日志: {error_count}个")
                
                self.add_info("日志", f"警告日志: {warning_count}个")
                print(f"  ℹ 警告日志: {warning_count}个")
                
            except Exception as e:
                self.add_warning("日志", f"无法读取日志: {e}")
        else:
            self.add_info("日志", "日志文件不存在")
    
    # ========== 生成报告 ==========
    def generate_report(self):
        """生成诊断报告"""
        print("\n" + "="*60)
        print("诊断报告")
        print("="*60)
        
        print(f"\n✅ 通过项: {len(self.passed)}")
        print(f"⚠️  警告项: {len(self.warnings)}")
        print(f"❌ 问题项: {len(self.issues)}")
        
        if self.issues:
            print("\n" + "="*60)
            print("❌ 严重问题（需立即修复）")
            print("="*60)
            for issue in self.issues:
                print(f"\n[{issue['category']}] {issue['severity'].upper()}")
                print(f"  {issue['message']}")
        
        if self.warnings:
            print("\n" + "="*60)
            print("⚠️  警告（建议优化）")
            print("="*60)
            for warning in self.warnings[:20]:  # 限制显示数量
                print(f"\n[{warning['category']}]")
                print(f"  {warning['message']}")
        
        # 保存报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "passed": len(self.passed),
                "warnings": len(self.warnings),
                "issues": len(self.issues)
            },
            "issues": self.issues,
            "warnings": self.warnings,
            "passed": self.passed,
            "info": self.info
        }
        
        with open("diagnostic_report.json", 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 详细报告已保存: diagnostic_report.json")
        
        return len(self.issues) == 0


def main():
    """主函数"""
    diagnostics = SystemDiagnostics()
    
    # 执行所有检查
    diagnostics.check_databases()
    diagnostics.check_modules()
    diagnostics.check_exception_handling()
    diagnostics.check_security()
    diagnostics.check_performance()
    diagnostics.check_config()
    diagnostics.check_api_endpoints()
    diagnostics.check_resources()
    diagnostics.check_dependencies()
    diagnostics.check_logs()
    
    # 生成报告
    success = diagnostics.generate_report()
    
    if success:
        print("\n✅ 系统诊断完成：无严重问题")
    else:
        print("\n⚠️ 系统诊断完成：发现问题，请查看报告")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)