import ollama
import os
import json
from typing import List, Dict, Any
from tools import get_spending_by_category, get_largest_expenses, semantic_search_transactions, TOOL_REGISTRY

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://host.docker.internal:11434")
OLLAMA_MODEL = "granite4:latest"

try:
    ollama_client = ollama.Client(host=OLLAMA_HOST)
except Exception as e:
    print(f"Warning: Could not connect to Ollama in ai_service.py: {e}")

# Provide Ollama the tool definitions using JSON schemas
OLLAMA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_spending_by_category",
            "description": "Returns a breakdown of spending (negative transactions) grouped by category.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_prefixes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of date prefixes to filter by, e.g., ['2025', '2026'] or ['2025-07']."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_largest_expenses",
            "description": "Returns the largest negative transactions (expenses).",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Limit of expenses to return."
                    },
                    "date_prefixes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of date prefixes to filter by, e.g., ['2025', '2026'] or ['2025-07']."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "semantic_search_transactions",
            "description": "Looks up specific transactions matching a query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query string."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_total_credit_debit",
            "description": "Calculates the exact total amount of money in (credit) and money out (debit).",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_prefixes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of date prefixes to filter by, e.g., ['2025', '2026'] or ['2025-07']."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_spending_by_description",
            "description": "Calculates the exact total amount of money sent to or received from a specific person, business, or entity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The name of the entity, person, or business (e.g. 'John', 'Amazon')."
                    },
                    "date_prefixes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of date prefixes to filter by, e.g., ['2025', '2026'] or ['2025-07']."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recipients",
            "description": "Returns a list of all names/entities the user has sent money to (debits/expenses). Use this when the user asks who they have sent money to or asks for a list of payees.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_prefixes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of date prefixes to filter by, e.g., ['2025', '2026'] or ['2025-07']."
                    }
                },
                "required": []
            }
        }
    }
]

def chat_with_granite(messages: List[Dict[str, Any]]) -> tuple[str, List[Dict[str, Any]]]:
    """
    Handles a conversation with Granite 4 executing tools natively via the ollama-python client.
    Returns a tuple of (response_text, updated_messages_list)
    """
    
    # Ensure system prompt is set to guide behavior
    system_message = {
        "role": "system",
        "content": "You are a helpful personal finance AI assistant. You have access to tools that can query the user's uploaded bank statements and transactions. If a user asks a question about their spending, use the provided tools to fetch the data before answering. The currency is Naira (₦). Pay strict attention to the date requested by the user. If they ask for '2025 and 2026', pass date_prefixes as ['2025', '2026']. Do not assume or hallucinate a specific month (like '-07') unless the user explicitly asks for it."
    }
    
    if len(messages) == 0 or messages[0].get("role") != "system":
        messages.insert(0, system_message)
        
    try:
        # Loop to handle possible sequential tool call chains
        while True:
            # Step 1: Send messages + tool definitions to Granite
            response = ollama_client.chat(
                model=OLLAMA_MODEL,
                messages=messages,
                tools=OLLAMA_TOOLS
            )
            
            # safely extract message whether it's an object or dict
            msg = response.get("message") if isinstance(response, dict) else response.message
            
            # Step 2: Check if Granite wants to call any tools
            tool_calls = msg.get("tool_calls") if isinstance(msg, dict) else msg.tool_calls
            
            if tool_calls:
                # Add the model's call tool request to the messages array
                if isinstance(msg, dict):
                     messages.append(msg)
                else:
                     # For serialization
                     messages.append({
                         "role": msg.role,
                         "content": msg.content or "",
                         "tool_calls": getattr(msg, "tool_calls", [])
                     })
                
                # Execute all requested functions
                for tool_call in tool_calls:
                    # Handle dictionary or object attribute
                    func_data = tool_call.get("function") if isinstance(tool_call, dict) else tool_call.function
                    function_name = func_data.get("name") if isinstance(func_data, dict) else func_data.name
                    kwargs = func_data.get("arguments", {}) if isinstance(func_data, dict) else func_data.arguments or {}
                    
                    print(f"Executing tool {function_name} with args {kwargs}", flush=True)
                    
                    # Retrieve the callable from registry
                    if function_name in TOOL_REGISTRY:
                        func_to_call = TOOL_REGISTRY[function_name]
                        
                        # Execute with provided arguments
                        try:
                            tool_result = func_to_call(**kwargs)
                        except Exception as e:
                            tool_result = f"Error executing tool {function_name}: {e}"
                            
                        print(f"Tool {function_name} returned: {tool_result}", flush=True)
                        
                        # Add the result to the messages array
                        messages.append({
                            "role": "tool",
                            "content": str(tool_result),
                            "name": function_name
                        })
                    else:
                        messages.append({
                            "role": "tool",
                            "content": f"Error: Tool {function_name} not found.",
                            "name": function_name
                        })
                        
                # After appending tool results, let the while loop repeat to send them back to the LLM
                continue
                
            else:
                # Model didn't want to call tools, it's done and returned a response directly
                content = msg.get("content") if isinstance(msg, dict) else msg.content
                
                # If content is None or completely empty but we are supposed to be done, provide a fallback
                if not content or not str(content).strip():
                    content = "I've analyzed the data, but I couldn't formulate a textual response. Please check the logs."
                    
                if isinstance(msg, dict):
                     messages.append(msg)
                else:
                     messages.append({"role": msg.role, "content": content})
                     
                print(f"Final LLM Response: {content}", flush=True)
                return content, messages
                
    except Exception as e:
        return f"Error communicating with AI service: {str(e)}", messages
