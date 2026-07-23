"""
Storage 端口 — 数据库持久化的抽象接口

任何数据库实现必须遵循此接口。
当前实现: infrastructure.database_manager.DatabaseManager

设计原则：
- 覆盖最常用的5个方法（query, query_one, execute, get, transaction）
- 同步接口（DatabaseManager本身是同步的，async由适配器处理）
- is_available()检查数据库连接是否可用
"""
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple


class StoragePort(ABC):
    """数据库存储端口"""

    @abstractmethod
    def query(self, sql: str, params: tuple = None) -> List[Tuple]:
        """执行查询，返回行列表"""
        ...

    @abstractmethod
    def query_one(self, sql: str, params: tuple = None) -> Optional[Tuple]:
        """执行查询，返回单行"""
        ...

    @abstractmethod
    def execute(self, sql: str, params: tuple = None, commit: bool = False) -> Any:
        """执行写操作"""
        ...

    @abstractmethod
    def get(self, db_path: str, **kwargs) -> "StoragePort":
        """获取指定路径的数据库连接（工厂方法）"""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """数据库是否可用"""
        ...

    def executescript(self, sql_script: str) -> None:
        """执行多条SQL语句（默认实现：逐条执行）"""
        for stmt in sql_script.split(";"):
            stmt = stmt.strip()
            if stmt:
                self.execute(stmt)