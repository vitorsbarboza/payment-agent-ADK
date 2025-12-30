"""
Send Money Agent Flow using Google ADK
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from google import genai
from google.genai.types import Tool, GenerateContentConfig, GoogleSearch


# State Schema
class TransferState(BaseModel):
    """State tracking for money transfer process"""
    beneficiary_name: Optional[str] = None
    beneficiary_id: Optional[str] = None
    destination_country: Optional[str] = None
    amount: Optional[float] = None
    currency: str = "USD"
    delivery_method: Optional[str] = None
    needs_clarification: bool = False
    clarification_options: List[dict] = Field(default_factory=list)
    last_asked_field: Optional[str] = None


# Mock Data
MOCK_CONTACTS = [
    {"id": "B001", "name": "John Smith", "country": "Brazil"},
    {"id": "B002", "name": "John Smith", "country": "Mexico"},
    {"id": "B003", "name": "Maria Garcia", "country": "Spain"},
    {"id": "B004", "name": "Carlos Rodriguez", "country": "Argentina"},
    {"id": "B005", "name": "Ana Silva", "country": "Portugal"},
]

SUPPORTED_COUNTRIES = [
    "Brazil", "Mexico", "Spain", "Argentina", "Portugal",
    "United Kingdom", "Canada", "India", "Philippines", "Colombia"
]

EXCHANGE_RATES = {
    "Brazil": {"rate": 5.25, "symbol": "BRL"},
    "Mexico": {"rate": 18.50, "symbol": "MXN"},
    "Spain": {"rate": 0.92, "symbol": "EUR"},
    "Argentina": {"rate": 350.00, "symbol": "ARS"},
    "Portugal": {"rate": 0.92, "symbol": "EUR"},
    "United Kingdom": {"rate": 0.79, "symbol": "GBP"},
    "Canada": {"rate": 1.35, "symbol": "CAD"},
    "India": {"rate": 83.20, "symbol": "INR"},
    "Philippines": {"rate": 56.50, "symbol": "PHP"},
    "Colombia": {"rate": 4100.00, "symbol": "COP"},
}


# Tool Functions
def search_contacts(query: str) -> dict:
    """
    Search for beneficiaries by name.
    If multiple matches found, return them for clarification.
    
    Args:
        query: Name or partial name to search for
    
    Returns:
        Dictionary with matches or single contact
    """
    query_lower = query.lower()
    matches = [c for c in MOCK_CONTACTS if query_lower in c["name"].lower()]
    
    if len(matches) == 0:
        return {
            "found": False,
            "message": f"No beneficiary found with name '{query}'. Please try another name or provide beneficiary details."
        }
    elif len(matches) == 1:
        return {
            "found": True,
            "single": True,
            "contact": matches[0]
        }
    else:
        return {
            "found": True,
            "single": False,
            "multiple": True,
            "matches": matches,
            "message": f"Found {len(matches)} beneficiaries named '{query}'. Please select one."
        }


def get_supported_countries() -> dict:
    """
    Get list of countries where money can be sent.
    
    Returns:
        Dictionary with list of supported countries
    """
    return {
        "countries": SUPPORTED_COUNTRIES,
        "count": len(SUPPORTED_COUNTRIES)
    }


def calculate_fx_rate(amount: float, country: str) -> dict:
    """
    Calculate foreign exchange rate and total for destination country.
    
    Args:
        amount: Amount in USD
        country: Destination country name
    
    Returns:
        Dictionary with exchange rate details
    """
    if country not in EXCHANGE_RATES:
        return {
            "error": True,
            "message": f"Exchange rate not available for {country}. Please check supported countries."
        }
    
    rate_info = EXCHANGE_RATES[country]
    total_foreign = amount * rate_info["rate"]
    
    return {
        "success": True,
        "source_amount": amount,
        "source_currency": "USD",
        "destination_currency": rate_info["symbol"],
        "exchange_rate": rate_info["rate"],
        "destination_amount": round(total_foreign, 2),
        "country": country
    }


# Define tools for the agent
def get_tools() -> List[Tool]:
    """Return list of tools for the agent"""
    return [
        Tool(function_declarations=[
            {
                "name": "search_contacts",
                "description": "Search for a beneficiary by name in the contact list. Returns contact details or multiple matches requiring clarification.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The name or partial name of the beneficiary to search for"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_supported_countries",
                "description": "Get the list of countries where money transfers are supported.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "calculate_fx_rate",
                "description": "Calculate the foreign exchange rate and converted amount for a transfer to a specific country.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "amount": {
                            "type": "number",
                            "description": "The amount in USD to convert"
                        },
                        "country": {
                            "type": "string",
                            "description": "The destination country for the transfer"
                        }
                    },
                    "required": ["amount", "country"]
                }
            }
        ])
    ]


# Tool execution dispatcher
def execute_tool(tool_name: str, tool_args: dict) -> dict:
    """Execute the requested tool with provided arguments"""
    if tool_name == "search_contacts":
        return search_contacts(tool_args.get("query", ""))
    elif tool_name == "get_supported_countries":
        return get_supported_countries()
    elif tool_name == "calculate_fx_rate":
        return calculate_fx_rate(
            tool_args.get("amount", 0),
            tool_args.get("country", "")
        )
    else:
        return {"error": f"Unknown tool: {tool_name}"}


def create_system_instruction() -> str:
    """Create system instruction for the Send Money Agent"""
    return """You are a helpful Send Money Agent that assists users in transferring money internationally.

Your role is to:
1. Collect all necessary information: beneficiary name, destination country, amount, and delivery method
2. Use the search_contacts tool to find beneficiaries
3. Use get_supported_countries to show available destinations
4. Use calculate_fx_rate to provide exchange rate information
5. If user tries to change any detail (like country), acknowledge it and ask for confirmation before proceeding
6. Guide users step by step through the transfer process
7. Be conversational, friendly, and clear
8. Once all information is collected, provide a natural language summary of the transfer

When a user provides information:
- Search for beneficiaries using search_contacts
- If multiple matches found, ask user to clarify which one
- Validate country against supported countries list
- Calculate exchange rates when amount and country are known
- Ask for delivery method (Bank Transfer, Cash Pickup, Mobile Wallet)

If user wants to change something already provided:
- Acknowledge the change
- Ask for confirmation
- Update the information only after confirmation

Be proactive in asking for missing information one piece at a time.
"""
