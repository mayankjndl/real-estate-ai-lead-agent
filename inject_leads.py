import json
import uuid
import re
from datetime import datetime
from database import SessionLocal, engine
from models import Session, Lead, Base

# The provided JSON data
anohita_data = [
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:37:11.896172",
    "query": "Looking for a 2Bhk",
    "response": "You're looking for a 2BHK! I have a few options that might interest you.\n\nIn Hinjewadi, I have properties available in the budget of 65L - 90L. Since you're looking for a 2BHK, I assume you're an IT professional. What's your preferred location within Hinjewadi?",
    "intent": "browsing",
    "intent_score": 0.35000014305114746
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:39:37.200431",
    "query": "Looking for a two bhk",
    "response": "Looking for a two BHK, got it! \n\nDirect answer: We have two BHK options available.\n\nShort explanation: Our two BHK properties are suitable for families and professionals, offering a comfortable living space.\n\nNext step: What is your budget range for a two BHK property?",
    "intent": "browsing",
    "intent_score": 0.40065452456474304
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:42:01.070323",
    "query": "Looking for a two bhk",
    "response": "We have options available in Hinjewadi and Baner. In Hinjewadi, a 2BHK can cost between 65L - 90L. Would you like to know more about the Hinjewadi options?",
    "intent": "browsing",
    "intent_score": 0.40065452456474304
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:42:25.956220",
    "query": "Actually I was considering Wakad",
    "response": "Wakad is a great option! We have 2BHK apartments available in Wakad, priced between 70L - 95L. Would you like to know more about the properties and their amenities?",
    "intent": "investment",
    "intent_score": 0.1616947501897812
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:42:56.159424",
    "query": "Sounds good but my budget is under 70 lakhs",
    "response": "In Hinjewadi, a 2BHK within your budget of 70L is possible, but the upper limit would be 65L. Would you like to explore options in Hinjewadi with a 65L budget?I can narrow down options further if you'd like.",
    "intent": "buy",
    "intent_score": 0.1731531322002411
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:43:42.345735",
    "query": "What is the budget for properties in wakad?",
    "response": "In Wakad, properties are priced between 45L - 1.4Cr, depending on the type of flat you're looking for. A 2BHK costs between 70L - 95L. What type of property are you interested in?I can narrow down options further if you'd like.",
    "intent": "investment",
    "intent_score": 0.5319206118583679
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:44:19.517560",
    "query": "I am also browsing renting options",
    "response": "We have some great rental options available! Baner is a premium rental area with 2BHK apartments priced between 25K - 40K. Would you like to know more about the Baner options?Want me to arrange a visit or connect you with our expert?",
    "intent": "rent",
    "intent_score": 0.5205876231193542
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:44:46.758838",
    "query": "Are renting options available in Hingewari",
    "response": "No, Hinjewadi is actually a popular area for buying, not renting. You might be interested in exploring Baner, a premium rental area with options starting from 25K - 40K for a 2BHK.Want me to arrange a visit or connect you with our expert?",
    "intent": "rent",
    "intent_score": 0.4798029661178589
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:45:39.595492",
    "query": "Yes please can you also provide me with different renting suggestions",
    "response": "We have some great rental options available! Baner is a premium rental area with 2BHK apartments priced between 25K - 40K. Would you like to know more about the Baner options?Want me to arrange a visit or connect you with our expert?",
    "intent": "rent",
    "intent_score": 0.6487019062042236
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:46:07.960853",
    "query": "Yes at what time can i visit",
    "response": "We can schedule a visit for you at your convenience. What day and time works best for you?",
    "intent": "browsing",
    "intent_score": 0.1799929440021515
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:46:27.723544",
    "query": "What about resale",
    "response": "Resale properties are also available in Hinjewadi and Wakad. In Hinjewadi, resale 2BHK options are priced between 50L - 80L. In Wakad, resale 2BHK options are priced between 50L - 80L. Would you like me to know more about the resale properties in both areas?Want me to arrange a visit or connect you with our expert?",
    "intent": "buy",
    "intent_score": 0.37821221351623535
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:46:55.679627",
    "query": "sounds good provide me with contact number",
    "response": "Here's the contact number of our expert: 9876543210. Would you like me to have them call you to discuss the details?",
    "intent": "browsing",
    "intent_score": 0.3280823826789856
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:51:16.794794",
    "query": "Lets start over the conversation",
    "response": "Let's start fresh! What are you looking for in terms of real estate? Are you looking to buy or rent a property?",
    "intent": "browsing",
    "intent_score": 0.2348296046257019
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:52:19.603707",
    "query": "looking to buy",
    "response": "I remember you're looking to buy! Since you mentioned Hinjewadi earlier, I'll provide an update. Within your budget of 65L, a 2BHK in Hinjewadi is possible, priced between 65L - 90L. Would you like to explore options in Hinjewadi with a 65L budget?",
    "intent": "browsing",
    "intent_score": 0.5154951214790344
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:52:59.055210",
    "query": "Hingewadi",
    "response": "You're interested in Hinjewadi! That's a popular area for IT professionals. What type of property are you looking for - buy or rent?Want me to arrange a visit or connect you with our expert?",
    "intent": "buy",
    "intent_score": 0.22754210233688354
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:53:22.545447",
    "query": "70 Lakhs Budget",
    "response": "What's your interest in a property within Hinjewadi? Are you looking to buy or rent?Want me to arrange a visit or connect you with our expert?",
    "intent": "buy",
    "intent_score": 0.20855292677879333
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:53:50.399591",
    "query": "Im thinking of switchin to wakad",
    "response": "Wakad's a great choice! It's a fast-growing area with great connectivity to Hinjewadi IT park. What type of property are you looking for in Wakad - a 1BHK, 2BHK, or 3BHK?I can narrow down options further if you'd like.",
    "intent": "investment",
    "intent_score": 0.14870403707027435
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:54:15.381434",
    "query": "I want to rent instead",
    "response": "Let's explore rental options again! You were interested in Baner, a premium rental area with 2BHK apartments priced between 25K - 40K. Would you like to know more about the Baner options?Want me to arrange a visit or connect you with our expert?",
    "intent": "rent",
    "intent_score": 0.6758342981338501
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:54:32.382481",
    "query": "in wakad itself",
    "response": "Wakad has some great options! Are you looking to buy or rent in Wakad?Want me to arrange a visit or connect you with our expert?",
    "intent": "buy",
    "intent_score": 0.19332492351531982
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:54:50.609417",
    "query": "in wakad itself for rent",
    "response": "Wakad has some great rental options! For a 2BHK in Wakad, you can expect to pay between 15K - 25K per month. Are you looking for something specific in terms of amenities or location within Wakad?Want me to arrange a visit or connect you with our expert?",
    "intent": "rent",
    "intent_score": 0.5566961169242859
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:55:08.323097",
    "query": "2bhk for 25k",
    "response": "You're looking for a 2BHK for rent in Baner, priced around 25K.",
    "intent": "browsing",
    "intent_score": 0.24759924411773682
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:55:21.760137",
    "query": "2bhk for 25k in wakad",
    "response": "For a 2BHK in Wakad, you can expect to pay between 15K - 25K per month. Are you looking for something specific in terms of amenities or location within Wakad?I can narrow down options further if you'd like.",
    "intent": "investment",
    "intent_score": 0.2889692783355713
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:55:42.833157",
    "query": "yes ok",
    "response": "Let's get back on track! Since we were discussing buying a property in Hinjewadi, I'd like to confirm: are you still interested in a 2BHK in Hinjewadi with a budget of 65L to 90L?",
    "intent": "browsing",
    "intent_score": 0.3798649311065674
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:56:44.983133",
    "query": "Lets start fresh",
    "response": "Let's start fresh! What type of property are you interested in - buying or renting?",
    "intent": "browsing",
    "intent_score": 0.21360424160957336
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:57:22.570363",
    "query": "Looking to buy",
    "response": "You're looking to buy! Which location are you interested in - Hinjewadi or Wakad?",
    "intent": "browsing",
    "intent_score": 0.5154951214790344
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:57:49.809782",
    "query": "Any location in pune under budget 70 lakhs",
    "response": "You're looking for a property under 70 lakhs in Pune. Hinjewadi and Wakad are great options. Hinjewadi has 2BHK options priced between 65L - 90L. Wakad has 1BHK, 2BHK, and 3BHK options priced between 45L - 1.4Cr. Which area are you leaning towards?Want me to arrange a visit or connect you with our expert?",
    "intent": "rent",
    "intent_score": 0.2407800555229187
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:58:14.487747",
    "query": "What about renting",
    "response": "You're looking to rent! You were previously interested in Baner, a premium rental area with 2BHK apartments priced between 25K - 40K. Would you like to know more about the Baner options?Want me to arrange a visit or connect you with our expert?Want me to arrange a visit or connect you with our expert?",
    "intent": "rent",
    "intent_score": 0.7233901023864746
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:58:43.364192",
    "query": "I want to rent in wakad instead",
    "response": "Wakad has some great rental options! For a 2BHK in Wakad, you can expect to pay between 15K - 25K per month. Are you looking for something specific in terms of amenities or location within Wakad?Want me to arrange a visit or connect you with our expert?",
    "intent": "rent",
    "intent_score": 0.564849317073822
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:59:09.579348",
    "query": "Fully furnished in wakad itself",
    "response": "Fully furnished 2BHK in Wakad sounds great! For that, you can expect to pay around 25K - 35K per month. Would you like me to arrange a visit or connect you with our expert?Want me to arrange a visit or connect you with our expert?",
    "intent": "rent",
    "intent_score": 0.2988714277744293
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:59:29.137653",
    "query": "just browsing for now",
    "response": "Just browsing for now! We're happy to help. You mentioned Hinjewadi as a location. Are you looking to buy a property there?",
    "intent": "browsing",
    "intent_score": 0.57439124584198
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T12:59:53.917428",
    "query": "Not buy rent maybe",
    "response": "You're open to both buying and renting. Let's explore your options further. Are you looking for a specific location, like Hinjewadi or Baner?Want me to arrange a visit or connect you with our expert?",
    "intent": "rent",
    "intent_score": 0.6525364518165588
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T13:01:56.081570",
    "query": "just exploring",
    "response": "You're just exploring! We're happy to help. You mentioned earlier that you're interested in buying a property. Would you like to explore options in Hinjewadi or Wakad?",
    "intent": "browsing",
    "intent_score": 0.7631129026412964
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T13:02:22.091185",
    "query": "not sure",
    "response": "No worries! Since you're not sure, let's take a step back. What type of property are you interested in - buying or renting?",
    "intent": "browsing",
    "intent_score": 0.3578106164932251
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T13:02:41.648381",
    "query": "investment",
    "response": "Investment! Hinjewadi and Wakad are great areas for investment in Pune. Hinjewadi has 2BHK options priced between 65L - 90L, perfect for IT professionals. Wakad has a range of options, including 1BHK, 2BHK, and 3BHK, priced between 45L - 1.4Cr. Which area are you leaning towards?I can narrow down options further if you'd like.",
    "intent": "investment",
    "intent_score": 0.7688489556312561
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T13:02:58.749046",
    "query": "2bhk",
    "response": "2BHK, got it! Are you looking to rent or buy a 2BHK?",
    "intent": "browsing",
    "intent_score": 0.24721603095531464
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T13:03:14.620723",
    "query": "rent?",
    "response": "You're looking to rent! You were previously interested in Baner, a premium rental area with 2BHK apartments priced between 25K - 40K. Would you like to know more about the Baner options?Want me to arrange a visit or connect you with our expert?",
    "intent": "rent",
    "intent_score": 0.7522748708724976
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T13:03:28.849216",
    "query": "ok baner",
    "response": "You're considering Baner again! What specifically are you looking for in a 2BHK in Baner - a specific price range or amenities?",
    "intent": "browsing",
    "intent_score": 0.22903381288051605
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T13:03:59.062888",
    "query": "fully furnished and 65lakhs budget in hingewari",
    "response": "Fully furnished 2BHK in Hinjewadi within your budget of 65 lakhs is a great option! You can find properties around 65-80 lakhs. Want me to arrange a visit or connect you with our expert?I can narrow down options further if you'd like.",
    "intent": "rent",
    "intent_score": 0.3275105655193329
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T13:05:52.007078",
    "query": "Yes please schedule a visit",
    "response": "I'd be happy to schedule a visit for you. Which property would you like to visit - fully furnished 2BHK in Wakad or 2BHK in Baner?",
    "intent": "browsing",
    "intent_score": 0.24859033524990082
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T13:06:15.350968",
    "query": "fully furnished 2bhk in wakad",
    "response": "Fully furnished 2BHK in Wakad! That's a great choice. You're looking for options within a specific budget, right?Want me to arrange a visit or connect you with our expert?",
    "intent": "rent",
    "intent_score": 0.31710726022720337
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T13:06:52.116231",
    "query": "no site visit now just browsing",
    "response": "Just browsing then! You're interested in buying a property. Let's explore options in Hinjewadi or Wakad. Would you like to know more about the 1BHK, 2BHK, or 3BHK options available in these areas?",
    "intent": "browsing",
    "intent_score": 0.3147091269493103
  },
  {
    "user_id": "string",
    "timestamp": "2026-04-10T13:07:18.450383",
    "query": "not interested",
    "response": "No worries! Since you're not interested, I'll just keep an eye out for new options that might catch your attention. Would you like me to keep you updated on new properties that match your previous search criteria?",
    "intent": "browsing",
    "intent_score": 0.5247178077697754
  }
]

