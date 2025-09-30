# FPL Monthly Scores App

Compute monthly scores for a Fantasy Premier League classic league using custom month definitions (groupings of gameweeks).

## Dev Setup

1. Install deps

```bash
npm install
```

2. Start API and Web in dev

```bash
npm start
```

- Web: http://localhost:5173
- API: http://localhost:3001

## Usage

- Enter your classic league ID
- Provide custom months JSON, e.g.

```json
[
  { "name": "Aug", "gameweeks": [1,2,3] },
  { "name": "Sep", "gameweeks": [4,5,6] }
]
```

Click Compute to fetch standings and aggregate per month.

## Notes

- Standings are paginated automatically.
- For each manager, weekly points are taken from `/entry/{id}/history/`.
- Requests are parallelised with a small concurrency to avoid rate limits.
