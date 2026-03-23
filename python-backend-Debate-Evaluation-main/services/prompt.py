from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder

def get_evaluation_prompt():
    system_message = SystemMessagePromptTemplate.from_template(
        """
        You are an expert debate evaluator. Your task is to evaluate a user's debate statement for factual accuracy and relevance to the given topic, considering the conversation history and the user's stance (in favor or against). Return a JSON response according to the provided format instructions. Use the conversation history to assess context, ensuring the statement responds appropriately to prior statements. For factual accuracy, provide a list of credible source URLs or references (e.g., scientific journals, reputable news, or reports) that support your evaluation. If specific URLs are unavailable, suggest authoritative sources (e.g., 'IPCC reports', 'WHO guidelines').

        {format_instructions}
        """
    )
    history_placeholder = MessagesPlaceholder(variable_name="history")
    human_message = HumanMessagePromptTemplate.from_template(
        """
        Topic: {topic}
        User {user_id} Statement: {statement}
        User Stance: {in_favour_string}

        Evaluate the statement and return the result in JSON format.
        """
    )
    return ChatPromptTemplate.from_messages([system_message, history_placeholder, human_message])


def get_exchange_scoring_prompt():
    system_message = SystemMessagePromptTemplate.from_template(
        """
        You are an expert debate judge. Your task is to evaluate a complete exchange between two debaters:
        one arguing FOR the topic and one arguing AGAINST it.

        Score each debater from 0 to 10 based on:
        - Argument strength and logical coherence (40%)
        - Factual accuracy (30%)
        - Relevance to the topic (20%)
        - Quality of rebuttal against prior arguments in the conversation (10%)

        Use the conversation history to assess whether each debater responded well to previous arguments.
        Be fair and unbiased. If both arguments are equally strong, award a tie.

        Return a JSON response according to the provided format instructions.

        {format_instructions}
        """
    )
    history_placeholder = MessagesPlaceholder(variable_name="history")
    human_message = HumanMessagePromptTemplate.from_template(
        """
        Topic: {topic}

        FOR argument (User {for_user_id}):
        "{for_statement}"

        AGAINST argument (User {against_user_id}):
        "{against_statement}"

        Judge this exchange and assign points to each debater (0-10 each). Return the result in JSON format.
        """
    )
    return ChatPromptTemplate.from_messages([system_message, history_placeholder, human_message])
