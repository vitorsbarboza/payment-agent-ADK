"""
FastAPI Backend for Send Money Agent
Manages sessions and integrates with Google ADK
"""
import os
import uuid
from typing import Dict, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai
from google.genai.types import GenerateContentConfig, Part, Content

from flows import (
    TransferState,
    get_tools,
    execute_tool,
    create_system_instruction
)

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(title="Send Money Agent API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Google Generative AI client
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# In-memory session storage (use Redis or database in production)
sessions: Dict[str, dict] = {}


# Request/Response Models
class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    response: str
    state: TransferState


class SessionResponse(BaseModel):
    session_id: str
    message: str


# Helper Functions
def get_or_create_session(session_id: str) -> dict:
    """Get existing session or create new one"""
    if session_id not in sessions:
        sessions[session_id] = {
            "state": TransferState(),
            "history": [],
            "chat": None
        }
    return sessions[session_id]


def process_tool_calls(response, state: TransferState) -> tuple[str, TransferState]:
    """Process tool calls from the model and update state"""
    tool_results = []
    
    for part in response.candidates[0].content.parts:
        if hasattr(part, 'function_call') and part.function_call:
            func_call = part.function_call
            tool_name = func_call.name
            tool_args = dict(func_call.args)
            
            # Execute the tool
            result = execute_tool(tool_name, tool_args)
            
            # Update state based on tool results
            if tool_name == "search_contacts":
                if result.get("single"):
                    contact = result["contact"]
                    state.beneficiary_name = contact["name"]
                    state.beneficiary_id = contact["id"]
                    state.destination_country = contact["country"]
                    state.needs_clarification = False
                    state.clarification_options = []
                elif result.get("multiple"):
                    state.needs_clarification = True
                    state.clarification_options = [
                        {
                            "id": c["id"],
                            "label": f"{c['name']} - {c['country']}",
                            "value": c["id"]
                        }
                        for c in result["matches"]
                    ]
                    state.last_asked_field = "beneficiary"
            
            # Prepare tool result for the model
            tool_results.append(
                Content(
                    role="user",
                    parts=[
                        Part.from_function_response(
                            name=tool_name,
                            response=result
                        )
                    ]
                )
            )
    
    return tool_results, state


def extract_state_from_conversation(history: List, current_state: TransferState) -> TransferState:
    """Extract state information from conversation history"""
    # This is a simple implementation - in production, use more sophisticated NLU
    return current_state


# API Endpoints
@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "Send Money Agent"}


@app.post("/session/create", response_model=SessionResponse)
async def create_session():
    """Create a new chat session"""
    session_id = str(uuid.uuid4())
    get_or_create_session(session_id)
    return SessionResponse(
        session_id=session_id,
        message="Session created successfully"
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a chat message"""
    try:
        # Get or create session
        session = get_or_create_session(request.session_id)
        state = session["state"]
        history = session["history"]
        
        # Reset clarification if user is responding to it
        if state.needs_clarification:
            # Check if message matches a clarification option
            for option in state.clarification_options:
                if option["value"] in request.message or option["label"].lower() in request.message.lower():
                    # User selected an option
                    if state.last_asked_field == "beneficiary":
                        # Find the contact and update state
                        from flows import MOCK_CONTACTS
                        contact = next((c for c in MOCK_CONTACTS if c["id"] == option["value"]), None)
                        if contact:
                            state.beneficiary_name = contact["name"]
                            state.beneficiary_id = contact["id"]
                            state.destination_country = contact["country"]
                    
                    state.needs_clarification = False
                    state.clarification_options = []
                    state.last_asked_field = None
                    break
        
        # Prepare messages for the model
        model_config = GenerateContentConfig(
            system_instruction=create_system_instruction(),
            tools=get_tools(),
            temperature=0.7,
        )
        
        # Add user message to history
        history.append(Content(role="user", parts=[Part(text=request.message)]))
        
        # Generate response
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=history,
            config=model_config
        )
        
        # Process any tool calls
        if response.candidates[0].content.parts:
            first_part = response.candidates[0].content.parts[0]
            if hasattr(first_part, 'function_call') and first_part.function_call:
                # Add model's response to history
                history.append(response.candidates[0].content)
                
                # Process tool calls
                tool_results, state = process_tool_calls(response, state)
                
                # Add tool results to history
                history.extend(tool_results)
                
                # Get final response after tool execution
                response = client.models.generate_content(
                    model="gemini-2.5-flash", #gemini-2.5-pro
                    contents=history,
                    config=model_config
                )
        
        # Extract response text
        response_text = ""
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'text'):
                    response_text += part.text
        
        # Add assistant response to history
        history.append(response.candidates[0].content)
        
        # Update session
        session["state"] = state
        session["history"] = history
        
        return ChatResponse(
            session_id=request.session_id,
            response=response_text,
            state=state
        )
    
    except Exception as e:
        error_message = str(e)
        
        # Handle specific quota errors with user-friendly messages
        if "RESOURCE_EXHAUSTED" in error_message or "quota" in error_message.lower():
            raise HTTPException(
                status_code=429,
                detail="API quota exceeded. Please try again in a few moments or check your Google API quota limits."
            )
        elif "API key" in error_message:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key. Please check your GOOGLE_API_KEY environment variable."
            )
        else:
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/session/{session_id}/state")
async def get_session_state(session_id: str):
    """Get current state of a session"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "state": sessions[session_id]["state"]
    }


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    if session_id in sessions:
        del sessions[session_id]
        return {"message": "Session deleted successfully"}
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/sessions")
async def list_sessions():
    """List all active sessions (for debugging)"""
    return {
        "count": len(sessions),
        "sessions": list(sessions.keys())
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
