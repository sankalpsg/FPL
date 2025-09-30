import axios from "axios";

const BASE = "https://fantasy.premierleague.com/api";

async function fetchLeagueStandingsPaged(leagueId) {
  // Classic league standings pages through `page_standings` param
  // https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/?page_standings=2
  const headers = { headers: { "User-Agent": "Mozilla/5.0" } };
  let page = 1;
  const results = [];
  while (true) {
    const url = `${BASE}/leagues-classic/${leagueId}/standings/?page_standings=${page}`;
    const { data } = await axios.get(url, headers);
    const pageResults = data?.standings?.results || [];
    results.push(...pageResults);
    const hasNext = Boolean(data?.standings?.has_next);
    if (!hasNext) break;
    page += 1;
  }
  return results;
}

async function fetchEntryEventPicks(entryId, eventId) {
  const url = `${BASE}/entry/${entryId}/event/${eventId}/picks/`;
  const { data } = await axios.get(url, { headers: { "User-Agent": "Mozilla/5.0" } });
  return data;
}

async function fetchBootstrap() {
  const url = `${BASE}/bootstrap-static/`;
  const { data } = await axios.get(url, { headers: { "User-Agent": "Mozilla/5.0" } });
  return data;
}

function groupByMonths(scoresByGw, months) {
  const result = [];
  for (const month of months) {
    const monthScores = {};
    for (const gw of month.gameweeks) {
      const gwScores = scoresByGw.get(gw) || new Map();
      for (const [entryId, points] of gwScores.entries()) {
        monthScores[entryId] = (monthScores[entryId] || 0) + points;
      }
    }
    result.push({ name: month.name, totals: monthScores });
  }
  return result;
}

export async function getLeagueMonthlyScores(leagueId, months) {
  // 1) Read league standings to collect entries (managers), paginate
  const entries = await fetchLeagueStandingsPaged(leagueId);
  const entryIds = entries.map(e => e.entry);

  // 2) Need current events list to know available gameweeks
  const bootstrap = await fetchBootstrap();
  const currentEvents = bootstrap?.events || [];
  const allGwIds = new Set(currentEvents.map(e => e.id));

  // 3) For each custom month, for each gw, fetch live score per entry
  // We can derive weekly points by comparing total points before/after a gw, but
  // the picks endpoint returns entry history; simpler is to call entry history
  // endpoint to get event-specific points. Use /entry/{id}/history/
  const scoresByGw = new Map(); // gw -> Map(entryId -> points)

  async function fetchEntryHistory(entryId) {
    const url = `${BASE}/entry/${entryId}/history/`;
    const { data } = await axios.get(url, { headers: { "User-Agent": "Mozilla/5.0" } });
    return data;
  }

  // Fetch histories in batches to avoid rate limits
  const concurrency = 10;
  let index = 0;
  const workers = Array.from({ length: concurrency }).map(async () => {
    while (index < entryIds.length) {
      const myIndex = index++;
      const entryId = entryIds[myIndex];
      try {
        const history = await fetchEntryHistory(entryId);
        const current = history?.current || [];
        for (const evt of current) {
          const gw = evt.event;
          if (!allGwIds.has(gw)) continue;
          const points = evt.points;
          if (!scoresByGw.has(gw)) scoresByGw.set(gw, new Map());
          scoresByGw.get(gw).set(entryId, points);
        }
      } catch (e) {
        // ignore this entry on failure
      }
    }
  });

  await Promise.all(workers);

  // 4) Aggregate per custom month
  const monthsData = groupByMonths(scoresByGw, months);

  // 5) Convert to array rows per manager for frontend
  const entryIdToName = new Map(entries.map(e => [e.entry, e.entry_name]));
  const managers = entries.map(e => ({ entryId: e.entry, name: e.player_name, teamName: e.entry_name }));

  const monthNames = months.map(m => m.name);
  const rows = managers.map(m => {
    const monthly = {};
    for (const mth of monthsData) {
      monthly[mth.name] = mth.totals[m.entryId] || 0;
    }
    const total = monthNames.reduce((acc, n) => acc + (monthly[n] || 0), 0);
    return { entryId: m.entryId, name: m.name, monthly, total };
  });

  // Sort by total desc
  rows.sort((a, b) => b.total - a.total);

  return { months: monthNames, rows };
}
