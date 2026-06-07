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
