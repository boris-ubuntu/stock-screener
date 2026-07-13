import asyncio
import httpx
import json


async def test_moex():
    """Тестовый запрос к MOEX API"""
    url = "https://iss.moex.com/iss/history/engines/stock/markets/shares/boards/TQBR/securities/SBER.json"

    params = {
        "iss.meta": "off",
        "iss.only": "history",
        "from": "2025-07-05",
        "till": "2026-07-05",
        "start": 0,
        "limit": 100
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Keys: {list(data.keys())}")

            if "history" in data:
                history = data["history"]
                print(f"History keys: {list(history.keys())}")
                print(f"Total: {history.get('total', 'N/A')}")
                print(f"Columns: {history.get('columns', [])}")
                print(f"Data rows: {len(history.get('data', []))}")

                # Покажем первые 3 записи
                rows = history.get('data', [])[:3]
                columns = history.get('columns', [])
                for row in rows:
                    print(dict(zip(columns, row)))
        else:
            print(f"Error: {response.text}")


if __name__ == "__main__":
    asyncio.run(test_moex())