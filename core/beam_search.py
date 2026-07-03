"""
多路径树搜索 (Beam Search) - P2-3

当阶段3的9路径并行结果不够好时，用beam search进行第二轮扩展。
深度=2, 宽度=2（可配置）

工作流程：
1. 从阶段3的候选结果中选取top-2（beam width）
2. 对每个候选结果，生成2个扩展查询（refinement/sub-question）
3. 并行执行扩展查询
4. 合并所有结果，重新排序

设计原则：
- 轻量级：只在适应度<60时触发
- 不重复：扩展查询必须与原始查询不同
- 超时安全：总时间不超过20秒
"""

import asyncio
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class BeamNode:
    query: str
    response: str
    source: str
    quality: float
    depth: int = 0
    parent_id: Optional[int] = None
    children: List[int] = field(default_factory=list)
    node_id: int = 0


class BeamSearchEngine:
    def __init__(self, max_depth: int = 2, beam_width: int = 2,
                 min_quality_to_skip: float = 60.0, max_total_seconds: float = 20.0):
        self.max_depth = max_depth
        self.beam_width = beam_width
        self.min_quality_to_skip = min_quality_to_skip
        self.max_total_seconds = max_total_seconds
        self._node_counter = 0

    def should_trigger(self, candidates: List[Dict]) -> bool:
        if not candidates:
            return True
        best_quality = max(c.get("quality", 0) for c in candidates)
        return best_quality < self.min_quality_to_skip

    def select_beam(self, candidates: List[Dict]) -> List[Dict]:
        sorted_cands = sorted(candidates, key=lambda c: c.get("quality", 0), reverse=True)
        return sorted_cands[:self.beam_width]

    def generate_expansion_queries(self, original_query: str, candidate: Dict) -> List[str]:
        source = candidate.get("source", "")
        response = candidate.get("response", "")
        quality = candidate.get("quality", 0)
        expansions = []

        if quality < 30:
            expansions.append(f"请更详细地解释：{original_query}")
            expansions.append(f"从另一个角度分析：{original_query}")
        elif quality < 50:
            expansions.append(f"补充细节：{original_query}")
            if len(response) < 100:
                expansions.append(f"深入展开：{original_query}")
            else:
                expansions.append(f"验证以下观点是否正确：{response[:200]}")
        else:
            expansions.append(f"进一步验证：{original_query}")
            expansions.append(f"有什么反例或例外情况：{original_query}")

        return expansions[:self.beam_width]

    async def search(self, original_query: str, candidates: List[Dict],
                     fetch_func=None, conversation_context: str = "") -> List[Dict]:
        if not self.should_trigger(candidates):
            logger.debug(f"Beam search跳过: 最佳质量>{self.min_quality_to_skip}")
            return candidates

        start = time.time()
        logger.info(f"Beam search启动: depth={self.max_depth}, width={self.beam_width}, "
                     f"candidates={len(candidates)}, best_quality={max((c.get('quality', 0) for c in candidates), default=0):.1f}")

        all_results = list(candidates)
        current_beam = self.select_beam(candidates)

        for depth in range(1, self.max_depth + 1):
            elapsed = time.time() - start
            if elapsed > self.max_total_seconds * 0.8:
                logger.info(f"Beam search深度{depth}跳过: 已用{elapsed:.1f}s")
                break

            expansion_tasks = []
            for cand in current_beam:
                queries = self.generate_expansion_queries(original_query, cand)
                for q in queries:
                    if fetch_func:
                        expansion_tasks.append(fetch_func(q, conversation_context))

            if not expansion_tasks:
                break

            try:
                expansion_results = await asyncio.wait_for(
                    asyncio.gather(*expansion_tasks, return_exceptions=True),
                    timeout=max(1.0, self.max_total_seconds - elapsed)
                )
            except asyncio.TimeoutError:
                logger.warning(f"Beam search深度{depth}超时")
                break

            new_candidates = []
            for r in expansion_results:
                if isinstance(r, dict) and r.get("response"):
                    new_candidates.append(r)
                elif isinstance(r, list):
                    for item in r:
                        if isinstance(item, dict) and item.get("response"):
                            new_candidates.append(item)

            all_results.extend(new_candidates)

            if new_candidates:
                current_beam = self.select_beam(new_candidates)
            else:
                break

            logger.info(f"Beam search深度{depth}: 新增{len(new_candidates)}个候选, "
                         f"总{len(all_results)}个, 耗时{time.time()-start:.1f}s")

        best_quality = max((c.get("quality", 0) for c in all_results), default=0)
        logger.info(f"Beam search完成: 总{len(all_results)}个候选, "
                     f"最佳质量{best_quality:.1f}, 耗时{time.time()-start:.1f}s")

        return all_results


beam_search_engine = BeamSearchEngine()