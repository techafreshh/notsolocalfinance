from typing import List, Dict, Any
from vdb import get_all_transactions, query_transactions

def get_spending_by_category(date_prefixes: list = None) -> str:
    """
    Returns a breakdown of spending (negative transactions) grouped by category.
    Use this to tell the user where their money is going overall.
    Optionally pass date_prefixes (list of YYYY or YYYY-MM) to filter by specific times.
    """
    transactions = get_all_transactions()
    category_totals = {}
    
    for tx in transactions:
        if date_prefixes:
            if not isinstance(date_prefixes, list):
                date_prefixes = [date_prefixes]
            if not any(tx.date.startswith(str(dp)) for dp in date_prefixes):
                continue
            
        if tx.amount < 0:
            cat = tx.category
            category_totals[cat] = category_totals.get(cat, 0.0) + tx.amount
            
    if not category_totals:
        return "No spending found."
        
    result = []
    for cat, total in category_totals.items():
        result.append(f"{cat}: ₦{abs(total):.2f}")
        
    return "\n".join(result)

def get_largest_expenses(limit: int = 5, date_prefixes: list = None) -> str:
    """
    Returns the largest negative transactions (expenses) in the provided limit.
    Use this to tell the user what their biggest individual purchases were.
    Optionally pass date_prefixes (list of YYYY or YYYY-MM) to filter by specific times.
    """
    try:
        if isinstance(limit, dict):
             # LLM hallucinated and gave us a dict
             limit = 5
        else:
             limit = int(limit)
    except (ValueError, TypeError):
        limit = 5
        
    transactions = get_all_transactions()
    
    # Filter for expenses and sort by amount ascending (largest negative first)
    expenses = []
    for tx in transactions:
        if date_prefixes:
            if not isinstance(date_prefixes, list):
                date_prefixes = [date_prefixes]
            if not any(tx.date.startswith(str(dp)) for dp in date_prefixes):
                continue
        if tx.amount < 0:
            expenses.append(tx)
            
    expenses.sort(key=lambda tx: tx.amount)
    
    top_expenses = expenses[:min(limit, len(expenses))]
    
    if not top_expenses:
       return "No expenses found for the specified period."
       
    result = []
    for tx in top_expenses:
        result.append(f"{tx.date} - {tx.description}: ₦{abs(tx.amount):.2f} (Category: {tx.category})")
        
    return "\n".join(result)

def semantic_search_transactions(query: str) -> str:
    """
    Looks up specific transactions matching a user's semantic query.
    For example: "Amazon purchases", "restaurants last month", "salary".
    """
    results = query_transactions(query, limit=5)
    
    if not results:
        return f"No transactions found matching '{query}'"
        
    formatted = []
    for tx in results:
         formatted.append(f"[{tx.date}] {tx.description} | {tx.category} | ₦{abs(tx.amount):.2f}")
         
    return "\n".join(formatted)

def get_total_credit_debit(date_prefixes: list = None) -> str:
    """
    Calculates the exact total amount of money in (credit) and money out (debit).
    Optionally pass date_prefixes (list of YYYY or YYYY-MM) to filter by specific times.
    """
    transactions = get_all_transactions()
    total_credit = 0.0
    total_debit = 0.0
    
    for tx in transactions:
        if date_prefixes:
            if not isinstance(date_prefixes, list):
                date_prefixes = [date_prefixes]
            if not any(tx.date.startswith(str(dp)) for dp in date_prefixes):
                continue
            
        if tx.amount > 0:
            total_credit += tx.amount
        elif tx.amount < 0:
            total_debit += tx.amount
            
    if total_credit == 0 and total_debit == 0:
        return "No transactions found for the specified period."
        
    return f"Total Credit (Money In): ₦{total_credit:.2f}\nTotal Debit (Money Out): ₦{abs(total_debit):.2f}"

def get_spending_by_description(query: str, date_prefixes: list = None) -> str:
    """
    Calculates the exact total amount of money sent to or received from a specific entity/person/description.
    query: A search string like the name of a person or business (e.g. "John", "Amazon")
    Optionally pass date_prefixes (list of YYYY or YYYY-MM) to filter by specific times.
    """
    transactions = get_all_transactions()
    total_credit = 0.0
    total_debit = 0.0
    found_count = 0
    query_lower = str(query).lower()
    
    for tx in transactions:
        if date_prefixes:
            if not isinstance(date_prefixes, list):
                date_prefixes = [date_prefixes]
            if not any(tx.date.startswith(str(dp)) for dp in date_prefixes):
                continue
            
        if query_lower in str(tx.description).lower() or query_lower in str(tx.category).lower():
            found_count += 1
            if tx.amount > 0:
                total_credit += tx.amount
            elif tx.amount < 0:
                total_debit += tx.amount
                
    if found_count == 0:
        return f"No transactions found matching '{query}' for the specified period."
        
    return f"Found {found_count} transactions matching '{query}'.\nTotal Received from '{query}': ₦{total_credit:.2f}\nTotal Sent to '{query}': ₦{abs(total_debit):.2f}"

def get_recipients(date_prefixes: list = None) -> str:
    """
    Returns a list of all names/entities the user has sent money to (debits/expenses).
    Optionally pass date_prefixes (list of YYYY or YYYY-MM) to filter by specific times.
    """
    transactions = get_all_transactions()
    recipients = {}
    
    for tx in transactions:
        if date_prefixes:
            if not isinstance(date_prefixes, list):
                date_prefixes = [date_prefixes]
            if not any(tx.date.startswith(str(dp)) for dp in date_prefixes):
                continue
            
        if tx.amount < 0:
            name = tx.description
            recipients[name] = recipients.get(name, 0.0) + tx.amount
            
    if not recipients:
        return "No outgoing transactions (recipients) found for the specified period."
        
    result = []
    # Sort by amount (most spent first)
    sorted_recipients = sorted(recipients.items(), key=lambda x: x[1])
    for name, total in sorted_recipients:
        result.append(f"{name}: ₦{abs(total):.2f}")
        
    return "List of recipients and total amounts sent:\n" + "\n".join(result)

# A registry of tools that maps function names to actual callables
TOOL_REGISTRY = {
    "get_spending_by_category": get_spending_by_category,
    "get_largest_expenses": get_largest_expenses,
    "semantic_search_transactions": semantic_search_transactions,
    "get_total_credit_debit": get_total_credit_debit,
    "get_spending_by_description": get_spending_by_description,
    "get_recipients": get_recipients
}
