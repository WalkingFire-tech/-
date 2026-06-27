# -*- coding: utf-8 -*-
"""
/learn 命令实现 - 借鉴Hermes Agent的设计

核心能力：
1. 从任何来源学习（代码、文档、PDF、对话）
2. 蒸馏出可验证、可复用的技能
3. 生成标准化的SKILL.md格式
4. 实时测试验证
5. 固化到技能库

这是"外挂炼丹炉"的高效工程化实现。
"""
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class SkillTemplate:
    """
    技能模板（借鉴Hermes Agent的SKILL.md格式）
    
    标准化格式：
    ---
    name: skill-name
    description: 60字以内简述
    version: 1.0.0
    created_at: 2026-06-27
    ---
    ## When to Use（什么时候用）
    ## Procedure（步骤）
    ## Pitfalls（踩坑记录）
    ## Verification（怎么确认成功）
    """
    
    def __init__(self,
                 name: str,
                 description: str,
                 when_to_use: str,
                 procedure: List[str],
                 pitfalls: List[str] = None,
                 verification: str = ""):
        """
        Args:
            name: 技能名称
            description: 简短描述（60字以内）
            when_to_use: 使用场景
            procedure: 执行步骤列表
            pitfalls: 踩坑记录
            verification: 验证方法
        """
        self.name = name
        self.description = description[:60]  # 限制60字
        self.version = "1.0.0"
        self.created_at = datetime.now().strftime("%Y-%m-%d")
        self.when_to_use = when_to_use
        self.procedure = procedure
        self.pitfalls = pitfalls or []
        self.verification = verification
    
    def to_markdown(self) -> str:
        """转换为SKILL.md格式"""
        md = f"""---
name: {self.name}
description: {self.description}
version: {self.version}
created_at: {self.created_at}
---

## When to Use（什么时候用）

{self.when_to_use}

## Procedure（步骤）

"""
        for i, step in enumerate(self.procedure, 1):
            md += f"{i}. {step}\n"
        
        if self.pitfalls:
            md += "\n## Pitfalls（踩坑记录）\n\n"
            for pitfall in self.pitfalls:
                md += f"- {pitfall}\n"
        
        if self.verification:
            md += f"\n## Verification（怎么确认成功）\n\n{self.verification}\n"
        
        return md
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "created_at": self.created_at,
            "when_to_use": self.when_to_use,
            "procedure": self.procedure,
            "pitfalls": self.pitfalls,
            "verification": self.verification
        }


