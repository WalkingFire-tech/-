"""
Hashline编辑器 - 从oh-my-pi移植
基于内容哈希定位代码行，避免"改错行"问题
"""
import hashlib
from typing import List, Tuple, Optional
from pathlib import Path
from loguru import logger


class HashlineEditor:
    """
    Hashline编辑器
    通过内容哈希而非行号定位代码
    """
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.content = None
        self.lines = []
        self.hash_map = {}
    
    def load(self) -> bool:
        """加载文件"""
        if not self.file_path.exists():
            logger.error(f"文件不存在: {self.file_path}")
            return False
        
        self.content = self.file_path.read_text(encoding='utf-8')
        self.lines = self.content.splitlines(keepends=True)
        
        # 构建哈希映射
        self.hash_map = {}
        for i, line in enumerate(self.lines):
            line_hash = self._hash_line(line)
            self.hash_map[line_hash] = i
        
        logger.info(f"加载文件: {self.file_path} ({len(self.lines)} 行)")
        return True
    
    @staticmethod
    def _hash_line(line: str) -> str:
        """计算行的哈希值"""
        # 移除行尾空白，保留内容语义
        normalized = line.rstrip()
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()[:12]
    
    def find_line(self, content_hash: str) -> Optional[int]:
        """根据哈希查找行号"""
        return self.hash_map.get(content_hash)
    
    def edit(
        self, 
        content_hash: str, 
        new_content: str,
        verify: bool = True
    ) -> Tuple[bool, str]:
        """
        编辑指定行
        
        Args:
            content_hash: 内容哈希
            new_content: 新内容
            verify: 是否验证哈希匹配
            
        Returns:
            (成功与否, 消息)
        """
        line_num = self.find_line(content_hash)
        
        if line_num is None:
            msg = f"哈希 {content_hash} 未找到对应行"
            logger.error(msg)
            return False, msg
        
        old_line = self.lines[line_num]
        
        if verify:
            # 验证哈希是否仍然匹配（防止文件已修改）
            current_hash = self._hash_line(old_line)
            if current_hash != content_hash:
                msg = f"文件已修改，哈希不匹配（期望 {content_hash}，实际 {current_hash}）"
                logger.error(msg)
                return False, msg
        
        # 执行编辑
        if not new_content.endswith('\n'):
            new_content += '\n'
        
        self.lines[line_num] = new_content
        
        logger.info(f"编辑行 {line_num + 1}: {old_line.strip()} → {new_content.strip()}")
        return True, f"成功编辑第 {line_num + 1} 行"
    
    def insert_after(
        self, 
        content_hash: str, 
        new_content: str
    ) -> Tuple[bool, str]:
        """在指定行后插入"""
        line_num = self.find_line(content_hash)
        
        if line_num is None:
            return False, f"哈希 {content_hash} 未找到"
        
        if not new_content.endswith('\n'):
            new_content += '\n'
        
        self.lines.insert(line_num + 1, new_content)
        logger.info(f"在第 {line_num + 1} 行后插入: {new_content.strip()}")
        return True, f"成功在第 {line_num + 1} 行后插入"
    
    def delete(self, content_hash: str) -> Tuple[bool, str]:
        """删除指定行"""
        line_num = self.find_line(content_hash)
        
        if line_num is None:
            return False, f"哈希 {content_hash} 未找到"
        
        deleted = self.lines.pop(line_num)
        logger.info(f"删除第 {line_num + 1} 行: {deleted.strip()}")
        return True, f"成功删除第 {line_num + 1} 行"
    
    def save(self, backup: bool = True) -> bool:
        """保存文件"""
        if backup:
            # 创建备份
            backup_path = self.file_path.with_suffix(self.file_path.suffix + '.bak')
            backup_path.write_text(self.content, encoding='utf-8')
            logger.info(f"创建备份: {backup_path}")
        
        # 写入新内容
        new_content = ''.join(self.lines)
        self.file_path.write_text(new_content, encoding='utf-8')
        
        logger.info(f"保存文件: {self.file_path}")
        return True
    
    def get_context(self, content_hash: str, context_lines: int = 3) -> List[str]:
        """获取上下文"""
        line_num = self.find_line(content_hash)
        
        if line_num is None:
            return []
        
        start = max(0, line_num - context_lines)
        end = min(len(self.lines), line_num + context_lines + 1)
        
        context = []
        for i in range(start, end):
            prefix = ">>> " if i == line_num else "    "
            context.append(f"{prefix}{i + 1}: {self.lines[i].rstrip()}")
        
        return context


def demo_hashline_edit():
    """演示Hashline编辑"""
    from tempfile import TemporaryDirectory
    
    with TemporaryDirectory() as tmpdir:
        # 创建测试文件
        test_file = Path(tmpdir) / "test.py"
        test_file.write_text("""def hello():
    print("Hello, World!")
    return True

def goodbye():
    print("Goodbye!")
    return False
""", encoding='utf-8')
        
        print("\n=== Hashline编辑演示 ===\n")
        
        # 创建编辑器
        editor = HashlineEditor(str(test_file))
        editor.load()
        
        # 查找要编辑的行
        target_line = '    print("Hello, World!")\n'
        target_hash = HashlineEditor._hash_line(target_line)
        
        print(f"目标行哈希: {target_hash}")
        print(f"上下文:")
        for line in editor.get_context(target_hash):
            print(f"  {line}")
        
        # 执行编辑
        success, msg = editor.edit(
            target_hash,
            '    print("Hello, Alliance-Pioneer!")'
        )
        print(f"\n编辑结果: {msg}")
        
        # 保存
        editor.save(backup=True)
        
        # 查看结果
        print(f"\n编辑后内容:")
        print(test_file.read_text(encoding='utf-8'))


if __name__ == "__main__":
    demo_hashline_edit()