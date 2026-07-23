"""
统一路径接口 - 从oh-my-pi移植
一个read命令读取一切：本地文件、PDF、SQLite、GitHub、arXiv、网页等
"""
import asyncio
import aiohttp
from typing import Optional, Dict, Any
from pathlib import Path
from loguru import logger


class UnifiedReader:
    """
    统一读取接口
    read一个命令读一切
    """
    
    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def read(self, path: str, **kwargs) -> Dict[str, Any]:
        """
        统一读取接口
        
        Args:
            path: 路径（支持多种格式）
            
        Returns:
            {
                "type": "file/pdf/sqlite/github/arxiv/web",
                "content": "内容",
                "metadata": {...}
            }
        """
        # 判断路径类型
        if path.startswith("http://") or path.startswith("https://"):
            return await self._read_web(path)
        elif path.startswith("github:"):
            return await self._read_github(path[7:])
        elif path.startswith("arxiv:"):
            return await self._read_arxiv(path[6:])
        elif path.endswith(".pdf"):
            return await self._read_pdf(path)
        elif path.endswith(".sqlite") or path.endswith(".db"):
            return await self._read_sqlite(path, **kwargs)
        else:
            return await self._read_file(path)
    
    async def _read_file(self, path: str) -> Dict[str, Any]:
        """读取本地文件"""
        file_path = Path(path)
        
        if not file_path.exists():
            return {"type": "error", "content": "", "error": "文件不存在"}
        
        content = file_path.read_text(encoding='utf-8')
        
        return {
            "type": "file",
            "content": content,
            "metadata": {
                "path": str(file_path.absolute()),
                "size": file_path.stat().st_size,
                "lines": len(content.splitlines())
            }
        }
    
    async def _read_pdf(self, path: str) -> Dict[str, Any]:
        """读取PDF"""
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(path)
            pages = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                pages.append(text)
            
            doc.close()
            
            full_text = "\n".join(pages)
            
            return {
                "type": "pdf",
                "content": full_text,
                "metadata": {
                    "path": path,
                    "pages": len(pages),
                    "chars": len(full_text)
                }
            }
            
        except ImportError:
            return {
                "type": "error",
                "content": "",
                "error": "PyMuPDF未安装，请运行: pip install pymupdf"
            }
        except Exception as e:
            return {"type": "error", "content": "", "error": str(e)}
    
    async def _read_sqlite(
        self, 
        path: str, 
        query: str = None,
        table: str = None
    ) -> Dict[str, Any]:
        """读取SQLite数据库"""
        from core.ports.adapters import get_storage_port
        
        db_path = Path(path)
        if not db_path.exists():
            return {"type": "error", "content": "", "error": "数据库不存在"}
        
        db = get_storage_port(path)
        
        try:
            if query:
                rows = db.query(query)
                content = str(rows)
            elif table:
                if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table):
                    return {"type": "error", "content": f"无效表名: {table}"}
                rows = db.query(f"SELECT * FROM {table} LIMIT 100")
                content = str(rows)
            else:
                rows = db.query("SELECT name FROM sqlite_master WHERE type='table'")
                content = f"数据库表: {', '.join(t[0] for t in rows)}"
            
            return {
                "type": "sqlite",
                "content": content,
                "metadata": {
                    "path": path,
                    "size": db_path.stat().st_size
                }
            }
            
        finally:
            pass
    
    async def _read_web(self, url: str) -> Dict[str, Any]:
        """读取网页"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return {
                        "type": "error",
                        "content": "",
                        "error": f"HTTP {response.status}"
                    }
                
                content = await response.text()
                
                return {
                    "type": "web",
                    "content": content[:10000],  # 限制大小
                    "metadata": {
                        "url": url,
                        "status": response.status,
                        "size": len(content)
                    }
                }
                
        except Exception as e:
            return {"type": "error", "content": "", "error": str(e)}
    
    async def _read_github(self, repo_path: str) -> Dict[str, Any]:
        """
        读取GitHub仓库内容
        
        Args:
            repo_path: 格式为 "owner/repo/path/to/file"
        """
        parts = repo_path.split("/", 2)
        if len(parts) < 2:
            return {"type": "error", "content": "", "error": "格式: owner/repo 或 owner/repo/path"}
        
        owner, repo = parts[0], parts[1]
        file_path = parts[2] if len(parts) > 2 else ""
        
        # 构建API URL
        if file_path:
            url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
        else:
            url = f"https://api.github.com/repos/{owner}/{repo}"
        
        headers = {}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    return {
                        "type": "error",
                        "content": "",
                        "error": f"GitHub API {response.status}"
                    }
                
                data = await response.json()
                
                if isinstance(data, list):
                    # 目录列表
                    content = "\n".join([
                        f"{item['type']}: {item['name']}" 
                        for item in data
                    ])
                elif isinstance(data, dict) and 'content' in data:
                    # 文件内容（base64编码）
                    import base64
                    content = base64.b64decode(data['content']).decode('utf-8')
                else:
                    # 仓库信息
                    content = f"仓库: {data.get('full_name')}\n描述: {data.get('description')}"
                
                return {
                    "type": "github",
                    "content": content,
                    "metadata": {
                        "repo": f"{owner}/{repo}",
                        "path": file_path
                    }
                }
                
        except Exception as e:
            return {"type": "error", "content": "", "error": str(e)}
    
    async def _read_arxiv(self, paper_id: str) -> Dict[str, Any]:
        """
        读取arXiv论文
        
        Args:
            paper_id: 论文ID，如 "2301.12345"
        """
        # arXiv API
        url = f"http://export.arxiv.org/api/query?id_list={paper_id}"
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return {
                        "type": "error",
                        "content": "",
                        "error": f"arXiv API {response.status}"
                    }
                
                xml_content = await response.text()
                
                # 简单解析XML提取标题和摘要
                import re
                title_match = re.search(r'<title>(.*?)</title>', xml_content, re.DOTALL)
                summary_match = re.search(r'<summary>(.*?)</summary>', xml_content, re.DOTALL)
                
                title = title_match.group(1).strip() if title_match else "未知标题"
                summary = summary_match.group(1).strip() if summary_match else "无摘要"
                
                content = f"标题: {title}\n\n摘要: {summary}"
                
                return {
                    "type": "arxiv",
                    "content": content,
                    "metadata": {
                        "paper_id": paper_id,
                        "url": f"https://arxiv.org/abs/{paper_id}"
                    }
                }
                
        except Exception as e:
            return {"type": "error", "content": "", "error": str(e)}


async def demo_unified_reader():
    """演示统一读取接口"""
    
    print("\n=== 统一读取接口演示 ===\n")
    
    async with UnifiedReader() as reader:
        # 1. 读取本地文件
        print("1. 读取本地文件:")
        result = await reader.read("README.md")
        if result["type"] != "error":
            print(f"   类型: {result['type']}")
            print(f"   大小: {result['metadata']['size']} 字节")
            print(f"   行数: {result['metadata']['lines']}")
        else:
            print(f"   错误: {result.get('error')}")
        
        # 2. 读取arXiv论文
        print("\n2. 读取arXiv论文:")
        result = await reader.read("arxiv:2301.00001")
        if result["type"] != "error":
            print(f"   类型: {result['type']}")
            print(f"   内容预览: {result['content'][:200]}...")
        else:
            print(f"   错误: {result.get('error')}")
        
        # 3. 读取GitHub仓库
        print("\n3. 读取GitHub仓库:")
        result = await reader.read("github:can1357/oh-my-pi")
        if result["type"] != "error":
            print(f"   类型: {result['type']}")
            print(f"   内容: {result['content'][:200]}...")
        else:
            print(f"   错误: {result.get('error')}")


if __name__ == "__main__":
    asyncio.run(demo_unified_reader())