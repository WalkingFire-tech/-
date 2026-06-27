#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统完整性检查脚本

检查内容：
1. 核心文件是否存在
2. 各模块能否正常运行
3. 数据文件是否完整
4. 配置文件是否正确
5. 文档是否齐全
"""
import sys
from pathlib import Path
from datetime import datetime
import json

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class SystemChecker:
    """系统完整性检查器"""
    
    def __init__(self):
        self.project_root = project_root
        self.results = {
            'check_time': datetime.now().isoformat(),
            'core_files': {},
            'modules': {},
            'data_files': {},
            'config_files': {},
            'docs': {},
            'issues': [],
            'summary': {}
        }
    
    def check_all(self):
        """执行所有检查"""
        print("="*70)
        print("🔍 联盟拓荒者系统完整性检查")
        print("="*70)
        print()
        
        # 1. 检查核心文件
        self._check_core_files()
        
        # 2. 检查模块
        self._check_modules()
        
        # 3. 检查数据文件
        self._check_data_files()
        
        # 4. 检查配置文件
        self._check_config_files()
        
        # 5. 检查文档
        self._check_docs()
        
        # 6. 生成摘要
        self._generate_summary()
        
        # 7. 保存结果
        self._save_results()
        
        # 8. 显示结果
        self._display_results()
    
    def _check_core_files(self):
        """检查核心文件"""
        print("\n【1. 核心文件检查】")
        print("-"*70)
        
        core_files = [
            "main.py",
            "main_integrated.py",
            "start.bat",
            "start_furnace.bat",
            "core/instant_learning.py",
            "core/gold_extractor.py",
            "core/auto_furnace.py",
            "core/furnace_state.py",
            "core/furnace_trainer.py",
            "core/furnace_scheduler.py",
            "core/learn_command.py",
            "core/self_evolution.py",
            "core/skill_tree.py",
            "core/decision_chain.py",
            "core/learning_reflector.py",
            "infrastructure/versioned_fact_store.py",
            "infrastructure/user_correction_flow.py",
            "infrastructure/interaction_data_collector.py"
        ]
        
        for file_path in core_files:
            full_path = self.project_root / file_path
            exists = full_path.exists()
            
            self.results['core_files'][file_path] = {
                'exists': exists,
                'path': str(full_path)
            }
            
            status = "✅" if exists else "❌"
            print(f"   {status} {file_path}")
            
            if not exists:
                self.results['issues'].append(f"核心文件缺失: {file_path}")
    
    def _check_modules(self):
        """检查模块是否能正常导入"""
        print("\n【2. 模块导入检查】")
        print("-"*70)
        
        modules = [
            ("core.instant_learning", "InstantLearningSystem"),
            ("core.gold_extractor", "GoldExtractor"),
            ("core.auto_furnace", "AutoFurnace"),
            ("core.furnace_state", "FurnaceState"),
            ("core.furnace_trainer", "FurnaceTrainer"),
            ("core.furnace_scheduler", "FurnaceScheduler"),
            ("core.learn_command", "LearnCommand"),
            ("core.self_evolution", "SelfEvolutionEngine"),
            ("core.skill_tree", "SkillTree")
        ]
        
        for module_name, class_name in modules:
            try:
                module = __import__(module_name, fromlist=[class_name])
                cls = getattr(module, class_name)
                
                self.results['modules'][module_name] = {
                    'importable': True,
                    'class': class_name
                }
                
                print(f"   ✅ {module_name}.{class_name}")
            except Exception as e:
                self.results['modules'][module_name] = {
                    'importable': False,
                    'error': str(e)
                }
                
                print(f"   ❌ {module_name}.{class_name}: {str(e)[:50]}")
                self.results['issues'].append(f"模块导入失败: {module_name}.{class_name}")
    
    def _check_data_files(self):
        """检查数据文件"""
        print("\n【3. 数据文件检查】")
        print("-"*70)
        
        data_files = {
            "训练数据": "data/sft/combined_all_training_data_v3.jsonl",
            "待学习数据": "data/pending_training.jsonl",
            "纠错数据": "data/corrections/correction_2026-06-27.json",
            "炼丹炉状态": "data/furnace_state.json",
            "即时学习库": "data/fact_assertions_v2.db",
            "学习日志": "logs/instant_learning.json",
            "进化日志": "logs/evolution_log.json"
        }
        
        for name, file_path in data_files.items():
            full_path = self.project_root / file_path
            exists = full_path.exists()
            
            info = {'exists': exists, 'path': str(full_path)}
            
            if exists:
                # 获取文件大小
                size = full_path.stat().st_size
                info['size'] = size
                
                # 如果是JSONL文件，统计行数
                if file_path.endswith('.jsonl'):
                    with open(full_path, 'r', encoding='utf-8') as f:
                        lines = sum(1 for _ in f)
                    info['lines'] = lines
                    print(f"   ✅ {name}: {lines} 行 ({size/1024:.1f} KB)")
                # 如果是JSON文件，统计内容
                elif file_path.endswith('.json'):
                    with open(full_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    info['type'] = type(data).__name__
                    if isinstance(data, list):
                        info['count'] = len(data)
                        print(f"   ✅ {name}: {len(data)} 条 ({size/1024:.1f} KB)")
                    elif isinstance(data, dict):
                        info['keys'] = list(data.keys())
                        print(f"   ✅ {name}: {len(data)} 个键 ({size/1024:.1f} KB)")
                    else:
                        print(f"   ✅ {name}: {size/1024:.1f} KB")
                # 如果是DB文件
                elif file_path.endswith('.db'):
                    import sqlite3
                    conn = sqlite3.connect(full_path)
                    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [row[0] for row in cursor.fetchall()]
                    conn.close()
                    info['tables'] = tables
                    print(f"   ✅ {name}: {len(tables)} 个表 ({size/1024:.1f} KB)")
                else:
                    print(f"   ✅ {name}: {size/1024:.1f} KB")
            else:
                print(f"   ⚠️  {name}: 不存在")
            
            self.results['data_files'][name] = info
    
    def _check_config_files(self):
        """检查配置文件"""
        print("\n【4. 配置文件检查】")
        print("-"*70)
        
        config_files = [
            "config/furnace_config.yaml",
            "config/model_config.json"
        ]
        
        for file_path in config_files:
            full_path = self.project_root / file_path
            exists = full_path.exists()
            
            self.results['config_files'][file_path] = {
                'exists': exists,
                'path': str(full_path)
            }
            
            status = "✅" if exists else "⚠️ "
            print(f"   {status} {file_path}")
    
    def _check_docs(self):
        """检查文档"""
        print("\n【5. 文档检查】")
        print("-"*70)
        
        docs = [
            "docs/PSAA_ARCHITECTURE.md",
            "docs/CHECKPOINT_TRAINING.md",
            "docs/HERMES_REFERENCE.md",
            "docs/LORA_INTEGRATION_REPORT.md",
            "docs/TRAINING_COMPLETE_REPORT.md",
            "README.md"
        ]
        
        for doc_path in docs:
            full_path = self.project_root / doc_path
            exists = full_path.exists()
            
            info = {'exists': exists, 'path': str(full_path)}
            
            if exists:
                size = full_path.stat().st_size
                info['size'] = size
                print(f"   ✅ {doc_path}: {size/1024:.1f} KB")
            else:
                print(f"   ⚠️  {doc_path}: 不存在")
            
            self.results['docs'][doc_path] = info
    
    def _generate_summary(self):
        """生成摘要"""
        # 统计核心文件
        core_ok = sum(1 for v in self.results['core_files'].values() if v['exists'])
        core_total = len(self.results['core_files'])
        
        # 统计模块
        module_ok = sum(1 for v in self.results['modules'].values() if v['importable'])
        module_total = len(self.results['modules'])
        
        # 统计数据文件
        data_ok = sum(1 for v in self.results['data_files'].values() if v['exists'])
        data_total = len(self.results['data_files'])
        
        # 统计文档
        doc_ok = sum(1 for v in self.results['docs'].values() if v['exists'])
        doc_total = len(self.results['docs'])
        
        self.results['summary'] = {
            'core_files': f"{core_ok}/{core_total}",
            'modules': f"{module_ok}/{module_total}",
            'data_files': f"{data_ok}/{data_total}",
            'docs': f"{doc_ok}/{doc_total}",
            'issues_count': len(self.results['issues']),
            'status': '健康' if len(self.results['issues']) == 0 else '有问题'
        }
    
    def _save_results(self):
        """保存检查结果"""
        output_file = self.project_root / "logs" / "system_check.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 检查结果已保存: {output_file}")
    
    def _display_results(self):
        """显示检查结果"""
        print("\n" + "="*70)
        print("📊 检查结果摘要")
        print("="*70)
        
        summary = self.results['summary']
        
        print(f"   核心文件: {summary['core_files']}")
        print(f"   模块导入: {summary['modules']}")
        print(f"   数据文件: {summary['data_files']}")
        print(f"   文档文件: {summary['docs']}")
        print(f"   问题数量: {summary['issues_count']}")
        print(f"   系统状态: {summary['status']}")
        
        if self.results['issues']:
            print("\n⚠️  发现的问题:")
            for issue in self.results['issues']:
                print(f"   - {issue}")
        else:
            print("\n✅ 系统完整性检查通过！")


if __name__ == "__main__":
    checker = SystemChecker()
    checker.check_all()