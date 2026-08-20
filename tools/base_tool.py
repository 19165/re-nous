from abc import ABC, abstractmethod
from typing import Any

class BaseTool(ABC):
    """Abstract Base Class for all external tool adapters."""
    
    name: str = "base_tool"
    description: str = "Base tool description"
    
    @abstractmethod
    def invoke(self, query: str, **kwargs: Any) -> Any:
        """Synchronously execute the tool."""
        pass
    
    @abstractmethod
    async def ainvoke(self, query: str, **kwargs: Any) -> Any:
        """Asynchronously execute the tool."""
        pass
