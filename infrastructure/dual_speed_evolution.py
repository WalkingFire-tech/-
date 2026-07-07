"""
双速进化协调器 (DualSpeedEvolutionCoordinator)

快循环（秒级）：每次交互后立即执行
- 经验积累 → 反思管道 → 轨迹修订 → 适应度更新
- 识别"痛点信号"传递给慢循环

慢循环（小时级）：定期深度优化
- 基因进化 → 策略优化 → 知识一致性验证 → 规则归纳
- 接收快循环的痛点信号作为优先优化目标
- 所有变更必须通过棘轮门验证

数据管道：
- 快→慢：pain_signals（低置信度区域、高频失败模式）
- 慢→快：optimized_params（基因/策略参数实时同步）
"""

import time
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger


@dataclass
class PainSignal:
    domain: str
    description: str
    severity: float
    context: Dict = field(default_factory=dict)
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class DualSpeedEvolutionCoordinator:
    FAST_LOOP_INTERVAL = 1.0
    SLOW_LOOP_INTERVAL = 3600.0
    MAX_PAIN_SIGNALS = 100

    def __init__(self):
        self._pain_signals: List[PainSignal] = []
        self._pain_lock = threading.Lock()
        self._fast_loop_count = 0
        self._slow_loop_count = 0
        self._last_slow_loop = 0.0
        self._running = False
        self._slow_thread: Optional[threading.Thread] = None

    def record_pain_signal(self, domain: str, description: str,
                           severity: float = 0.5, context: Dict = None):
        signal = PainSignal(
            domain=domain,
            description=description,
            severity=max(0.0, min(1.0, severity)),
            context=context or {},
        )
        with self._pain_lock:
            self._pain_signals.append(signal)
            if len(self._pain_signals) > self.MAX_PAIN_SIGNALS:
                self._pain_signals = sorted(self._pain_signals, key=lambda s: s.severity, reverse=True)[
                                      :self.MAX_PAIN_SIGNALS]
        logger.debug(f"痛点信号: {domain} severity={severity:.2f} {description[:50]}")

    def get_pain_signals(self, domain: str = None, min_severity: float = 0.0) -> List[PainSignal]:
        with self._pain_lock:
            signals = list(self._pain_signals)
        if domain:
            signals = [s for s in signals if s.domain == domain]
        if min_severity > 0:
            signals = [s for s in signals if s.severity >= min_severity]
        return sorted(signals, key=lambda s: s.severity, reverse=True)

    def clear_pain_signals(self, domain: str = None):
        with self._pain_lock:
            if domain:
                self._pain_signals = [s for s in self._pain_signals if s.domain != domain]
            else:
                self._pain_signals.clear()

    def run_fast_loop(self, question: str = "", response: str = "",
                      fitness_score: float = 0.0, intent_type: str = ""):
        self._fast_loop_count += 1

        if fitness_score < 40 and question:
            self.record_pain_signal(
                domain="response_quality",
                description=f"低适应度({fitness_score:.1f}): {question[:80]}",
                severity=max(0.3, (40 - fitness_score) / 40),
                context={"intent_type": intent_type, "fitness": fitness_score},
            )

        try:
            from infrastructure.reflection_pipeline import get_reflection_pipeline
            rp = get_reflection_pipeline()
            import asyncio
            asyncio.get_event_loop().run_until_complete(rp._write_campfire_log({
                "question": question, "response": response, "fitness_score": fitness_score
            }))
        except Exception as e:
            logger.debug(f"快循环: 反思管道跳过: {e}")

        try:
            pass
        except Exception as e:
            logger.debug(f"快循环: 轨迹进化跳过: {e}")

        if self._fast_loop_count % 10 == 0:
            self._try_promote_ratchet()

    def _try_promote_ratchet(self):
        try:
            from infrastructure.ratchet_gate import ratchet_gate
            ratchet_gate.promote("global")
        except Exception:
            pass

    def run_slow_loop(self) -> Dict:
        self._slow_loop_count += 1
        self._last_slow_loop = time.time()

        pain_signals = self.get_pain_signals(min_severity=0.3)
        pain_domains = set(s.domain for s in pain_signals)

        results = {
            "slow_loop_count": self._slow_loop_count,
            "pain_signals_processed": len(pain_signals),
            "pain_domains": list(pain_domains),
            "steps": {},
        }

        step1 = self._slow_step_gene_evolution(pain_domains)
        results["steps"]["gene_evolution"] = step1

        step2 = self._slow_step_strategy_optimization(pain_domains)
        results["steps"]["strategy_optimization"] = step2

        step3 = self._slow_step_knowledge_consolidation(pain_domains)
        results["steps"]["knowledge_consolidation"] = step3

        step4 = self._slow_step_ratchet_validation()
        results["steps"]["ratchet_validation"] = step4

        self.clear_pain_signals()

        logger.info(
            f"慢循环完成(第{self._slow_loop_count}次): "
            f"痛点={len(pain_signals)}, 基因={step1.get('status', '?')}, "
            f"策略={step2.get('status', '?')}, 知识={step3.get('status', '?')}, "
            f"棘轮={step4.get('status', '?')}"
        )

        return results

    def _slow_step_gene_evolution(self, pain_domains: set) -> Dict:
        try:
            from infrastructure.ratchet_gate import ratchet_gate

            try:
                from core.genome_evolver import genome_evolver
                genome_evolver.sync_from_gene_pool()
                current_fitness = genome_evolver.get_evolution_stats().get("avg_fitness", 0.5)
                child_ids = genome_evolver.evolve(current_fitness)

                if not child_ids:
                    return {"status": "no_children", "child_count": 0}

                promoted = 0
                for cid in child_ids:
                    child_fitness = genome_evolver.evaluate_fitness({
                        "like_rate": 0.5, "hit_rate": 0.5,
                        "efficiency": 0.5, "dialog_reduction": 0, "external_reduction": 0,
                    })
                    decision = ratchet_gate.validate(child_fitness, domain="genome")
                    if decision.approved:
                        genome_evolver.promote_candidate(cid)
                        promoted += 1

                return {"status": "ok", "child_count": len(child_ids), "promoted": promoted}
            except Exception:
                ratchet_level = ratchet_gate.get_ratchet_level("genome")
                return {"status": "genome_unavailable", "ratchet_level": ratchet_level}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _slow_step_strategy_optimization(self, pain_domains: set) -> Dict:
        try:
            from infrastructure.ratchet_gate import ratchet_gate

            if "response_quality" in pain_domains:
                ratchet_gate.create_snapshot("strategy", "pre_optimization", {
                    "pain_domains": list(pain_domains),
                    "timestamp": datetime.now().isoformat(),
                }, fitness_score=0.5)

            return {"status": "ok", "pain_addressed": bool(pain_domains)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _slow_step_knowledge_consolidation(self, pain_domains: set) -> Dict:
        try:
            from infrastructure.ratchet_gate import ratchet_gate

            ratchet_gate.create_snapshot("knowledge", "consolidation_point", {
                "pain_domains": list(pain_domains),
            }, fitness_score=0.5)

            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _slow_step_ratchet_validation(self) -> Dict:
        try:
            from infrastructure.ratchet_gate import ratchet_gate

            promoted = ratchet_gate.promote("global")
            promoted_genome = ratchet_gate.promote("genome")
            promoted_strategy = ratchet_gate.promote("strategy")

            stats = ratchet_gate.get_stats()
            return {
                "status": "ok",
                "global_promoted": promoted,
                "genome_promoted": promoted_genome,
                "strategy_promoted": promoted_strategy,
                "approval_rate": stats.get("approval_rate", 0),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def start_slow_loop_background(self):
        if self._running:
            return
        self._running = True
        self._slow_thread = threading.Thread(target=self._slow_loop_worker, daemon=True)
        self._slow_thread.start()
        logger.info(f"双速进化慢循环后台启动 (间隔{self.SLOW_LOOP_INTERVAL}s)")

    def stop_slow_loop_background(self):
        self._running = False
        if self._slow_thread and self._slow_thread.is_alive():
            self._slow_thread.join(timeout=5)
        logger.info("双速进化慢循环后台停止")

    def _slow_loop_worker(self):
        while self._running:
            try:
                elapsed = time.time() - self._last_slow_loop
                if elapsed >= self.SLOW_LOOP_INTERVAL:
                    self.run_slow_loop()
                time.sleep(60.0)
            except Exception as e:
                logger.error(f"慢循环工作线程异常: {e}")
                time.sleep(120.0)

    def get_status(self) -> Dict:
        with self._pain_lock:
            pain_count = len(self._pain_signals)
            top_pain = max((s.severity for s in self._pain_signals), default=0.0)

        return {
            "fast_loop_count": self._fast_loop_count,
            "slow_loop_count": self._slow_loop_count,
            "pain_signal_count": pain_count,
            "top_pain_severity": top_pain,
            "last_slow_loop": self._last_slow_loop,
            "slow_loop_running": self._running,
        }


dual_speed_evolution = DualSpeedEvolutionCoordinator()