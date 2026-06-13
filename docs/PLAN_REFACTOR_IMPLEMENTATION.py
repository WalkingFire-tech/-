"""
plan方法拆分 - 子方法实现
这些方法将被添加到planner.py中
"""

# 1. 反射级检查
def _check_reflex_level(self, intent) -> Optional[str]:
    """【反射级】硬编码快速响应（最高优先级）
    
    Returns:
        拦截消息，None表示通过
    """
    try:
        from infrastructure.reflex_engine import reflex_engine
        
        reflex_context = {
            "user_input": intent.raw_text,
            "recent_failures": len(self.failure_history.get(intent.type, []))
        }
        
        try:
            import psutil
            reflex_context["memory_percent"] = psutil.virtual_memory().percent
        except:
            pass
        
        reflex_result = reflex_engine.check(reflex_context)
        if reflex_result:
            logger.warning(f"【反射级】触发拦截")
            return reflex_result
            
    except Exception as e:
        logger.debug(f"反射检查失败: {e}")
    
    return None


# 2. 情绪推断
def _infer_emotion(self, intent) -> Dict:
    """【情绪推断】理解用户状态
    
    Returns:
        情绪推断结果
    """
    try:
        from infrastructure.emotion_inferencer import emotion_inferencer
        
        emotion_result = emotion_inferencer.infer(
            intent.raw_text,
            {"recent_failures": len(self.failure_history.get(intent.type, []))}
        )
        
        if emotion_inferencer.should_simplify_response(emotion_result):
            logger.info(f"用户状态: {emotion_result['emotion']} (耐心: {emotion_result['patience']:.2f})")
        
        return emotion_result
        
    except Exception as e:
        logger.debug(f"情绪推断失败: {e}")
        return {"emotion": "neutral", "patience": 1.0}


# 3. 系统状态检查
def _check_system_state(self) -> Optional[str]:
    """【系统状态检查】健康度+资源检查
    
    Returns:
        状态异常消息，None表示正常
    """
    # 健康度检查
    try:
        from infrastructure.health_dashboard import health_dashboard
        if health_dashboard.should_reduce_load():
            logger.warning(f"系统健康度低，当前模式: {health_dashboard.mode}")
            if health_dashboard.should_request_help():
                return "系统状态不佳，正在自我修复中。部分功能可能受限。"
    except Exception as e:
        logger.debug(f"健康度检查失败: {e}")
    
    # 资源检查
    try:
        from infrastructure.charter_executor import charter_executor
        resource_check = charter_executor.check_resource_limits()
        if not resource_check['within_limits']:
            logger.warning(f"资源超限: {resource_check['violations']}")
            return "系统资源紧张，已暂缓处理。请稍后重试。"
    except:
        pass
    
    return None


# 4. 五层防御机制
def _apply_five_layer_defense(self, intent) -> Optional[str]:
    """【五层防御机制】
    
    第1层: 工具优先调用
    第2层: 任务智能分解（在normal_flow中处理）
    第3层: 知识库检索
    第4层: 主动用户求助（在normal_flow异常中处理）
    第5层: 失败学习机制（在normal_flow异常中处理）
    
    Returns:
        防御层结果，None表示需要进入normal_flow
    """
    # 第1层：工具优先调用
    tool_result = self._try_tool_first(intent)
    if tool_result:
        logger.info(f"【第1层】工具调用成功")
        return tool_result
    
    # 第3层：知识库检索
    knowledge_result = self._try_knowledge_retrieval(intent)
    if knowledge_result:
        logger.info(f"【第3层】知识库命中")
        return knowledge_result
    
    return None


# 5. 重构后的plan方法
def plan_refactored(self, intent):
    """主规划方法 - 清晰的流程编排
    
    流程:
    1. 反射级检查（最高优先级）
    2. 情绪推断（理解用户）
    3. 系统状态检查（自我感知）
    4. 意图路由（特殊意图处理）
    5. 五层防御（智能应对）
    6. 正常流程（常规处理）
    """
    # 1. 反射级检查
    if result := self._check_reflex_level(intent):
        bus.publish("plan_executed", result)
        return
    
    # 2. 情绪推断
    emotion = self._infer_emotion(intent)
    
    # 3. 系统状态检查
    if result := self._check_system_state():
        bus.publish("plan_executed", result)
        return
    
    # 4. 定期归纳检查
    self._check_periodic_induction()
    
    # 5. 意图路由
    if intent.type == "meta":
        logger.info("处理元认知问题")
        response = self._handle_meta_question(intent.raw_text)
        bus.publish("plan_executed", response)
        return
    
    # 6. 五层防御
    if result := self._apply_five_layer_defense(intent):
        bus.publish("plan_executed", result)
        return
    
    # 7. 正常流程
    self._handle_normal_flow(intent, emotion)