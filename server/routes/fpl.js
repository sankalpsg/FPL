import { Router } from "express";
import { getLeagueMonthlyScores } from "../services/fplService.js";

const router = Router();

// POST /api/league-monthly
// { leagueId: number, months: Array<{ name: string, gameweeks: number[] }> }
router.post("/league-monthly", async (req, res) => {
  try {
    const { leagueId, months } = req.body;
    if (!leagueId || !Array.isArray(months)) {
      return res.status(400).json({ error: "leagueId and months are required" });
    }
    const data = await getLeagueMonthlyScores(leagueId, months);
    res.json(data);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "Failed to compute monthly scores" });
  }
});

export default router;
