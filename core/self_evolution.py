# -*- coding: utf-8 -*-
"""
自我进化模块 - 使用Ollama进行本地训练

核心能力：
1. 监控数据积累情况
2. 当数据达到阈值时自动触发训练
3. 使用Ollama进行训练（无需GPU）
4. 自动更新模型权重
5. 持续学习循环

这是"联盟拓荒者"的核心进化机制。
"""
import json
import time
import subprocess
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class SelfEvolutionEngine:
    """
    自我进化引擎（Ollama版本）
    
    让系统具备自我学习能力：
    - 自动监控数据积累
    - 自动触发训练
    - 使用Ollama进行训练
    - 自动更新模型
    - 持续进化
    """
    
    def __init__(self, 
                 data_dir: str = "./data/sft",
                 model_dir: str = "./models/closed_loop_lora",
                 data_threshold: int = 100,
                 training_interval_hours: int = 24,
                 ollama_url: str = "http://localhost:11434"):
        """
        Args:
            data_dir: 训练数据目录
            model_dir: 模型目录
            data_threshold: 数据阈值（达到此数量触发训练）
            training_interval_hours: 训练间隔（小时）
            ollama_url: Ollama服务地址
        """
        self.data_dir = Path(data_dir)
        self.model_dir = Path(model_dir)
        self.data_threshold = data_threshold
        self.training_interval_hours = training_interval_hours
        self.ollama_url = ollama_url
        
        # 进化状态
        self.evolution_log_file = Path("./logs/evolution_log.json")
        self.evolution_log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 加载进化历史
        self.evolution_history = self._load_evolution_history()
        
        logger.info("🧬 自我进化引擎已初始化（Ollama模式）")
        logger.info(f"   数据阈值: {data_threshold} 条")
        logger.info(f"   训练间隔: {training_interval_hours} 小时")
        logger.info(f"   Ollama地址: {ollama_url}")
    
    def _load_evolution_history(self) -> List[Dict]:
        """加载进化历史"""
        if self.evolution_log_file.exists():
            with open(self.evolution_log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _save_evolution_history(self):
        """保存进化历史"""
        with open(self.evolution_log_file, 'w', encoding='utf-8') as f:
            json.dump(self.evolution_history, f, ensure_ascii=False, indent=2)
    
    def check_ollama_available(self) -> bool:
        """检查Ollama是否可用"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def check_data_accumulation(self) -> Dict:
        """
        检查数据积累情况
        
        Returns:
            {
                'total_samples': int,
                'last_training_samples': int,
                'new_samples': int,
                'ready_for_training': bool
            }
        """
        # 查找最新的训练数据文件
        data_files = list(self.data_dir.glob("combined_all_training_data_v*.jsonl"))
        if not data_files:
            data_files = list(self.data_dir.glob("*.jsonl"))
        
        if not data_files:
            return {
                'total_samples': 0,
                'last_training_samples': 0,
                'new_samples': 0,
                'ready_for_training': False
            }
        
        # 统计最新文件的数据量
        latest_file = max(data_files, key=lambda f: f.stat().st_mtime)
        total_samples = 0
        with open(latest_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    total_samples += 1
        
        # 获取上次训练时的数据量
        last_training_samples = 0
        if self.evolution_history:
            last_training_samples = self.evolution_history[-1].get('total_samples', 0)
        
        # 计算新增数据
        new_samples = total_samples - last_training_samples
        
        # 判断是否准备好训练
        ready_for_training = new_samples >= self.data_threshold
        
        result = {
            'total_samples': total_samples,
            'last_training_samples': last_training_samples,
            'new_samples': new_samples,
            'ready_for_training': ready_for_training,
            'data_file': str(latest_file)
        }
        
        logger.info(f"📊 数据积累检查:")
        logger.info(f"   总数据量: {total_samples} 条")
        logger.info(f"   上次训练: {last_training_samples} 条")
        logger.info(f"   新增数据: {new_samples} 条")
        logger.info(f"   准备训练: {'✅ 是' if ready_for_training else '❌ 否'}")
        
        return result
    
    def check_training_time(self) -> bool:
        """
        检查是否到达训练时间
        
        Returns:
            是否应该训练
        """
        if not self.evolution_history:
            return True
        
        last_training_time = self.evolution_history[-1].get('timestamp', '')
        if not last_training_time:
            return True
        
        last_time = datetime.fromisoformat(last_training_time)
        elapsed_hours = (datetime.now() - last_time).total_seconds() / 3600
        
        should_train = elapsed_hours >= self.training_interval_hours
        
        logger.info(f"⏰ 训练时间检查:")
        logger.info(f"   上次训练: {last_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"   距今: {elapsed_hours:.1f} 小时")
        logger.info(f"   应该训练: {'✅ 是' if should_train else '❌ 否'}")
        
        return should_train
    
    def trigger_training_with_ollama(self, data_file: str) -> Dict:
        """
        使用Ollama进行训练
        
        Args:
            data_file: 训练数据文件路径
        
        Returns:
            训练结果
        """
        logger.info("🚀 触发自我训练（Ollama模式）...")
        
        training_start = datetime.now()
        
        # 检查Ollama是否可用
        if not self.check_ollama_available():
            logger.error("❌ Ollama不可用，无法训练")
            return {
                'status': 'failed',
                'error': 'Ollama服务不可用'
            }
        
        # 准备训练数据（转换为Ollama格式）
        training_data = self._prepare_ollama_training_data(data_file)
        
        # 使用Ollama进行微调
        try:
            # 创建Modelfile
            modelfile_path = self._create_modelfile(training_data)
            
            # 创建新模型
            model_name = f"alliance-pioneer-evolved-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            logger.info(f"📝 创建模型: {model_name}")
            
            # 调用Ollama创建模型
            result = subprocess.run(
                ["ollama", "create", model_name, "-f", str(modelfile_path)],
                capture_output=True,
                text=True,
                timeout=600  # 10分钟超时
            )
            
            training_end = datetime.now()
            training_duration = (training_end - training_start).total_seconds()
            
            if result.returncode == 0:
                logger.info(f"✅ 训练成功！模型: {model_name}")
                
                # 记录进化历史
                evolution_record = {
                    'timestamp': training_start.isoformat(),
                    'type': 'auto_training_ollama',
                    'data_file': data_file,
                    'total_samples': self.check_data_accumulation()['total_samples'],
                    'duration_seconds': training_duration,
                    'model_name': model_name,
                    'status': 'success',
                    'output': result.stdout[-500:] if len(result.stdout) > 500 else result.stdout
                }
                
                self.evolution_history.append(evolution_record)
                self._save_evolution_history()
                
                # 更新系统使用的模型
                self._update_system_model(model_name)
                
                return {
                    'status': 'success',
                    'model_name': model_name,
                    'duration': training_duration,
                    'output': result.stdout
                }
            else:
                logger.error(f"❌ 训练失败: {result.stderr}")
                
                evolution_record = {
                    'timestamp': training_start.isoformat(),
                    'type': 'auto_training_ollama',
                    'data_file': data_file,
                    'status': 'failed',
                    'error': result.stderr[-500:] if len(result.stderr) > 500 else result.stderr
                }
                
                self.evolution_history.append(evolution_record)
                self._save_evolution_history()
                
                return {
                    'status': 'failed',
                    'error': result.stderr
                }
                
        except subprocess.TimeoutExpired:
            logger.error("❌ 训练超时")
            return {
                'status': 'timeout',
                'error': '训练超过10分钟未完成'
            }
        except Exception as e:
            logger.error(f"❌ 训练异常: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _prepare_ollama_training_data(self, data_file: str) -> List[Dict]:
        """
        准备Ollama训练数据
        
        Args:
            data_file: 训练数据文件路径
        
        Returns:
            Ollama格式的训练数据
        """
        training_data = []
        
        with open(data_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    # 转换为Ollama格式
                    ollama_item = {
                        'prompt': item['instruction'],
                        'response': item['output']
                    }
                    training_data.append(ollama_item)
        
        logger.info(f"📝 准备训练数据: {len(training_data)} 条")
        
        return training_data
    
    def _create_modelfile(self, training_data: List[Dict]) -> Path:
        """
        创建Ollama Modelfile
        
        Args:
            training_data: 训练数据
        
        Returns:
            Modelfile路径
        """
        # 选择前100条作为训练样本（Ollama限制）
        samples = training_data[:100]
        
        # 构造Modelfile内容
        modelfile_content = f'''# 联盟拓荒者 - 自我进化模型
# 生成时间: {datetime.now().isoformat()}
# 训练样本: {len(samples)} 条

FROM qwen2.5-coder:7b

# 设置参数
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 4096

# 系统提示
SYSTEM 你是联盟拓荒者，一个具备自我进化能力的AI系统。你的核心理念是"学习即存在方式"。

# 训练样本
'''
        
        # 添加训练样本
        for i, sample in enumerate(samples[:20]):  # 最多20个样本
            modelfile_content += f'''
# 样本 {i+1}
MESSAGE user {sample['prompt'][:200]}
MESSAGE assistant {sample['response'][:500]}
'''
        
        # 保存Modelfile
        modelfile_path = Path("./models/modelfile_auto_generated")
        modelfile_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(modelfile_path, 'w', encoding='utf-8') as f:
            f.write(modelfile_content)
        
        logger.info(f"📝 Modelfile已生成: {modelfile_path}")
        
        return modelfile_path
    
    def _update_system_model(self, model_name: str):
        """
        更新系统使用的模型
        
        Args:
            model_name: 新模型名称
        """
        # 更新配置文件
        config_file = Path("./config/model_config.json")
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        config = {
            'current_model': model_name,
            'updated_at': datetime.now().isoformat(),
            'evolution_count': len([e for e in self.evolution_history if e.get('status') == 'success'])
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 系统模型已更新: {model_name}")
    
    def evolve(self) -> Dict:
        """
        执行自我进化
        
        这是核心方法，系统会：
        1. 检查数据积累
        2. 检查训练时间
        3. 如果满足条件，触发训练
        4. 更新模型
        
        Returns:
            进化结果
        """
        logger.info("\n" + "="*60)
        logger.info("🧬 自我进化循环")
        logger.info("="*60)
        
        # 1. 检查数据积累
        data_status = self.check_data_accumulation()
        
        # 2. 检查训练时间
        time_status = self.check_training_time()
        
        # 3. 判断是否应该训练
        should_train = data_status['ready_for_training'] and time_status
        
        if should_train:
            logger.info("\n🎯 满足训练条件，开始自我训练...")
            
            # 触发训练
            training_result = self.trigger_training_with_ollama(data_status['data_file'])
            
            return {
                'action': 'training',
                'data_status': data_status,
                'training_result': training_result
            }
        else:
            logger.info("\n⏸️ 不满足训练条件，继续积累数据...")
            
            return {
                'action': 'wait',
                'data_status': data_status,
                'reason': '数据不足或时间未到'
            }
    
    def get_evolution_summary(self) -> Dict:
        """
        获取进化摘要
        
        Returns:
            {
                'total_evolutions': int,
                'total_samples_trained': int,
                'last_evolution': str,
                'next_evolution_estimate': str
            }
        """
        total_evolutions = len([e for e in self.evolution_history if e.get('type') == 'auto_training_ollama'])
        
        total_samples = 0
        if self.evolution_history:
            total_samples = self.evolution_history[-1].get('total_samples', 0)
        
        last_evolution = '从未训练'
        if self.evolution_history:
            last_time = self.evolution_history[-1].get('timestamp', '')
            if last_time:
                last_evolution = datetime.fromisoformat(last_time).strftime('%Y-%m-%d %H:%M:%S')
        
        # 估算下次训练时间
        next_evolution = '未知'
        if self.evolution_history:
            last_time = datetime.fromisoformat(self.evolution_history[-1].get('timestamp', datetime.now().isoformat()))
            next_time = last_time + timedelta(hours=self.training_interval_hours)
            next_evolution = next_time.strftime('%Y-%m-%d %H:%M:%S')
        
        return {
            'total_evolutions': total_evolutions,
            'total_samples_trained': total_samples,
            'last_evolution': last_evolution,
            'next_evolution_estimate': next_evolution,
            'data_threshold': self.data_threshold,
            'training_interval_hours': self.training_interval_hours
        }


def run_evolution_daemon():
    """
    运行进化守护进程
    
    这是一个持续运行的进程，定期检查并触发训练
    """
    print("="*60)
    print("🧬 联盟拓荒者 - 自我进化守护进程")
    print("="*60)
    print()
    
    # 创建进化引擎
    engine = SelfEvolutionEngine(
        data_threshold=50,  # 每50条新数据训练一次
        training_interval_hours=6  # 每6小时检查一次
    )
    
    # 显示当前状态
    summary = engine.get_evolution_summary()
    print("📊 进化状态:")
    print(f"   总进化次数: {summary['total_evolutions']}")
    print(f"   已训练数据: {summary['total_samples_trained']} 条")
    print(f"   上次进化: {summary['last_evolution']}")
    print(f"   下次进化: {summary['next_evolution_estimate']}")
    print()
    
    # 执行一次进化检查
    result = engine.evolve()
    
    print("\n" + "="*60)
    if result['action'] == 'training':
        print("✅ 本次进化: 已完成训练")
        if 'model_name' in result.get('training_result', {}):
            print(f"   新模型: {result['training_result']['model_name']}")
    else:
        print("⏸️ 本次进化: 继续积累数据")
        print(f"   原因: {result.get('reason', '未知')}")
    print("="*60)
    
    return result


if __name__ == "__main__":
    run_evolution_daemon()
