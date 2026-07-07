import json, urllib.request, urllib.error, sys, time

GET_ENDPOINTS = [
    '/api/health',
    '/api/resource-status',
    '/api/background-tasks',
    '/api/stats',
    '/api/genes',
    '/api/skills',
    '/api/truths',
    '/api/truths/entropy',
    '/api/models',
    '/api/knowledge/health',
    '/api/reflection/stats',
    '/api/module/health',
    '/api/trajectory/stats',
    '/api/tools',
    '/api/tools/stats',
    '/api/events/stats',
    '/api/scheduled-tasks/status',
    '/api/system/audit',
    '/api/defense/status',
    '/api/defense/anomalies',
    '/api/defense/health/metrics',
    '/api/self-assessment',
    '/api/self-assessment/history',
    '/api/forgetting/evaluate',
    '/api/facts/search',
    '/api/facts/stats',
    '/api/memory/search',
    '/api/memory/stats',
    '/api/relationship/summary',
    '/api/relationship/metrics',
    '/api/presence/status',
    '/api/proactivity/evaluate',
    '/api/agent/status',
    '/api/weights',
    '/api/attributions',
    '/api/probability-field',
    '/api/delta-stats',
    '/api/config/external',
    '/api/recent_learning',
]

BASE = 'http://localhost:8000'

results = []
for ep in GET_ENDPOINTS:
    url = f'{BASE}{ep}'
    try:
        start = time.time()
        r = urllib.request.urlopen(url, timeout=15)
        elapsed = time.time() - start
        data = json.loads(r.read())
        
        # Analyze data quality
        has_error = isinstance(data, dict) and 'error' in data
        is_empty = False
        data_richness = 0
        
        if isinstance(data, dict):
            keys = list(data.keys())
            data_richness = len(keys)
            # Check for empty/fallback indicators
            empty_indicators = ['unknown', 'N/A', 'none', 'null', '[]', '{}']
            values_str = json.dumps(data, ensure_ascii=False)
            null_count = values_str.count(': null') + values_str.count(':null')
            zero_count = values_str.count(': 0') + values_str.count(':0')
            total_values = len(keys)
            
            # Determine if data is "real" vs "empty shell"
            if total_values > 0 and null_count / max(total_values, 1) > 0.7:
                is_empty = True
            if data_richness <= 1 and not has_error:
                is_empty = True
                
        status = 'ERROR' if has_error else ('EMPTY' if is_empty else 'OK')
        richness = data_richness
        
        result = {
            'endpoint': ep,
            'status': status,
            'richness': richness,
            'latency_ms': int(elapsed * 1000),
            'error': data.get('error', '') if has_error else '',
            'sample_keys': list(data.keys())[:8] if isinstance(data, dict) else str(data)[:50]
        }
    except urllib.error.HTTPError as e:
        result = {
            'endpoint': ep,
            'status': f'HTTP_{e.code}',
            'richness': 0,
            'latency_ms': 0,
            'error': str(e),
            'sample_keys': []
        }
    except Exception as e:
        result = {
            'endpoint': ep,
            'status': 'FAIL',
            'richness': 0,
            'latency_ms': 0,
            'error': str(e)[:80],
            'sample_keys': []
        }
    
    results.append(result)
    status_icon = {'OK': '✓', 'ERROR': '✗', 'EMPTY': '○'}.get(result['status'], '?')
    print(f"  {status_icon} {result['status']:8s} {result['latency_ms']:5d}ms  r={result['richness']:2d}  {ep}")
    if result['error']:
        print(f"         ERROR: {result['error'][:60]}")

# Summary
ok_count = sum(1 for r in results if r['status'] == 'OK')
err_count = sum(1 for r in results if r['status'] in ('ERROR', 'EMPTY'))
fail_count = sum(1 for r in results if r['status'] not in ('OK', 'ERROR', 'EMPTY'))
total = len(results)

print(f"\n{'='*60}")
print(f"GET ENDPOINTS SUMMARY: {total} tested")
print(f"  OK:    {ok_count} ({ok_count/total*100:.0f}%)")
print(f"  ERROR: {err_count} ({err_count/total*100:.0f}%)")
print(f"  FAIL:  {fail_count} ({fail_count/total*100:.0f}%)")

# Save detailed results
with open(r'C:\Users\Administrator\alliance_pioneer\_audit_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\nDetailed results saved to _audit_results.json")