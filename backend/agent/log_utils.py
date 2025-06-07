from typing import List, Dict, Optional

class AgentLog:
    def __init__(self, agent_name: str, thought: str, conclusion: str, chunk: Optional[int] = None, prompt: Optional[str] = None, response: Optional[str] = None, status: Optional[str] = None, extra: Optional[dict] = None):
        self.agent_name = agent_name
        self.thought = thought
        self.conclusion = conclusion
        self.chunk = chunk
        self.prompt = prompt
        self.response = response
        self.status = status
        self.extra = extra or {}

    def to_dict(self) -> Dict:
        return {
            "agent": self.agent_name,
            "thought": self.thought,
            "conclusion": self.conclusion,
            "chunk": self.chunk,
            "prompt": self.prompt,
            "response": self.response,
            "status": self.status,
            "extra": self.extra
        }

def collect_logs(logs: List[AgentLog]) -> List[Dict]:
    return [log.to_dict() for log in logs]