def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Safely clear the database of previous incorrect mock insertions without needing to kill the running Uvicorn server
    print("Clearing previous mock data...")
    try:
        db.query(Lead).delete()
        db.query(Session).delete()
        db.commit()
    except Exception as e:
        db.rollback()
    
    print(f"Injecting {len(anohita_data)} records...")
    
    count = 0
    for record in anohita_data:
        # Create a new unique session for each lead in this mock scenario
        session_id = f"ANOHITA-MOCK-{uuid.uuid4().hex[:8]}"
        new_session = Session(id=session_id, client_id="client_A")
        db.add(new_session)
        db.commit() # Commit so foreign key constraint passes
        
        # Parse Intent Score mapping
        intent = record.get("intent", "browsing").lower()
        score = "Low"
        if intent in ["buy", "investment"]:
            score = "High"
        elif intent == "rent":
            score = "Medium"
            
        # Parse Dates
        try:
            timestamp = datetime.fromisoformat(record.get("timestamp"))
        except:
            timestamp = datetime.now()
            
        # Optional field parsing based on query string
        query = record.get("query", "").lower()
        
        location = "Unknown"
        if "wakad" in query:
            location = "Wakad"
        elif "hinjewadi" in query or "hingewari" in query or "hingewadi" in query:
            location = "Hinjewadi"
        elif "baner" in query:
            location = "Baner"
            
        budget = "Unknown"
        # Properly parse real budget numbers (e.g., '70 lakhs', '25k')
        budget_match = re.search(r"(\d+)\s*(lakhs?|k)", query)
        if budget_match:
            val, unit = budget_match.groups()
            budget = f"{val} {unit.capitalize()}"
            
        # Inject Lead
        new_lead = Lead(
            session_id=session_id,
            name=f"Lead_{count}",
            phone=f"+91{str(1000000000 + count)}",
            budget=budget,
            location=location,
            intent=intent.capitalize(),
            score=score,
            updated_at=timestamp
        )
        
        db.add(new_lead)
        count += 1
        
    db.commit()
    db.close()
    
    print(f"✅ Success! Injected {count} leads perfectly formatted into your SQLite database.")

if __name__ == "__main__":
    main()
