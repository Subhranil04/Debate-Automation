from typing import Dict
import uuid

try:
    # Older LangChain versions
    from langchain.memory import ConversationBufferWindowMemory  # type: ignore
except Exception:  # pragma: no cover
    # LangChain 1.x removed `langchain.memory`; keep a tiny compatible shim.
    from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

    class ConversationBufferWindowMemory:
        def __init__(self, memory_key: str = "history", k: int = 5, return_messages: bool = True):
            self.memory_key = memory_key
            self.k = k
            self.return_messages = return_messages
            self.buffer: list[BaseMessage] = []

        def load_memory_variables(self, inputs: Dict) -> Dict:
            window = self.buffer[-(self.k * 2) :] if self.k else self.buffer
            if self.return_messages:
                return {self.memory_key: window}
            return {self.memory_key: "\n".join(getattr(m, "content", "") for m in window)}

        def save_context(self, inputs: Dict, outputs: Dict) -> None:
            input_text = inputs.get("input") if isinstance(inputs, dict) else None
            if input_text is None and isinstance(inputs, dict) and inputs:
                input_text = next(iter(inputs.values()))

            output_text = outputs.get("output") if isinstance(outputs, dict) else None
            if output_text is None and isinstance(outputs, dict) and outputs:
                output_text = next(iter(outputs.values()))

            self.buffer.append(HumanMessage(content=str(input_text or "")))
            self.buffer.append(AIMessage(content=str(output_text or "")))


class MemoryManager:
    def __init__(self, k: int = 5):
        self.session_store: Dict[str, Dict] = {}
        self.k = k

    def create_session(self, topic: str) -> str:
        session_id = str(uuid.uuid4())
        memory = ConversationBufferWindowMemory(
            memory_key="history",
            k=self.k,
            return_messages=True
        )
        self.session_store[session_id] = {
            "topic": topic,
            "memory": memory
        }
        return session_id

    def get_memory(self, session_id: str):
        if session_id not in self.session_store:
            raise ValueError("Invalid session_id")
        return self.session_store[session_id]["memory"]

    def get_topic(self, session_id: str) -> str:
        if session_id not in self.session_store:
            raise ValueError("Invalid session_id")
        return self.session_store[session_id]["topic"]
    
    @staticmethod
    def print_current_memory(session_store: Dict[str, Dict], session_id: str):
        """Prints the current conversation memory for a given session."""
        if session_id == None or session_store == None :
            print("No session_id or No session_store given")
            return ;
        
        if session_id not in session_store:
            raise ValueError("Invalid session_id")
        
        memory = session_store[session_id]["memory"]
        history = memory.buffer
        
        if not history:
            print("No conversation history yet.")
            return
            
        print(f"Conversation history for session {session_id}:")
        for message in history:
            role = getattr(message, "type", "unknown")
            content = getattr(message, "content", "")
            print(f"[{role}] {content}")