from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import PydanticOutputParser
from services.prompt import get_evaluation_prompt, get_exchange_scoring_prompt
from config import Config
from models.pydantic_models import EvaluationResponse, ExchangeScoreResponse
from services.memory import MemoryManager
import logging


# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class DebateEvaluator:
    def __init__(self):
        self.model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=Config.GEMINI_API_KEY,
            temperature=0.3
        )
        self.prompt = get_evaluation_prompt()
        self.parser = PydanticOutputParser(pydantic_object=EvaluationResponse)
        self.chain = self.prompt | self.model | self.parser

        # Exchange scoring chain
        self.exchange_prompt = get_exchange_scoring_prompt()
        self.exchange_parser = PydanticOutputParser(pydantic_object=ExchangeScoreResponse)
        self.exchange_chain = self.exchange_prompt | self.model | self.exchange_parser

    def evaluate_statement(self, topic: str, statement: str, user_id: int, memory: 'ConversationBufferWindowMemory',in_favour_string: str = None ,session_store = None,session_id : str =None) -> EvaluationResponse:
        try:
            # Invoke chain with memory's history
            response = self.chain.invoke({
                "topic": topic,
                "statement": statement,
                "user_id": user_id,
                "history": memory.load_memory_variables({})["history"],
                "format_instructions": self.parser.get_format_instructions(),
                "in_favour_string": in_favour_string
            })

            # Save statement and response to memory
            memory.save_context(
                inputs={"input": f"User {user_id}: {statement} (Stance: {in_favour_string})"},
                outputs={"output": response.model_dump_json()}
            )

            #debug :
            logger.debug("*********************************************")
            MemoryManager.print_current_memory(session_store,session_id)
            logger.debug("*********************************************")

            return response
        except Exception as e:
            logger.error(f"Error evaluating statement: {str(e)}")
            raise Exception(f"Error evaluating statement: {str(e)}")

    def score_exchange(self, topic: str, for_user_id: str, for_statement: str,
                       against_user_id: str, against_statement: str,
                       memory: 'ConversationBufferWindowMemory') -> ExchangeScoreResponse:
        try:
            response = self.exchange_chain.invoke({
                "topic": topic,
                "for_user_id": for_user_id,
                "for_statement": for_statement,
                "against_user_id": against_user_id,
                "against_statement": against_statement,
                "history": memory.load_memory_variables({})["history"],
                "format_instructions": self.exchange_parser.get_format_instructions(),
            })
            logger.debug(f"Exchange scored: for={response.for_points}, against={response.against_points}, winner={response.exchange_winner}")
            return response
        except Exception as e:
            logger.error(f"Error scoring exchange: {str(e)}")
            raise Exception(f"Error scoring exchange: {str(e)}")