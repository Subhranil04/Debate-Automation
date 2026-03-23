from flask import Blueprint, request, jsonify
from services.model import DebateEvaluator
from services.memory import MemoryManager
from models.pydantic_models import EvaluationResponse
from typing import Optional

api_bp = Blueprint("api", __name__)
evaluator: Optional[DebateEvaluator] = None
memory_manager = MemoryManager(k=5)


def get_evaluator() -> DebateEvaluator:
    global evaluator
    if evaluator is None:
        evaluator = DebateEvaluator()
    return evaluator


@api_bp.route("/", methods=["GET"])
def home():
    return jsonify({"Message": "Welcome to Debate Analyzer"}), 200

@api_bp.route("/start_session", methods=["POST"])
def start_session():
    try:
        data = request.get_json()
        topic = data.get("topic")
        if not topic:
            return jsonify({"error": "Topic is required"}), 400
    
        session_id = memory_manager.create_session(topic)
        return jsonify({"session_id": session_id}), 201
    except Exception as e:
        return jsonify({"error": f"Failed to create session: {str(e)}"}), 500


@api_bp.route("/evaluate", methods=["POST"])
def evaluate_statement():
    data = request.get_json()
    session_id = data.get("session_id")
    user_id = data.get("user_id")
    statement = data.get("statement")
    in_favour = data.get("in_favour")

    print(session_id,"  ",user_id,"  ",statement)

    if not all([session_id, user_id, statement, in_favour is not None]):
        return jsonify({"error": "session_id, user_id, statement, and in_favour are required"}), 400

    try:
        # Converting boolean to string for the prompt
        in_favour_string = "in favor" if in_favour else "against"

        # Get topic and memory
        topic = memory_manager.get_topic(session_id)
        memory = memory_manager.get_memory(session_id)

        # Evaluate statement
        evaluation = get_evaluator().evaluate_statement(topic, statement, user_id, memory, in_favour_string)

        # Get conversation history
        history = [
            {"type": msg.__class__.__name__, "content": msg.content}
            for msg in memory.load_memory_variables({})["history"]
        ]

        return jsonify({
            "evaluation": evaluation.model_dump(),
            "history": history
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/score_exchange", methods=["POST"])
def score_exchange():
    data = request.get_json()
    session_id = data.get("session_id")
    for_user_id = data.get("for_user_id")
    for_statement = data.get("for_statement")
    against_user_id = data.get("against_user_id")
    against_statement = data.get("against_statement")

    if not all([session_id, for_user_id, for_statement, against_user_id, against_statement]):
        return jsonify({"error": "session_id, for_user_id, for_statement, against_user_id, against_statement are required"}), 400

    try:
        topic = memory_manager.get_topic(session_id)
        memory = memory_manager.get_memory(session_id)

        result = get_evaluator().score_exchange(
            topic, for_user_id, for_statement,
            against_user_id, against_statement, memory
        )

        return jsonify({"score": result.model_dump()}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
