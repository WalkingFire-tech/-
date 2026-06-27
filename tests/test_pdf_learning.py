"""
端到端测试 - PDF学习功能
"""
import requests
import time
import os
from pathlib import Path

API_BASE = "http://localhost:8000"

def test_pdf_learning():
    """测试PDF学习功能"""
    print("\n" + "="*60)
    print("端到端测试 - PDF学习功能")
    print("="*60)
    
    # 1. 创建测试PDF
    print("\n1. 创建测试PDF文件...")
    try:
        import fitz  # PyMuPDF
        
        # 创建一个简单的PDF
        doc = fitz.open()
        
        # 添加10页内容
        for i in range(10):
            page = doc.new_page()
            text = f"""
第 {i+1} 页 - 电子设计基础知识

这是测试PDF文件的第{i+1}页。

主要内容：
1. 电路设计基础
2. 模拟电路分析
3. 数字电路设计
4. PCB布局原则
5. 电磁兼容设计

示例代码：
def calculate_voltage(current, resistance):
    return current * resistance

def calculate_power(voltage, current):
    return voltage * current

关键公式：
- 欧姆定律：V = I × R
- 功率公式：P = V × I
- 基尔霍夫定律：ΣI = 0, ΣV = 0

注意事项：
- 注意电源去耦
- 注意信号完整性
- 注意热设计
"""
            page.insert_text((50, 50), text, fontsize=12)
        
        # 保存PDF
        test_pdf = Path("test_electronics.pdf")
        doc.save(str(test_pdf))
        doc.close()
        
        print(f"   ✓ 测试PDF已创建: {test_pdf} ({test_pdf.stat().st_size} 字节)")
        
    except Exception as e:
        print(f"   ✗ 创建PDF失败: {e}")
        return False
    
    # 2. 测试文件学习API
    print("\n2. 测试文件学习API...")
    try:
        response = requests.post(
            f"{API_BASE}/api/files/learn",
            json={"files": [str(test_pdf.absolute())]},
            timeout=60
        )
        
        print(f"   状态码: {response.status_code}")
        data = response.json()
        
        if data.get("success"):
            print(f"   ✓ 学习成功")
            print(f"   总知识点: {data.get('total_knowledge', 0)}条")
            print(f"\n   摘要:")
            print(data.get("summary", ""))
        else:
            print(f"   ✗ 学习失败: {data.get('error')}")
            return False
            
    except Exception as e:
        print(f"   ✗ API调用失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 3. 验证知识库
    print("\n3. 验证知识库...")
    try:
        import sqlite3
        
        with sqlite3.connect("data/knowledge_store.db") as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM knowledge 
                WHERE source LIKE 'pdf:test_electronics%'
            """)
            count = cursor.fetchone()[0]
            
            print(f"   ✓ 知识库中有 {count} 条来自该PDF的知识点")
            
            # 查看内容示例
            cursor = conn.execute("""
                SELECT content, source FROM knowledge 
                WHERE source LIKE 'pdf:test_electronics%'
                LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                print(f"   内容示例: {row[0][:100]}...")
                print(f"   来源: {row[1]}")
            
    except Exception as e:
        print(f"   ✗ 知识库验证失败: {e}")
        return False
    
    # 4. 清理测试文件
    print("\n4. 清理测试文件...")
    try:
        os.remove("test_electronics.pdf")
        print("   ✓ 测试文件已删除")
    except:
        pass
    
    print("\n" + "="*60)
    print("✓ 端到端测试完成")
    print("="*60)
    return True


def test_large_pdf():
    """测试大PDF文件"""
    print("\n" + "="*60)
    print("测试大PDF文件")
    print("="*60)
    
    # 查找桌面上的PDF
    desktop_pdfs = list(Path("C:/Users/Administrator/Desktop").glob("*.pdf"))
    
    if not desktop_pdfs:
        print("   未找到测试PDF")
        return False
    
    # 选择一个较大的PDF
    test_pdf = max(desktop_pdfs, key=lambda p: p.stat().st_size)
    file_size = test_pdf.stat().st_size / 1024 / 1024
    
    print(f"\n测试文件: {test_pdf.name}")
    print(f"文件大小: {file_size:.2f} MB")
    
    if file_size < 1:
        print("   文件太小，跳过测试")
        return True
    
    # 测试学习
    print("\n开始学习...")
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{API_BASE}/api/files/learn",
            json={"files": [str(test_pdf)]},
            timeout=120
        )
        
        elapsed = time.time() - start_time
        
        print(f"   处理时间: {elapsed:.2f} 秒")
        print(f"   状态码: {response.status_code}")
        
        data = response.json()
        
        if data.get("success"):
            print(f"   ✓ 学习成功")
            print(f"   总知识点: {data.get('total_knowledge', 0)}条")
            
            # 验证处理时间合理
            if elapsed < 1:
                print(f"   ⚠️ 警告: {file_size:.2f}MB的PDF在{elapsed:.2f}秒内处理完成，可能没有真正解析")
                return False
            else:
                print(f"   ✓ 处理时间合理")
                return True
        else:
            print(f"   ✗ 学习失败: {data.get('error')}")
            return False
            
    except Exception as e:
        print(f"   ✗ 测试失败: {e}")
        return False


if __name__ == "__main__":
    # 测试1：基础PDF学习
    result1 = test_pdf_learning()
    
    # 测试2：大PDF文件
    result2 = test_large_pdf()
    
    if result1 and result2:
        print("\n✅ 所有测试通过！")
    else:
        print("\n❌ 部分测试失败")