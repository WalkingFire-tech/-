"""
真正的学习闭环 - 从失败中学习
核心逻辑：
1. 检测能力不足（置信度低、质量差、失败）
2. 触发搜索学习
3. 分析对比搜索结果
4. 存储高质量知识
5. 形成学习闭环
"""
from infrastructure.database_manager import DatabaseManager
import json
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger


class LearningLoop:
    """学习闭环管理器"""
    
    def __init__(self, db_path: str = "data/knowledge_store.db"):
        self.db_path = db_path
    
    def detect_capability_gap(self, 
                              question: str, 
                              answer: str = None,
                              confidence: float = 0.0,
                              quality_score: float = 0.0,
                              error: str = None) -> Dict:
        """
        检测能力不足
        
        返回: {
            "has_gap": bool,
            "gap_type": str,  # "low_confidence" | "low_quality" | "failure" | "unknown_topic"
            "severity": float,  # 0-1, 严重程度
            "learning_priority": str  # "high" | "medium" | "low"
        }
        """
        result = {
            "has_gap": False,
            "gap_type": None,
            "severity": 0.0,
            "learning_priority": "low"
        }
        
        # 1. 检查是否失败
        if error or not answer:
            result.update({
                "has_gap": True,
                "gap_type": "failure",
                "severity": 1.0,
                "learning_priority": "high"
            })
            return result
        
        # 2. 检查置信度
        if confidence < 0.5:
            result.update({
                "has_gap": True,
                "gap_type": "low_confidence",
                "severity": 1.0 - confidence,
                "learning_priority": "high" if confidence < 0.3 else "medium"
            })
            return result
        
        # 3. 检查质量
        if quality_score < 50:
            result.update({
                "has_gap": True,
                "gap_type": "low_quality",
                "severity": 1.0 - quality_score/100,
                "learning_priority": "high" if quality_score < 30 else "medium"
            })
            return result
        
        # 4. 检查知识库是否有相关知识
        try:
            db = DatabaseManager.get(self.db_path)
            knowledge_count = db.query_one(
                'SELECT COUNT(*) FROM knowledge_items WHERE question LIKE ? OR answer LIKE ?',
                (f'%{question[:30]}%', f'%{question[:30]}%')
            )[0]
            
            if knowledge_count == 0:
                result.update({
                    "has_gap": True,
                    "gap_type": "unknown_topic",
                    "severity": 0.5,
                    "learning_priority": "medium"
                })
        except:
            pass
        
        return result
    
    def trigger_learning(self,
                        question: str,
                        gap_info: Dict,
                        context: Dict = None) -> Dict:
        """
        触发学习
        
        返回: {
            "success": bool,
            "knowledge_gained": int,
            "sources": List[str],
            "analysis": str
        }
        """
        result = {
            "success": False,
            "knowledge_gained": 0,
            "sources": [],
            "analysis": ""
        }
        
        if not gap_info["has_gap"]:
            return result
        
        logger.info(f"🔍 检测到能力不足: {gap_info['gap_type']}, 优先级: {gap_info['learning_priority']}")
        logger.info(f"📚 触发学习: {question[:50]}...")
        
        # 1. 搜索学习
        search_results = self._search_and_learn(question)
        
        # 2. 分析对比
        analysis = self._analyze_and_compare(question, search_results)
        
        # 3. 存储知识
        saved_count = self._save_knowledge(question, search_results, analysis, gap_info)
        
        # 4. 生成学习规则
        self._generate_learning_rule(question, gap_info, saved_count)
        
        result.update({
            "success": saved_count > 0,
            "knowledge_gained": saved_count,
            "sources": [sr.get('href', 'unknown') for sr in search_results],
            "analysis": analysis
        })
        
        logger.info(f"✅ 学习完成: 获得{saved_count}条知识")
        
        return result
    
    def _search_and_learn(self, question: str) -> List[Dict]:
        """搜索并学习"""
        results = []
        
        # 尝试新包名
        try:
            from ddgs import DDGS
            
            with DDGS() as ddgs:
                search_results = list(ddgs.text(question, max_results=5))
            
            for sr in search_results:
                results.append({
                    'title': sr.get('title', ''),
                    'body': sr.get('body', ''),
                    'href': sr.get('href', ''),
                    'source': 'duckduckgo'
                })
            
            logger.info(f"✅ DuckDuckGo搜索获得{len(results)}条结果")
            return results
            
        except Exception as e:
            logger.debug(f"ddgs包失败: {e}")
        
        # 尝试旧包名
        try:
            from ddgs import DDGS
            
            with DDGS() as ddgs:
                search_results = list(ddgs.text(question, max_results=5))
            
            for sr in search_results:
                results.append({
                    'title': sr.get('title', ''),
                    'body': sr.get('body', ''),
                    'href': sr.get('href', ''),
                    'source': 'duckduckgo_old'
                })
            
            logger.info(f"✅ DuckDuckGo(旧)搜索获得{len(results)}条结果")
            return results
            
        except Exception as e:
            logger.warning(f"搜索失败: {e}")
        
        return results
    
    def _analyze_and_compare(self, question: str, search_results: List[Dict]) -> str:
        """分析对比搜索结果"""
        if not search_results:
            return "无搜索结果可供分析"
        
        # 提取关键信息
        analysis_parts = []
        analysis_parts.append(f"关于'{question[:30]}'的学习分析：\n")
        
        # 对比不同来源的信息
        for i, sr in enumerate(search_results[:3], 1):
            analysis_parts.append(f"\n【来源{i}】{sr.get('title', '未知')}")
            analysis_parts.append(f"摘要: {sr.get('body', '')[:200]}...")
            analysis_parts.append(f"链接: {sr.get('href', '')}")
        
        # 归纳总结
        analysis_parts.append("\n\n【学习总结】")
        titles = [sr.get('title', '') for sr in search_results[:3]]
        analysis_parts.append(f"相关主题: {', '.join(titles)}")
        
        analysis = '\n'.join(analysis_parts)
        return analysis
    
    def _save_knowledge(self, 
                       question: str,
                       search_results: List[Dict],
                       analysis: str,
                       gap_info: Dict) -> int:
        """存储知识"""
        saved_count = 0
        
        try:
            db = DatabaseManager.get(self.db_path)
            for sr in search_results:
                answer = f"{sr.get('title', '')}\n\n{sr.get('body', '')}"
                source = sr.get('href', 'search_learned')
                
                db.execute('''
                    INSERT INTO knowledge_items 
                    (question, answer, source, knowledge_type, quality_score, created_at)
                    VALUES (?, ?, ?, 'search_learned', 50.0, ?)
                ''', (question, answer, source, datetime.now().isoformat()), commit=True)
                saved_count += 1
            
            if analysis:
                db.execute('''
                    INSERT INTO knowledge_items 
                    (question, answer, source, knowledge_type, quality_score, created_at)
                    VALUES (?, ?, 'analysis', 'learning_analysis', 60.0, ?)
                ''', (f"{question} - 学习分析", analysis, datetime.now().isoformat()), commit=True)
                saved_count += 1
                
        except Exception as e:
            logger.error(f"存储知识失败: {e}")
        
        return saved_count
    
    def _generate_learning_rule(self, 
                               question: str,
                               gap_info: Dict,
                               saved_count: int) -> None:
        """生成学习规则"""
        if saved_count == 0:
            return
        
        try:
            # 提取关键词
            import re
            keywords = re.findall(r'\w+', question.lower())
            keywords = [k for k in keywords if len(k) > 3][:3]
            
            if not keywords:
                return
            
            db = DatabaseManager.get(self.db_path)
            existing = db.query_one(
                'SELECT 1 FROM learning_rules WHERE trigger_pattern LIKE ?',
                (f'%{keywords[0]}%',)
            )
            
            if not existing:
                db.execute('''
                    INSERT INTO learning_rules 
                    (trigger_pattern, action, confidence, source, created_at)
                    VALUES (?, ?, ?, 'auto_learned', ?)
                ''', (
                    f"问题包含'{keywords[0]}'",
                    f"优先搜索学习关于'{keywords[0]}'的知识",
                    0.7,
                    datetime.now().isoformat()
                ), commit=True)
                logger.info(f"生成学习规则: {keywords[0]}")
                    
        except Exception as e:
            logger.error(f"生成学习规则失败: {e}")


# 全局学习闭环实例
learning_loop = LearningLoop()


def check_and_learn(question: str,
                   answer: str = None,
                   confidence: float = 0.0,
                   quality_score: float = 0.0,
                   error: str = None) -> Dict:
    """
    检查能力不足并触发学习的便捷函数
    """
    # 1. 检测能力不足
    gap_info = learning_loop.detect_capability_gap(
        question=question,
        answer=answer,
        confidence=confidence,
        quality_score=quality_score,
        error=error
    )
    
    # 2. 触发学习
    if gap_info["has_gap"]:
        return learning_loop.trigger_learning(question, gap_info)
    
    return {"success": False, "knowledge_gained": 0, "message": "无能力不足"}