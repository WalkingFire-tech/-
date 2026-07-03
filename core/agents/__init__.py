"""
多Agent协作框架 - P2-4

三角色协作：PlannerAgent → ExecutorAgent → ReflectorAgent
通过EventBus事件驱动通信，形成 Plan→Execute→Reflect→(Replan) 闭环
"""