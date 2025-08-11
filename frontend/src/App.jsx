import { useEffect, useMemo, useState } from "react";

// Use backend URL from .env (frontend/.env -> VITE_API_URL=http://localhost:8000)
const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export default function App() {
  const seasons = useMemo(
    () => Array.from({ length: 30 }, (_, i) => 1995 + i).reverse(),
    []
  );

  // Defaults: Nuggets 2024–25
  const [season, setSeason] = useState(2024);
  const [teamId, setTeamId] = useState(1610612743); // Denver Nuggets ID
  const [teamName, setTeamName] = useState("Nuggets"); // stored name in your DB
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  async function fetchGames() {
    setLoading(true);
    setErr("");
    try {
      const params = new URLSearchParams();
      if (teamId) params.set("team_id", String(teamId));
      else if (teamName) params.set("team_name", teamName);
      if (season) params.set("season", String(season));
      params.set("limit", "200");
      const data = await getJSON(`${API}/games?${params.toString()}`);
      setGames(data);
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchGames();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // load once

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="sticky top-0 bg-white/70 backdrop-blur border-b p-4">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row gap-3 items-center justify-between">
          <h1 className="text-2xl font-semibold">Outlier‑Style NBA (Local)</h1>
          <div className="flex gap-2 items-center">
            <select
              value={season}
              onChange={(e) => setSeason(Number(e.target.value))}
              className="border rounded-xl px-3 py-2"
            >
              {seasons.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            <input
              className="border rounded-xl px-3 py-2 w-40"
              placeholder="Team ID (e.g., 1610612743)"
              value={teamId ?? ""}
              onChange={(e) =>
                setTeamId(e.target.value ? Number(e.target.value) : undefined)
              }
            />
            <input
              className="border rounded-xl px-3 py-2 w-40"
              placeholder="Team Name (e.g., Nuggets)"
              value={teamName}
              onChange={(e) => setTeamName(e.target.value)}
            />
            <button
              onClick={fetchGames}
              className="px-4 py-2 rounded-xl bg-black text-white"
            >
              Fetch Games
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto p-4 space-y-4">
        {err && <div className="p-3 bg-red-100 text-red-700 rounded">{err}</div>}

        <section className="space-y-2">
          <div className="font-medium">Games</div>
          {loading ? (
            <div>Loading…</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left border-b">
                    <th className="py-2 pr-4">Date</th>
                    <th className="py-2 pr-4">Home</th>
                    <th className="py-2 pr-4">Away</th>
                    <th className="py-2 pr-4">Score</th>
                    <th className="py-2 pr-4">Type</th>
                  </tr>
                </thead>
                <tbody>
                  {games.map((g) => (
                    <tr key={g.game_id} className="border-b hover:bg-white">
                      <td className="py-2 pr-4">{g.game_date}</td>
                      <td className="py-2 pr-4">{g.home_team_name}</td>
                      <td className="py-2 pr-4">{g.away_team_name}</td>
                      <td className="py-2 pr-4">
                        {g.home_score} – {g.away_score}
                      </td>
                      <td className="py-2 pr-4">{g.game_type}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {games.length === 0 && (
                <div className="text-gray-500 mt-2">No games found.</div>
              )}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}