"""
检查前端HTML文件中的资源引用
"""
import os
import re

print("=" * 70)
print("前端资源引用检查")
print("=" * 70)
print()

html_files = []
for root, dirs, files in os.walk('frontend'):
    for f in files:
        if f.endswith('.html'):
            html_files.append(os.path.join(root, f))

issues = []

for html_file in html_files:
    print(f"检查: {html_file}")
    
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找CSS引用
    css_refs = re.findall(r'href="([^"]+\.css)"', content)
    for css in css_refs:
        # 检查路径是否正确
        if css.startswith('/frontend/'):
            actual_path = css[1:]  # 去掉开头的/
        else:
            actual_path = os.path.join(os.path.dirname(html_file), css)
        
        if not os.path.exists(actual_path):
            issues.append(f"{html_file}: CSS不存在 - {css}")
            print(f"  ✗ CSS: {css} (不存在)")
        else:
            print(f"  ✓ CSS: {css}")
    
    # 查找JS引用
    js_refs = re.findall(r'src="([^"]+\.js[^"]*)"', content)
    for js in js_refs:
        # 去掉版本参数
        js_path = js.split('?')[0]
        
        if js_path.startswith('/frontend/'):
            actual_path = js_path[1:]
        else:
            actual_path = os.path.join(os.path.dirname(html_file), js_path)
        
        if not os.path.exists(actual_path):
            issues.append(f"{html_file}: JS不存在 - {js}")
            print(f"  ✗ JS: {js} (不存在)")
        else:
            print(f"  ✓ JS: {js}")
    
    print()

print("=" * 70)
if issues:
    print(f"发现 {len(issues)} 个问题:")
    for issue in issues:
        print(f"  ✗ {issue}")
else:
    print("✅ 所有资源引用正常")
print("=" * 70)