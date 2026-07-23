from abc import ABC, abstractmethod

class UIPort(ABC):
    @abstractmethod
    def start(self):
        """启动用户界面"""
        pass
    
    @abstractmethod
    def show_response(self, text: str):
        """显示响应给用户"""
        pass

    def is_available(self) -> bool:
        """UI是否可用（默认True，子类可覆盖）"""
        return True
