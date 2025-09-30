import React, { useMemo, useState } from "react";

function defaultMonths() {
  return [
    { name: "Aug", gameweeks: [1, 2, 3] },
    { name: "Sep", gameweeks: [4, 5, 6] },
  ];
}

export default function App() {
  const [leagueId, setLeagueId] = useState(123);
  const [monthsJson, setMonthsJson] = useState(
    JSON.stringify(defaultMonths(), null, 2)
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [data, setData] = useState(null);

  const months = useMemo(() => {
    try {
      const parsed = JSON.parse(monthsJson);
      if (!Array.isArray(parsed)) return [];
      return parsed;
    } catch {
      return [];
    }
  }, [monthsJson]);

  async function fetchMonthly() {
    setLoading(true);
    setError("");
    setData(null);
    try {
      const res = await fetch("/api/league-monthly", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ leagueId, months }),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "Request failed");
      }
      const json = await res.json();
      setData(json);
    } catch (e) {
      setError(e?.message || "Error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      style={{
        maxWidth: 960,
        margin: "20px auto",
        fontFamily: "Inter, system-ui, Arial",
      }}
    >
      <h1>FPL Monthly Scores</h1>
      <div
        style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}
      >
        <label>
          <div>League ID</div>
          <input
            type="number"
            value={leagueId}
            onChange={(e) => setLeagueId(Number(e.target.value))}
            style={{ width: "100%", padding: 8 }}
          />
        </label>
        <label>
          <div>Custom Months (JSON)</div>
          <textarea
            value={monthsJson}
            onChange={(e) => setMonthsJson(e.target.value)}
            rows={8}
            style={{ width: "100%", fontFamily: "monospace", padding: 8 }}
          />
        </label>
      </div>
      <div style={{ marginTop: 12 }}>
        <button onClick={fetchMonthly} disabled={loading || months.length === 0}>
          Compute
        </button>
      </div>
      {loading && <p>Loading… This may take ~10-30s for large leagues.</p>}
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      {data && <Results data={data} />}
    </div>
  );
}

function Results({ data }) {
  const months = data.months;
  return (
    <div style={{ marginTop: 24 }}>
      <h2>Results</h2>
      <div style={{ overflowX: "auto" }}>
        <table
          border="1"
          cellPadding="6"
          style={{ borderCollapse: "collapse", minWidth: 600 }}
        >
          <thead>
            <tr>
              <th>Manager</th>
              {months.map((m) => (
                <th key={m}>{m}</th>
              ))}
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            {data.rows.map((r) => (
              <tr key={r.entryId}>
                <td>{r.name}</td>
                {months.map((m) => (
                  <td key={m + r.entryId}>{r.monthly[m] || 0}</td>
                ))}
                <td>
                  <strong>{r.total}</strong>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
