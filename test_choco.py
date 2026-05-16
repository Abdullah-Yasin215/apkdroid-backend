import asyncio
import httpx

async def test():
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://community.chocolatey.org/api/v2/Packages?$filter=IsLatestVersion&$top=5",
            headers={"Accept": "application/json"}
        )
        print("Status:", resp.status_code)
        try:
            print("Keys:", resp.json().keys())
            data = resp.json()
            if "d" in data:
                print("First app title:", data["d"][0]["Title"])
            elif "value" in data:
                print("First app title:", data["value"][0]["Title"])
        except Exception as e:
            print("Text:", resp.text[:200])

asyncio.run(test())
