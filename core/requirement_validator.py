"""
需求贯穿验证器 - 确保需求核心贯穿始终
"""
import re
from typing import Tuple, List, Dict

class RequirementValidator:
    """需求贯穿验证器"""
    
    def __init__(self):
        self.requirement_chain = []
    
    def extract_core_requirement(self, user_query: str) -> Dict:
        """提取核心需求"""
        
        core = {
            'original_query': user_query,
            'domain': None,
            'key_features': [],
            'constraints': [],
            'intent': None
        }
        
        # 1. 识别领域
        domains = {
            '电池保护': ['电池保护', '保护板', 'BMS', '电池管理'],
            'LED驱动': ['LED', '背光', '屏幕驱动'],
            '充电管理': ['充电', '充电管理', '充电控制'],
            '电源管理': ['电源管理', 'PMIC', '电源控制'],
        }
        
        for domain, keywords in domains.items():
            if any(kw in user_query for kw in keywords):
                core['domain'] = domain
                break
        
        # 2. 提取关键特性
        features = {
            '均衡': ['均衡', '平衡', '电池均衡'],
            '保护': ['保护', '过压', '过流', '短路'],
            '充电': ['充电', '快充', '恒流恒压'],
        }
        
        for feature, keywords in features.items():
            if any(kw in user_query for kw in keywords):
                core['key_features'].append(feature)
        
        # 3. 提取约束条件
        constraints_patterns = [
            (r'(\d+串)', '电池串数'),
            (r'(\d+v)', '电压'),
            (r'(\d+A)', '电流'),
            (r'26650|18650|21700', '电池型号'),
        ]
        
        for pattern, constraint_type in constraints_patterns:
            match = re.search(pattern, user_query, re.IGNORECASE)
            if match:
                core['constraints'].append({
                    'type': constraint_type,
                    'value': match.group(1) if match.lastindex else match.group(0)
                })
        
        # 4. 识别意图
        if '推荐' in user_query or '选型' in user_query:
            core['intent'] = '推荐选型'
        elif '如何' in user_query or '怎么' in user_query:
            core['intent'] = '方法指导'
        elif '为什么' in user_query:
            core['intent'] = '原理解释'
        
        return core
    
    def validate_response_against_requirement(self, 
                                              requirement: Dict, 
                                              response: str) -> Tuple[bool, List[str]]:
        """验证响应是否满足需求"""
        
        issues = []
        
        # 1. 领域匹配验证
        if requirement['domain']:
            # 检查响应中的芯片类型
            chip_types = {
                '电池保护': ['BQ769', 'BQ779', 'SH367', 'RT9428', 'S-82', 'MM3'],
                'LED驱动': ['TPS611', 'LM36', 'ISL976', 'CAT36'],
                '充电管理': ['BQ24', 'BQ25', 'TPS25', 'MP26'],
            }
            
            response_domain = None
            for domain, prefixes in chip_types.items():
                if any(prefix in response for prefix in prefixes):
                    response_domain = domain
                    break
            
            if response_domain and response_domain != requirement['domain']:
                issues.append(f"❌ 领域不匹配: 需求是'{requirement['domain']}'，推荐的是'{response_domain}'")
        
        # 2. 关键特性验证
        for feature in requirement['key_features']:
            if feature == '均衡':
                # 检查响应是否提到均衡功能
                if '均衡' not in response and '平衡' not in response:
                    issues.append(f"❌ 缺少关键特性: '{feature}'")
        
        # 3. 约束条件验证
        for constraint in requirement['constraints']:
            if constraint['type'] == '电池型号':
                # 检查是否适合该电池型号
                if constraint['value'] not in response:
                    issues.append(f"⚠️ 未明确说明适用于{constraint['value']}电池")
        
        is_valid = len(issues) == 0
        return is_valid, issues
    
    def chain_validate(self, user_query: str, response: str, stage: str) -> Dict:
        """链式验证（贯穿整个流程）"""
        
        # 提取需求
        requirement = self.extract_core_requirement(user_query)
        
        # 记录到链
        self.requirement_chain.append({
            'stage': stage,
            'requirement': requirement,
            'response': response
        })
        
        # 验证
        is_valid, issues = self.validate_response_against_requirement(
            requirement, response
        )
        
        return {
            'stage': stage,
            'is_valid': is_valid,
            'issues': issues,
            'requirement': requirement
        }

# 全局实例
requirement_validator = RequirementValidator()

# 测试
if __name__ == "__main__":
    user_query = "推荐一款26650的锂电保护板控制芯片，需要带平衡功能"
    
    # 提取需求
    req = requirement_validator.extract_core_requirement(user_query)
    print("核心需求:")
    print(f"  领域: {req['domain']}")
    print(f"  特性: {req['key_features']}")
    print(f"  约束: {req['constraints']}")
    print(f"  意图: {req['intent']}")
    
    # 验证错误回答
    wrong_response = "推荐使用TPS61182，这款芯片具有内置的平衡电路..."
    is_valid, issues = requirement_validator.validate_response_against_requirement(
        req, wrong_response
    )
    
    print(f"\n验证结果: {'✓ 通过' if is_valid else '✗ 不通过'}")
    for issue in issues:
        print(f"  {issue}")