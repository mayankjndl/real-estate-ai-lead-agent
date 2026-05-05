import asyncio
from agent import process_chat
from database import SessionLocal

async def test():
    db = SessionLocal()
    #res = await process_chat('+919999999999', "I am looking to buy a 2BHK flat in Baner", db)
    #print("RES:", res)
    
    res2 = await process_chat('+919999999999', "My name is Rohan Sharma", db)
    print("RES2:", res2)

asyncio.run(test())
