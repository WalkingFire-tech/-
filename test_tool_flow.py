import asyncio
import sys
import re

sys.path.insert(0, '.')

async def test():
    from core.tool_registry import tool_executor, tool_registry
    
    from core.tools.file_reader_tool import FileReaderTool
    from core.tools.project_scanner_tool import ProjectScannerTool
    from core.tools.code_indexer_tool import CodeIndexerTool
    from core.tools.dependency_analyzer_tool import DependencyAnalyzerTool
    from core.tools.web_search_tool import WebSearchTool
    from core.tools.calculator_tool import CalculatorTool
    from core.tools.code_executor_tool import CodeExecutorTool
    from core.tools.knowledge_lookup_tool import KnowledgeLookupTool
    from core.tools.fact_check_tool import FactCheckTool
    for cls in [WebSearchTool, CalculatorTool, CodeExecutorTool, KnowledgeLookupTool, FactCheckTool,
                FileReaderTool, ProjectScannerTool, CodeIndexerTool, DependencyAnalyzerTool]:
        tool_registry.register(cls())
    
    query = '读取README.md'
    intent_type = 'complex_query'
    
    tool_names = tool_registry.plan_tools(query, intent_type)
    print(f'Planned tools: {tool_names}')
    
    if not tool_names:
        print('No tools matched!')
        return
    
    tool_names = tool_names[:5]
    
    params = {'query': query}
    path_pattern = r'(?:读取|打开|查看|看看|读一下|read|open|show|cat)\s*[`"\']?([\w/\\.-]+\.\w{1,6})[`"\']?'
    path_match = re.search(path_pattern, query, re.IGNORECASE)
    if path_match:
        params['query'] = path_match.group(1).strip()
    print(f'Params: {params}')
    
    results = await tool_executor.execute_parallel(tool_names, params, total_timeout=20.0)
    candidates = []
    for r in results:
        err_str = r.error[:100] if r.error else ""
        data_len = len(r.data) if r.data else 0
        print(f'Result: success={r.success} source={r.source} error={err_str} data_len={data_len}')
        c = r.to_candidate()
        if c:
            candidates.append(c)
            resp_len = len(c["response"])
            print(f'  Candidate: source={c["source"]} quality={c["quality"]} resp_len={resp_len}')
        else:
            print('  to_candidate returned None!')
    
    print(f'Total candidates: {len(candidates)}')
    return candidates

result = asyncio.run(test())
print(f'Final result count: {len(result) if result else 0}')