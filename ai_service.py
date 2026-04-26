from dotenv import load_dotenv
load_dotenv()
import os
import logfire
from typing import List, Dict, Any, Optional
from pydantic_ai import Agent, RunContext, ModelRetry

from pydantic_ai.messages import ModelMessage, ModelResponse, ModelRequest, TextPart, ToolCallPart

from tools import (
    get_spending_by_category, get_largest_expenses, semantic_search_transactions,
    get_monthly_summary, compare_periods, get_income_by_source,
    detect_anomalies, get_transaction_frequency, get_category_trend,
    get_transactions_by_date_range, get_spending_velocity, get_running_balance,
    get_total_credit_debit, get_spending_by_description, get_recipients,
    get_day_of_week_analysis, get_time_of_month_analysis, get_largest_expense_categories,
    find_similar_transactions, get_merchant_spending, get_top_merchants,
    get_merchant_comparison, detect_recurring_transactions, get_subscription_summary,
    get_upcoming_payments
)

# Optional: Initialize Logfire for observability
if os.environ.get("LOGFIRE_TOKEN"):
    logfire.configure()
    logfire.instrument_pydantic_ai()

# System Prompt
SYSTEM_PROMPT = (
    "You are a helpful personal finance AI assistant. You have access to tools that can query the user's "
    "uploaded bank statements and transactions. If a user asks a question about their spending, use the "
    "provided tools to fetch the data before answering. The currency is Naira (₦). Pay strict attention "
    "to the date requested by the user. If they ask for '2025 and 2026', pass date_prefixes as ['2025', '2026']. "
    "Do not assume or hallucinate a specific month (like '-07') unless the user explicitly asks for it. "
    "IMPORTANT: When searching for 'sender' or 'receiver', note that the transaction descriptions usually "
    "contain phrases like 'FROM [Name]' or 'TO [Name]'. Do not search for the literal word 'sender'; "
    "instead, search for specific names or use 'FROM' / 'TO' keywords in your query to find relevant entries."
)

# Initialize Agent with native OpenRouter support
# Pydantic AI now supports OpenRouter natively. 
# We pass the model directly without needing the openai library.
agent = Agent(
    'openrouter:mistralai/mistral-nemo',
    system_prompt=SYSTEM_PROMPT,
    deps_type=str,
)

# Register Tools
agent.tool(get_spending_by_category)
agent.tool(get_largest_expenses)
agent.tool(semantic_search_transactions)
agent.tool(get_monthly_summary)
agent.tool(compare_periods)
agent.tool(get_income_by_source)
agent.tool(detect_anomalies)
agent.tool(get_transaction_frequency)
agent.tool(get_category_trend)
agent.tool(get_transactions_by_date_range)
agent.tool(get_spending_velocity)
agent.tool(get_running_balance)
agent.tool(get_total_credit_debit)
agent.tool(get_spending_by_description)
agent.tool(get_recipients)
agent.tool(get_day_of_week_analysis)
agent.tool(get_time_of_month_analysis)
agent.tool(get_largest_expense_categories)
agent.tool(find_similar_transactions)
agent.tool(get_merchant_spending)
agent.tool(get_top_merchants)
agent.tool(get_merchant_comparison)
agent.tool(detect_recurring_transactions)
agent.tool(get_subscription_summary)
agent.tool(get_upcoming_payments)

def _convert_history_to_pydantic_ai(history: List[Dict[str, Any]]) -> List[ModelMessage]:
    """
    Very basic conversion of generic message history to Pydantic AI ModelMessages.
    """
    pydantic_history = []
    
    for msg in history:
        role = msg.get("role")
        content = msg.get("content", "")
        
        if role == "user":
            pydantic_history.append(ModelRequest(parts=[TextPart(content)]))
        elif role == "assistant":
            pydantic_history.append(ModelResponse(parts=[TextPart(content)]))
            
    return pydantic_history

async def chat_with_ai(messages: List[Dict[str, Any]], user_id: str) -> tuple[str, List[Dict[str, Any]]]:
    """
    Handles a conversation using Pydantic AI and OpenRouter.
    Returns (response_text, updated_messages_list)
    """
    if not messages:
        return "No message received.", messages
        
    last_message = messages[-1]
    if last_message.get("role") != "user":
         return "Please send a user message.", messages
         
    user_prompt = last_message.get("content", "")
    history_messages = messages[:-1]
    
    try:
        result = await agent.run(
            user_prompt, 
            message_history=_convert_history_to_pydantic_ai(history_messages),
            deps=user_id
        )
        
        # Build back JSON history format
        new_history = []
        for msg in result.all_messages():
            if isinstance(msg, ModelRequest):
                for part in msg.parts:
                    if isinstance(part, TextPart):
                        new_history.append({"role": "user", "content": part.content})
            elif isinstance(msg, ModelResponse):
                for part in msg.parts:
                    if isinstance(part, TextPart):
                         new_history.append({"role": "assistant", "content": part.content})

        return result.output, new_history

    except Exception as e:
        return f"Error: {str(e)}", messages

# Backward compatibility
chat_with_granite = chat_with_ai
