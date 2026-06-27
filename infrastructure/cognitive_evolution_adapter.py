"""
v2.0认知进化架构适配器
将六层认知进化架构集成到现有系统
"""
from typing import Dict, Any, Optional
from loguru import logger

try:
    from core.cognitive_architecture_v2 import cognitive_architecture
    V2_AVAILABLE = True
except Exception as e:
    V2_AVAILABLE = False
    logger.warning(f"v2.0认知架构加载失败: {e}")


class CognitiveEvolutionAdapter:
    """
    v2.0认知进化架构适配器
    
    功能：
    1. 将v2.0架构集成到现有系统
    2. 转换数据格式
    3. 提供增强功能
    """
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled and V2_AVAILABLE
        
        if self.enabled:
            logger.info("✅ v2.0认知进化架构已启用")
        else:
            logger.info("⚠️ v2.0认知进化架构未启用")
    
    def enhance(
        self,
        text: str,
        existing_result: Optional[Dict] = None,
        enable_evolution: bool = True
    ) -> Dict[str, Any]:
        """
        用v2.0架构增强现有结果
        
        Args:
            text: 用户输入
            existing_result: 现有处理结果（可选）
            enable_evolution: 是否启用进化处理
        
        Returns:
            增强后的结果
        """
        if not self.enabled or not enable_evolution:
            return existing_result or {}
        
        try:
            # 调用v2.0架构
            v2_result = cognitive_architecture.process(text)
            
            # 构建增强结果
            enhanced = {
                'original': existing_result,
                'evolution': {
                    'is_valid': v2_result.get('is_valid', False),
                    'status': v2_result.get('status', 'unknown'),
                    'user_friendly_output': v2_result.get('user_friendly_output', ''),
                    'thinking_chain': self._simplify_thinking_chain(
                        v2_result.get('thinking_chain', [])
                    ),
                    'diagnosis': v2_result.get('meta', {})
                }
            }
            
            # 如果v2.0校验失败，添加警告
            if not v2_result.get('is_valid', True):
                enhanced['warning'] = "⚠️ v2.0架构检测到潜在问题，建议人工确认"
            
            return enhanced
            
        except Exception as e:
            logger.error(f"v2.0架构处理失败: {e}")
            return existing_result or {}
    
    def process_standalone(self, text: str) -> Dict[str, Any]:
        """
        独立处理（不依赖现有结果）
        
        Args:
            text: 用户输入
        
        Returns:
            v2.0处理结果
        """
        if not self.enabled:
            return {
                'is_valid': False,
                'solution': 'v2.0架构未启用',
                'status': 'disabled'
            }
        
        try:
            result = cognitive_architecture.process(text)
            
            return {
                'is_valid': result.get('is_valid', False),
                'solution': result.get('solution', ''),
                'user_friendly_output': result.get('user_friendly_output', ''),
                'status': result.get('status', 'unknown'),
                'thinking_chain': result.get('thinking_chain', []),
                'diagnosis': result.get('meta', {})
            }
            
        except Exception as e:
            logger.error(f"v2.0独立处理失败: {e}")
            return {
                'is_valid': False,
                'solution': f'处理失败: {str(e)}',
                'status': 'error'
            }
    
    def _simplify_thinking_chain(self, chain: list) -> list:
        """简化思考链（只保留关键信息）"""
        
        simplified = []
        
        for layer_name, layer_result in chain:
            if isinstance(layer_result, dict):
                simplified.append({
                    'layer': layer_name,
                    'declaration': layer_result.get('declaration', ''),
                    'status': layer_result.get('status', 'unknown')
                })
        
        return simplified
    
    def get_evolution_stats(self) -> Dict[str, Any]:
        """获取进化统计"""
        
        if not self.enabled:
            return {'enabled': False}
        
        try:
            stats = cognitive_architecture.get_evolution_stats()
            stats['enabled'] = True
            return stats
        except:
            return {'enabled': False, 'error': '获取统计失败'}
    
    def get_diagnosis(self) -> Dict[str, Any]:
        """获取系统诊断"""
        
        if not self.enabled:
            return {'status': 'disabled', 'message': 'v2.0架构未启用'}
        
        try:
            return cognitive_architecture.get_diagnosis()
        except:
            return {'status': 'error', 'message': '诊断失败'}
    
    def should_use_evolution(self, text: str) -> bool:
        """
        判断是否应该使用进化架构
        
        Args:
            text: 用户输入
        
        Returns:
            是否使用进化架构
        """
        if not self.enabled:
            return False
        
        # 触发关键词
        evolution_keywords = [
            '推荐', '选型', '芯片', 'IC',
            '反思', '历史', '回顾',
            '电池', '保护', '均衡',
            '不确定', '不确定'
        ]
        
        # 检查是否包含关键词
        for keyword in evolution_keywords:
            if keyword in text:
                return True
        
        return False


# 全局实例
cognitive_evolution_adapter = CognitiveEvolutionAdapter()


# 测试
if __name__ == "__main__":
    print("=" * 70)
    print("v2.0认知进化架构适配器测试")
    print("=" * 70)
    
    adapter = CognitiveEvolutionAdapter()
    
    # 测试1：独立处理
    print("\n[测试1] 独立处理")
    result = adapter.process_standalone("推荐一款26650的锂电保护板控制芯片")
    print(f"状态: {result['status']}")
    print(f"有效: {result['is_valid']}")
    print(f"输出: {result['user_friendly_output'][:100]}...")
    
    # 测试2：增强现有结果
    print("\n[测试2] 增强现有结果")
    existing = {
        'analysis': {'core_need': '芯片推荐'},
        'subtasks': ['检索芯片', '验证匹配']
    }
    enhanced = adapter.enhance("推荐一款26650的锂电保护板控制芯片", existing)
    print(f"原始结果: {existing}")
    print(f"增强结果: {enhanced.get('evolution', {}).get('status')}")
    
    # 测试3：进化统计
    print("\n[测试3] 进化统计")
    stats = adapter.get_evolution_stats()
    print(f"统计: {stats}")
    
    # 测试4：系统诊断
    print("\n[测试4] 系统诊断")
    diagnosis = adapter.get_diagnosis()
    print(f"诊断: {diagnosis}")
    
    print("\n✅ 适配器测试完成")