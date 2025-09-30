# fpl_client.py

import aiohttp
from fpl import FPL

class FPLClient:
    def __init__(self, session, username=None, password=None):
        self.fpl = FPL(session)
        self.username = username
        self.password = password
        self.logged_in = False

    async def login_if_needed(self):
        if (self.username and self.password) and (not self.logged_in):
            await self.fpl.login(self.username, self.password)
            self.logged_in = True

    async def get_league_entries(self, league_id: int):
        """Fetch league info including all the entry IDs in the league."""
        await self.login_if_needed()
        league = await self.fpl.get_league(league_id)
        # Depending on version, league.standings.results, etc.
        # For simplicity, assume:
        return league["standings"]["results"]

    async def get_entry_history(self, entry_id: int):
        await self.login_if_needed()
        hist = await self.fpl.get_entry_history(entry_id)
        return hist  # you'll inspect this dict

    async def get_entry_score_for_gw(self, entry_id: int, gw: int) -> int:
        """Get that entry’s points in given GW (if exists)."""
        hist = await self.get_entry_history(entry_id)
        # The structure might have a “past” list of dicts having event, points etc.
        for ev in hist.get("past", []):
            if ev.get("event") == gw:
                return ev.get("points", 0)
        # Not found => maybe future or no data
        return 0
