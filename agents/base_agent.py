from abc import ABC, abstractmethod
from typing import Any

class BaseAgent(ABC):
    """Abstract Base Class for all specialized agents."""
    
    name: str = "base_agent"
    role: str = "Base agent role"
    
    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Synchronously execute the agent."""
        pass
    
    async def arun(self, *args: Any, **kwargs: Any) -> Any:
        """Asynchronously execute the agent (defaults to sync run if not overridden)."""
        return self.run(*args, **kwargs)
