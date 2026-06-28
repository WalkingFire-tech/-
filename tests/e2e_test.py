"""
端到端测试脚本 - 联盟拓荒者系统
"""
import requests
import json
import time
import sys

API_BASE = "http://localhost:8000"

def test_stream_chat(message, history=None, label="测试"):
    """测试流式聊天接口"""
    print(f"\n{'='*60}")
    print(f"🧪 {label}: {message}")
    print(f"{'='*60}")
    
    body = {"message": message}
    if history:
        body["history"] = history
    
    start = time.time()
    try:
        response = requests.post(
            f"{API_BASE}/api/chat/stream",
            json=body,
            stream=True,
            timeout=120
        )
        
        steps = []
        final_result = None
        
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            json_str = line[6:].strip()
            if not json_str:
                continue
            try:
                event = json.loads(json_str)
                if event.get("type") == "step":
                    phase = event.get("phase", "")
                    status = event.get("status", "")
                    detail = event.get("detail", "")
                    icon = "✅" if status == "done" else "⏳"
                    steps.append(f"  {icon} {phase}: {detail}")
                    print(f"  {icon} {phase}: {detail}")
                elif event.get("type") == "result":
                    final_result = event
            except:
                pass
        
        elapsed = time.time() - start
        
        if final_result:
            resp = final_result.get("response", "")
            intent = final_result.get("intent", "")
            attempts = final_result.get("attempts", [])
            
            print(f"\n📊 结果统计:")
            print(f"  耗时: {elapsed:.1f}秒")
            print(f"  意图: {intent}")
            print(f"  尝试步骤: {len(attempts)}")
            for a in attempts:
                status_icon = "✅" if a[1] else "❌"
                print(f"    {status_icon} {a[0]}: {a[2] if len(a) > 2 else ''}")
            
            print(f"\n💬 回复内容 ({len(resp)}字):")
            if len(resp) > 500:
                print(f"  {resp[:500]}...")
            else:
                print(f"  {resp}")
            
            # 检查关键特性
            checks = []
            if "建议参考" in resp and "NASA" in resp:
                checks.append("⚠️ 免责声明包含NASA（应领域感知）")
            if "建议参考" in resp and "学术期刊" in resp:
                checks.append("✅ 免责声明领域感知正确")
            if "建议参考" not in resp and any(kw in message for kw in ["代码", "编程", "STM32"]):
                checks.append("✅ 代码问题未触发科学免责")
            if "罗列" in resp or "观点" in resp:
                checks.append("✅ 诚实罗列分歧模式")
            if "⚠️" in resp:
                checks.append("⚠️ 包含不确定性声明")
            
            if checks:
                print(f"\n🔍 特性检查:")
                for c in checks:
                    print(f"  {c}")
            
            return {
                "success": True,
                "elapsed": elapsed,
                "intent": intent,
                "response": resp,
                "steps": len(attempts)
            }
        else:
            print(f"❌ 无最终结果 (耗时{elapsed:.1f}秒)")
            return {"success": False, "elapsed": elapsed}
            
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时")
        return {"success": False, "elapsed": 120}
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return {"success": False, "elapsed": 0}


def test_api(endpoint, label="API测试"):
    """测试普通API"""
    print(f"\n📡 {label}: {endpoint}")
    try:
        resp = requests.get(f"{API_BASE}{endpoint}", timeout=5)
        data = resp.json()
        print(f"  ✅ {json.dumps(data, ensure_ascii=False, indent=2)[:300]}")
        return data
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return None


if __name__ == "__main__":
    test_num = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    
    results = []
    
    # 先检查系统状态
    print("🔍 系统状态检查...")
    test_api("/api/health", "健康检查")
    test_api("/api/genes", "基因池")
    test_api("/api/skills", "技能库")
    test_api("/api/truths", "真谛库")
    test_api("/api/truths/entropy", "认知熵值")
    
    if test_num == 0 or test_num == 1:
        # 测试1：简单问候
        r = test_stream_chat("你好", label="测试1: 简单问候")
        results.append(("问候", r))
    
    if test_num == 0 or test_num == 2:
        # 测试2：科学事实问题 — 应触发本质推理+科学免责(领域感知)
        r = test_stream_chat("为什么天空是蓝色的", label="测试2: 科学事实(物理)")
        results.append(("科学事实", r))
    
    if test_num == 0 or test_num == 3:
        # 测试3：代码问题 — 应触发代码验证，不触发科学免责
        r = test_stream_chat("给我写一段二分查找的代码，我要在STM32单片机上运行", label="测试3: 代码/工程")
        results.append(("代码工程", r))
    
    if test_num == 0 or test_num == 4:
        # 测试4：悖论问题 — 应触发本质闸门悖论识别
        r = test_stream_chat("遇到鸡和蛋的问题我该如何处理", label="测试4: 悖论问题")
        results.append(("悖论", r))
    
    if test_num == 0 or test_num == 5:
        # 测试5：质疑检测
        r = test_stream_chat("你确定吗", label="测试5: 质疑检测")
        results.append(("质疑", r))
    
    if test_num == 0 or test_num == 6:
        # 测试6：上下文连续性
        r1 = test_stream_chat("火星的大气成分是什么", label="测试6a: 上下文-第一轮")
        r2 = test_stream_chat("那火星的天空是什么颜色", label="测试6b: 上下文-第二轮(应联系前文)")
        results.append(("上下文", r2))
    
    # 汇总
    print(f"\n\n{'='*60}")
    print(f"📊 端到端测试汇总")
    print(f"{'='*60}")
    for name, r in results:
        if r.get("success"):
            print(f"  ✅ {name}: {r['elapsed']:.1f}秒, 意图={r.get('intent','?')}, 步骤={r.get('steps',0)}")
        else:
            print(f"  ❌ {name}: 失败 ({r.get('elapsed',0):.1f}秒)")