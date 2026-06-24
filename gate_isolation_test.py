import httpx
import asyncio


async def test_isolation():
    print("--- STARTING TENANT ISOLATION TEST ---")
    # Replace these with your actual keys from .env
    KEY_A = "a8d4a6ce95b7e108839cb6920cfc8c9561a8c8abf0fe90b14c4f88f1c687ff09"
    KEY_B = "84bb6274da76a73053d5db8ccf55f1b07d9ba69af2d61a1fdfae1fea7e69c124"

    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Create a lead for Client A
        print("\n1. Injecting Lead into Client A's Workspace...")
        await client.post("/api/v1/whatsapp", data={"From": "+919999911111", "Body": "I want to buy 2BHK Baner"},
                          params={"api_key": KEY_A})

        # Check Client A's Dashboard
        res_a = await client.get("/api/v1/leads", headers={"X-API-Key": KEY_A})
        print(f"Client A Leads Found: {res_a.json().get('total_returned')}")

        # Check Client B's Dashboard (Should be isolated!)
        res_b = await client.get("/api/v1/leads", headers={"X-API-Key": KEY_B})
        print(f"Client B Leads Found: {res_b.json().get('total_returned')}")

        if res_a.json().get('total_returned') > res_b.json().get('total_returned'):
            print("\n✅ ISOLATION TEST PASSED: Client B cannot see Client A's data.")
        else:
            print("\n❌ ISOLATION TEST FAILED: Data leakage detected.")


asyncio.run(test_isolation())