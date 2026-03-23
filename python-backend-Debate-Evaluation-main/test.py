# from services.prompt import get_evaluation_prompt
# from langchain_core.output_parsers import PydanticOutputParser
# from models.pydantic_models import EvaluationResponse


# parser = PydanticOutputParser(pydantic_object=EvaluationResponse)

# prompt = get_evaluation_prompt()

# ip = {
#     "topic": "Climate change is a global crisis",
#     "statement": "Climate change is caused by only human activity",
#     "user_id": 1,
#     "history": [],
#     "format_instructions": parser.get_format_instructions()
# }

# prompt_value = prompt.invoke(ip)
# print("Prompt messages:")
# print()
# print(prompt_value)
# print("")
# print("_____________________________________")
# print("")
# for msg in prompt_value.messages:
#     print(f"- {msg.__class__.__name__}: {msg.content}")


# test memory manager :

from services.memory import MemoryManager  
from langchain.schema import HumanMessage, AIMessage



def process_debate_turns(session_memory, debate_turns: list[tuple[str, str]]):
    """Process each debate turn, store it in memory, and simulate evaluation."""
    for speaker, statement in debate_turns:
        full_statement = f"[{speaker}] {statement}"
        session_memory.chat_memory.add_user_message(full_statement)




memory_manager = MemoryManager(k=3)  

session_id = memory_manager.create_session(topic="Artificial Intelligence Discussion")
print(f"session_id: {session_id}")

# Get the memory object
session = memory_manager.session_store[session_id]
memory = session["memory"]


debate_turns = [
        ("A", "AI has created more jobs than it has destroyed."),
        ("B", "But many low-skill jobs have been automated away, leaving people unemployed."),
        ("A", "New industries powered by AI have absorbed a lot of workers."),
        ("B", "However, not everyone can transition to tech-related jobs easily."),
]

process_debate_turns(memory, debate_turns)

memory_manager.print_current_memory(session_id)