class LearnCommand:
    """
    /learn 命令实现
    
    核心流程（借鉴Hermes Agent）：
    1. 接收输入（对话、文档、代码等）
    2. 提取关键信息
    3. 生成技能模板
    4. 实时测试验证
    5. 固化到技能库
    """
    
    def __init__(self,
                 skills_dir: str = "data/skills"):
        """
        Args:
            skills_dir: 技能库目录
        """
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("📚 /learn 命令已初始化")
    
    def learn_from_conversation(self,
                               conversation: str,
                               skill_name: Optional[str] = None) -> Dict:
        """
        从对话中学习
        
        Args:
            conversation: 对话内容
            skill_name: 技能名称（可选）
        
        Returns:
            学习结果
        """
        logger.info(f"📖 从对话中学习...")
        
        # 1. 提取关键信息
        extracted = self._extract_knowledge(conversation)
        
        # 2. 生成技能名称
        if not skill_name:
            skill_name = self._generate_skill_name(extracted)
        
        # 3. 创建技能模板
        skill = SkillTemplate(
            name=skill_name,
            description=extracted['description'],
            when_to_use=extracted['when_to_use'],
            procedure=extracted['procedure'],
            pitfalls=extracted.get('pitfalls', []),
            verification=extracted.get('verification', "")
        )
        
        # 4. 验证技能
        validation_result = self._validate_skill(skill)
        
        # 5. 保存到技能库
        if validation_result['valid']:
            self._save_skill(skill)
            
            logger.info(f"✅ 技能已创建: {skill_name}")
            
            return {
                'status': 'success',
                'skill_name': skill_name,
                'skill_file': str(self.skills_dir / f"{skill_name}.md"),
                'validation': validation_result
            }
        else:
            logger.warning(f"⚠️ 技能验证失败: {validation_result['reason']}")
            
            return {
                'status': 'validation_failed',
                'reason': validation_result['reason']
            }
    
    def learn_from_document(self,
                           doc_path: str,
                           focus: Optional[str] = None) -> Dict:
        """
        从文档中学习
        
        Args:
            doc_path: 文档路径
            focus: 关注点（可选）
        
        Returns:
            学习结果
        """
        logger.info(f"📄 从文档中学习: {doc_path}")
        
        # 读取文档
        doc_file = Path(doc_path)
        if not doc_file.exists():
            return {'status': 'error', 'reason': '文件不存在'}
        
        with open(doc_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取关键信息
        extracted = self._extract_from_document(content, focus)
        
        # 生成技能
        skill_name = doc_file.stem
        
        skill = SkillTemplate(
            name=skill_name,
            description=extracted['description'],
            when_to_use=extracted['when_to_use'],
            procedure=extracted['procedure'],
            pitfalls=extracted.get('pitfalls', []),
            verification=extracted.get('verification', "")
        )
        
        # 验证并保存
        validation_result = self._validate_skill(skill)
        
        if validation_result['valid']:
            self._save_skill(skill)
            
            logger.info(f"✅ 技能已创建: {skill_name}")
            
            return {
                'status': 'success',
                'skill_name': skill_name,
                'skill_file': str(self.skills_dir / f"{skill_name}.md"),
                'validation': validation_result
            }
        else:
            return {
                'status': 'validation_failed',
                'reason': validation_result['reason']
            }
    
    def learn_from_correction(self,
                             question: str,
                             wrong_answer: str,
                             correct_answer: str,
                             issues: List[str] = None) -> Dict:
        """
        从纠错中学习
        
        Args:
            question: 问题
            wrong_answer: 错误答案
            correct_answer: 正确答案
            issues: 问题列表
        
        Returns:
            学习结果
        """
        logger.info(f"🔧 从纠错中学习...")
        
        # 提取技能名称
        skill_name = self._extract_skill_name_from_question(question)
        
        # 生成技能
        skill = SkillTemplate(
            name=skill_name,
            description=f"正确回答关于{skill_name}的问题",
            when_to_use=f"当用户询问关于{skill_name}的问题时",
            procedure=[
                f"识别用户关于{skill_name}的问题",
                f"检索相关知识库",
                f"生成结构化的回答",
                f"确保回答包含所有关键要点"
            ],
            pitfalls=issues or [],
            verification=f"回答应包含正确的{skill_name}信息"
        )
        
        # 验证并保存
        validation_result = self._validate_skill(skill)
        
        if validation_result['valid']:
            self._save_skill(skill)
            
            logger.info(f"✅ 技能已创建: {skill_name}")
            
            return {
                'status': 'success',
                'skill_name': skill_name,
                'skill_file': str(self.skills_dir / f"{skill_name}.md"),
                'validation': validation_result
            }
        else:
            return {
                'status': 'validation_failed',
                'reason': validation_result['reason']
            }
    
    def _extract_knowledge(self, conversation: str) -> Dict:
        """从对话中提取知识"""
        # 简化版：提取关键信息
        lines = conversation.split('\n')
        
        # 提取描述（第一行）
        description = lines[0][:60] if lines else "从对话中学习的技能"
        
        # 提取步骤
        procedure = []
        for line in lines:
            if line.strip().startswith(('1.', '2.', '3.', '-', '*')):
                procedure.append(line.strip().lstrip('123456789.-* '))
        
        if not procedure:
            procedure = ["根据对话内容执行相应操作"]
        
        return {
            'description': description,
            'when_to_use': "当需要执行对话中描述的任务时",
            'procedure': procedure[:10],  # 最多10步
            'pitfalls': [],
            'verification': "任务成功完成"
        }
    
    def _extract_from_document(self, content: str, focus: Optional[str]) -> Dict:
        """从文档中提取知识"""
        # 提取标题作为描述
        lines = content.split('\n')
        description = "从文档学习的技能"
        
        for line in lines[:10]:
            if line.startswith('#'):
                description = line.lstrip('# ').strip()[:60]
                break
        
        # 提取步骤（查找列表项）
        procedure = []
        in_list = False
        
        for line in lines:
            if line.strip().startswith(('- ', '* ', '1. ', '2. ', '3. ')):
                procedure.append(line.strip().lstrip('- * 123456789. '))
                in_list = True
            elif in_list and not line.strip():
                break
        
        if not procedure:
            procedure = ["根据文档内容执行相应操作"]
        
        return {
            'description': description,
            'when_to_use': f"当需要使用文档中的知识时" + (f"（关注：{focus}）" if focus else ""),
            'procedure': procedure[:10],
            'pitfalls': [],
            'verification': "操作成功完成"
        }
    
    def _generate_skill_name(self, extracted: Dict) -> str:
        """生成技能名称"""
        # 从描述中提取关键词
        desc = extracted['description']
        
        # 提取中文关键词
        keywords = re.findall(r'[\u4e00-\u9fa5]+', desc)
        
        if keywords:
            return '-'.join(keywords[:3])
        else:
            return f"skill-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    def _extract_skill_name_from_question(self, question: str) -> str:
        """从问题中提取技能名称"""
        # 提取关键词
        keywords = re.findall(r'[\u4e00-\u9fa5]+', question)
        
        if keywords:
            return '-'.join(keywords[:3])
        else:
            return "general-skill"
    
    def _validate_skill(self, skill: SkillTemplate) -> Dict:
        """
        验证技能（实时测试）
        
        Returns:
            {'valid': bool, 'reason': str}
        """
        # 简化版：检查必要字段
        if not skill.name:
            return {'valid': False, 'reason': '技能名称不能为空'}
        
        if not skill.description:
            return {'valid': False, 'reason': '技能描述不能为空'}
        
        if not skill.procedure:
            return {'valid': False, 'reason': '执行步骤不能为空'}
        
        # 验证通过
        return {'valid': True, 'reason': '验证通过'}
    
    def _save_skill(self, skill: SkillTemplate):
        """保存技能到技能库"""
        skill_file = self.skills_dir / f"{skill.name}.md"
        
        with open(skill_file, 'w', encoding='utf-8') as f:
            f.write(skill.to_markdown())
        
        logger.info(f"💾 技能已保存: {skill_file}")
    
    def list_skills(self) -> List[Dict]:
        """列出所有技能"""
        skills = []
        
        for skill_file in self.skills_dir.glob("*.md"):
            with open(skill_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析YAML前置数据
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    yaml_part = parts[1]
                    # 简化解析
                    name_match = re.search(r'name:\s*(.+)', yaml_part)
                    desc_match = re.search(r'description:\s*(.+)', yaml_part)
                    
                    if name_match:
                        skills.append({
                            'name': name_match.group(1).strip(),
                            'description': desc_match.group(1).strip() if desc_match else '',
                            'file': str(skill_file)
                        })
        
        return skills


def test_learn_command():
    """测试/learn命令"""
    print("="*60)
    print("测试 /learn 命令")
    print("="*60)
    print()
    
    learn = LearnCommand()
    
    # 1. 从对话中学习
    print("\n1. 从对话中学习")
    conversation = """
用户: 帮我整理会议笔记
助手: 好的，我会：
1. 提取会议主题
2. 记录参会人员
3. 整理讨论要点
4. 提取待办事项
5. 标记截止日期
"""
    
    result = learn.learn_from_conversation(conversation)
    print(f"   状态: {result['status']}")
    if result['status'] == 'success':
        print(f"   技能: {result['skill_name']}")
        print(f"   文件: {result['skill_file']}")
    
    # 2. 从纠错中学习
    print("\n2. 从纠错中学习")
    result = learn.learn_from_correction(
        question="什么是深度学习的特点？",
        wrong_answer="深度学习的特点包括自动特征提取。",
        correct_answer="深度学习的特点包括：自动特征提取、端到端学习、层次化表示学习、数据驱动与规模效应、可扩展性。",
        issues=["回答过于简略", "缺少关键要点"]
    )
    
    print(f"   状态: {result['status']}")
    if result['status'] == 'success':
        print(f"   技能: {result['skill_name']}")
    
    # 3. 列出所有技能
    print("\n3. 列出所有技能")
    skills = learn.list_skills()
    print(f"   技能数量: {len(skills)}")
    for skill in skills[:5]:
        print(f"   - {skill['name']}: {skill['description'][:30]}...")
    
    print("\n✅ 测试完成")


if __name__ == "__main__":
    test_learn_command()