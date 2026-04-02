import json
import google.generativeai as genai
from config import settings
from system_prompt import REAL_ESTATE_SYSTEM_PROMPT
from sqlalchemy.orm import Session as DBSession
from models import Session, Message, Lead

# 1. Gemini Initialization
genai.configure(api_key=settings.GEMINI_API_KEY)

# 4. Structured Tool Calling Definition
def extract_lead_info(
    name: str = None, 
    phone: str = None, 
    budget: str = None, 
    location: str = None, 
    intent: str = None, 
    score: str = None
):
    """
    Saves or updates the lead's information in the database. Use this tool silently when the user shares their budget, location, intent (buy/rent/investment), name, or phone number.

    Args:
        name: The name of the client.
        phone: The phone number of the client.
        budget: The requested budget range (e.g., '80L', '20k', '1Cr').
        location: The area they are looking in (e.g., 'Hinjewadi', 'Pune').
        intent: The goal (e.g., 'buy', 'rent', 'investment', 'browsing').
        score: Your internal lead scoring evaluation (High, Medium, Low).
    """
    pass # This function is a schema definition for Gemini. Execution is handled manually in process_chat.

# Initialize the generative model with the Anohita's system instruction and the extraction tool
model = genai.GenerativeModel(
    model_name=settings.GEMINI_MODEL,
    system_instruction=REAL_ESTATE_SYSTEM_PROMPT,
    tools=[extract_lead_info]
)

# 3. Stateful Memory Function
def process_chat(session_id: str, user_message: str, db: DBSession, client_id: str = "default") -> str:
    """
    Main orchestrator for user input. Fetches memory, injects context to the LLM, 
    extracts function calls for lead generation, and commits all data to DB.
    """
    
    # Ensure session exists in the database
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        session = Session(id=session_id, client_id=client_id)
        db.add(session)
        db.commit()

    # Save the new user message to the Message table
    db.add(Message(session_id=session_id, role="user", content=user_message))
    db.commit()

    # Query all past messages belonging to this session_id up to the current turn
    past_messages = db.query(Message).filter(Message.session_id == session_id).order_by(Message.id).all()
    
    formatted_history = []
    # Loop over all history EXCEPT the last message we just pushed to the DB 
    for m in past_messages[:-1]: 
        role = "user" if m.role == "user" else "model"
        formatted_history.append({"role": role, "parts": [m.content]})

    # Start Gemini Chat with retrieved history
    chat = model.start_chat(history=formatted_history)

    # Send the history + new message to Gemini
    response = chat.send_message(user_message)

    # 5. Database Commits & Tool Execution Handling
    # Detect if Gemini triggered the lead extraction tool
    fc = None
    # We look inside the 'parts' of the response to find the function call
    if response.candidates and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if part.function_call:
                fc = part.function_call
                break

    if fc and fc.name == "extract_lead_info":
        # Extract arguments payload securely
        args = fc.args
        
        # Fetch existing lead record or create a new one
        lead = db.query(Lead).filter(Lead.session_id == session_id).first()
        if not lead:
            lead = Lead(session_id=session_id)
            db.add(lead)
        
        # Update Lead table fields dynamically
        if "name" in args: lead.name = args["name"]
        if "phone" in args: lead.phone = args["phone"]
        if "budget" in args: lead.budget = args["budget"]
        if "location" in args: lead.location = args["location"]
        if "intent" in args: lead.intent = args["intent"]
        if "score" in args: lead.score = args["score"]
        
        db.commit()
        
        # Send tool response confirmation back to Gemini
        tool_res_part = genai.protos.Part(
            function_response=genai.protos.FunctionResponse(
                name="extract_lead_info",
                response={"status": "Extracted lead data saved successfully."}
            )
        )
        response = chat.send_message(tool_res_part)

    # Safely get the final text (handling cases where only a tool call was returned)
    try:
        final_text = response.text
    except ValueError:
        final_text = "I've noted those details. What else can I help you find today?"

    # Save Gemini's textual response to the Message table
    db.add(Message(session_id=session_id, role="assistant", content=final_text))
    db.commit()
    
    # Return the text response isolated from tool calls
    return final_text