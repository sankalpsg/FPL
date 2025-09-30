# main.py

import asyncio
from config import LEAGUE_ID, MONTH_TO_GWS
from fpl_client import FPLClient
import aiohttp

async def compute_monthly(league_id, month_to_gws):
    async with aiohttp.ClientSession() as session:
        client = FPLClient(session)
        entries = await client.get_league_entries(league_id)
        results = {}
        for ent in entries:
            eid = ent["entry"]  # or ent["entry_id"], inspect what the API returns
            results[eid] = {}
            for month, gws in month_to_gws.items():
                total = 0
                for gw in gws:
                    pts = await client.get_entry_score_for_gw(eid, gw)
                    total += pts
                results[eid][month] = total
        return results

def main():
    monthly = asyncio.run(compute_monthly(LEAGUE_ID, MONTH_TO_GWS))
    print("Monthly custom scores:")
    for eid, mdata in monthly.items():
        print(f"Entry {eid}:")
        for month, pts in mdata.items():
            print(f"  Month {month}: {pts}")

if __name__ == "__main__":
    main()
