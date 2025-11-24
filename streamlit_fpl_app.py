import streamlit as st
import pandas as pd
import plotly.express as px
from io import StringIO

st.set_page_config(page_title="FPL Monthly Winners (Admin Months)", layout="wide")

# -----------------------------
# ADMIN-DEFINED CUSTOM MONTHS
# -----------------------------
CUSTOM_MONTHS = {
    "Month 1": [1, 4],
    "Month 2": [5, 8],
    "Month 3": [9, 12],
    "Month 4": [13, 16],
    "Month 5": [17, 19],
}

# -----------------------------
# Helpers: Normalize & compute
# -----------------------------
def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure required columns exist and normalize common variants.
    Required (after normalization):
      - entry_id
      - player_name
      - team_name
      - gameweek
      - event_points
      - total_points
      - transfer_cost  (the column you confirmed)
    """
    col_map = {}
    for c in df.columns:
        lc = c.strip().lower()
        if lc in ("entryid","entry_id","entry id","entry"):
            col_map[c] = "entry_id"
        elif lc in ("manager","player","player_name","player name","manager_name"):
            col_map[c] = "player_name"
        elif lc in ("team","team_name","entry_name","team name"):
            col_map[c] = "team_name"
        elif lc in ("gameweek","gw","event","game week"):
            col_map[c] = "gameweek"
        elif lc in ("points","event_points","pts","event points"):
            col_map[c] = "event_points"
        elif lc in ("total","total_points","total points"):
            col_map[c] = "total_points"
        elif lc in ("transfer_cost","event_transfers_cost","transfers_cost","transfer cost","hits"):
            # prefer the explicit transfer_cost name you provided
            col_map[c] = "transfer_cost"

    df = df.rename(columns=col_map)
    # Check required columns
    required = ["entry_id","player_name","team_name","gameweek","event_points","total_points","transfer_cost"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in CSV after normalization: {missing}. "
                         "Make sure your CSV has columns for gameweek, event_points, total_points and transfer_cost.")
    # types
    df["gameweek"] = pd.to_numeric(df["gameweek"], errors="coerce")
    df = df.dropna(subset=["gameweek"])
    df["gameweek"] = df["gameweek"].astype(int)
    df["event_points"] = pd.to_numeric(df["event_points"], errors="coerce").fillna(0).astype(int)
    df["total_points"] = pd.to_numeric(df["total_points"], errors="coerce").fillna(0).astype(int)
    df["transfer_cost"] = pd.to_numeric(df["transfer_cost"], errors="coerce").fillna(0).astype(int)
    # compute net points for the GW: event_points - transfer_cost
    df["net_points"] = df["event_points"] - df["transfer_cost"]
    return df

def compute_monthly_and_overall(df: pd.DataFrame, months_map: dict):
    """
    Returns:
      - month_tables: list of tuples (month_label, month_df) where month_df has entry_id, player_name, team_name, month_gross, month_transfer_cost, month_net, month_rank
      - combined_df: wide table with each month as a column (month_net) plus totals and overall ranks
      - pivot & cumulative (for charts)
    """
    # Pivot per GW for plotting if needed
    pivot_gross = df.pivot_table(index=["entry_id","player_name","team_name"], columns="gameweek", values="event_points", aggfunc="sum", fill_value=0)
    pivot_net = df.pivot_table(index=["entry_id","player_name","team_name"], columns="gameweek", values="net_points", aggfunc="sum", fill_value=0)
    # cumulative net across GWs
    cumulative_net = pivot_net.cumsum(axis=1)

    month_tables = []
    combined_series = []

    for label, (start, end) in months_map.items():
        # subset rows in those GWs
        subset = df[(df["gameweek"] >= int(start)) & (df["gameweek"] <= int(end))]
        # compute sums per manager
        grouped = subset.groupby(["entry_id","player_name","team_name"]).agg(
            month_gross = ("event_points", "sum"),
            month_transfer_cost = ("transfer_cost", "sum"),
            month_net = ("net_points", "sum"),
        ).reset_index()
        if grouped.empty:
            # ensure every manager appears with 0s
            # use list of unique managers from full df
            managers = df[["entry_id","player_name","team_name"]].drop_duplicates()
            grouped = managers.merge(grouped, on=["entry_id","player_name","team_name"], how="left").fillna({"month_gross":0,"month_transfer_cost":0,"month_net":0})
            grouped["month_gross"] = grouped["month_gross"].astype(int)
            grouped["month_transfer_cost"] = grouped["month_transfer_cost"].astype(int)
            grouped["month_net"] = grouped["month_net"].astype(int)

        # rank by month_net (dense)
        grouped["month_rank"] = grouped["month_net"].rank(method="dense", ascending=False).astype(int)
        grouped = grouped.sort_values(["month_rank","month_net"], ascending=[True, False]).reset_index(drop=True)

        month_tables.append((label, grouped))
        # for combined wide table, keep month_net per entry_id
        combined_series.append((label, grouped.set_index("entry_id")["month_net"]))

    # combined wide
    if combined_series:
        combined_df = pd.concat([s for (_,s) in combined_series], axis=1).fillna(0).reset_index()
        combined_df.columns = ["entry_id"] + [label for (label,_) in combined_series]
        # attach manager names (from df)
        managers = df[["entry_id","player_name","team_name"]].drop_duplicates()
        combined_df = combined_df.merge(managers, on="entry_id", how="left")
        # reorder
        cols = ["entry_id","player_name","team_name"] + [label for (label,_) in combined_series]
        combined_df = combined_df[cols]
        # totals and overall rank (by net across months)
        month_cols = [label for (label,_) in combined_series]
        combined_df["total_net_across_months"] = combined_df[month_cols].sum(axis=1)
        combined_df["overall_rank"] = combined_df["total_net_across_months"].rank(method="dense", ascending=False).astype(int)
        combined_df = combined_df.sort_values(["overall_rank","total_net_across_months"], ascending=[True, False]).reset_index(drop=True)
    else:
        combined_df = pd.DataFrame()

    return {
        "month_tables": month_tables,
        "combined": combined_df,
        "pivot_gross": pivot_gross,
        "pivot_net": pivot_net,
        "cumulative_net": cumulative_net
    }

# -----------------------------
# Streamlit UI
# -----------------------------
st.title("FPL Monthly Winners — Admin Months (Net Score)")
st.markdown("Upload the CSV produced by your extractor (one row per manager per gameweek). Months are fixed in the code by the admin.")

col1, col2 = st.columns([3,1])

with col1:
    uploaded = st.file_uploader("Upload league CSV (required)", type=["csv"])
    st.caption("CSV must include columns: gameweek, event_points, total_points, transfer_cost (case-insensitive).")

with col2:
    show_charts = st.checkbox("Show cumulative charts (top N)", value=True)
    top_n = st.number_input("Top N managers for charts", min_value=3, max_value=200, value=8, step=1)

if uploaded is not None:
    try:
        content = uploaded.getvalue().decode("utf-8")
        df = pd.read_csv(StringIO(content))
        df = normalize_df(df)
        st.success("CSV parsed and normalized successfully.")
    except Exception as e:
        st.error(f"Failed to parse CSV: {e}")
        st.stop()

    # compute
    computed = compute_monthly_and_overall(df, CUSTOM_MONTHS)
    month_tables = computed["month_tables"]
    combined = computed["combined"]
    cumulative_net = computed["cumulative_net"]

    # show per-month leaderboards
    st.header("Monthly Leaderboards (based on NET points)")
    # create tabs: one per month + Combined
    month_labels = [m[0] for m in month_tables]
    tabs = st.tabs(month_labels + ["Combined"])

    for i, (label, table) in enumerate(month_tables):
        with tabs[i]:
            st.subheader(f"{label} — GW {CUSTOM_MONTHS[label][0]} to {CUSTOM_MONTHS[label][1]}")
            # show top N
            st.write(f"Top {top_n}")
            st.dataframe(table[["month_rank","player_name","team_name","month_net","month_gross","month_transfer_cost"]].head(top_n).rename(
                columns={
                    "month_net":"Net Points",
                    "month_gross":"Gross Points",
                    "month_transfer_cost":"Transfer Cost",
                    "month_rank":"Rank",
                    "player_name":"Manager",
                    "team_name":"Team"
                }
            ))

            # winner highlight
            if not table.empty:
                winner = table.iloc[0]
                st.markdown(f"**Winner:** {winner['player_name']} ({winner['team_name']}) — **Net {int(winner['month_net'])} pts**")
            else:
                st.info("No data for this month.")

    # Combined tab
    with tabs[-1]:
        st.subheader("Combined months table (Net points per custom month)")
        if combined.empty:
            st.info("Combined table is empty (no months computed).")
        else:
            # show top_n rows
            st.dataframe(combined.head(200))
            # CSV download
            csv_bytes = combined.to_csv(index=False).encode("utf-8")
            st.download_button("Download combined CSV", csv_bytes, file_name="combined_months_net.csv", mime="text/csv")

    # overall summary
    st.header("Overall Summary & Analytics")
    # winners table
    winners = []
    for label, table in month_tables:
        if not table.empty:
            top = table.sort_values("month_net", ascending=False).iloc[0]
            winners.append({
                "month": label,
                "winner": top["player_name"],
                "team": top["team_name"],
                "net_points": int(top["month_net"])
            })
    if winners:
        st.subheader("Winners by Month")
        st.table(pd.DataFrame(winners))

    # top movers & stats
    st.subheader("Top Analytics")
    # top average net per month (mean)
    if not combined.empty:
        combined["avg_net_per_month"] = combined[[c for c in combined.columns if c.startswith("Month ")]] .mean(axis=1)
        top_avg = combined.sort_values("avg_net_per_month", ascending=False).head(5)[["player_name","team_name","avg_net_per_month"]]
        st.write("Top average net points per month (top 5):")
        st.table(top_avg)
    else:
        st.info("No combined data to produce analytics.")

    # charts
    if show_charts and not cumulative_net.empty:
        st.header("Cumulative Net Points (by GW) — Top managers")
        # pick top N by final total net
        last_gw = cumulative_net.columns[-1] if len(cumulative_net.columns)>0 else None
        if last_gw is not None:
            totals = cumulative_net[last_gw].sort_values(ascending=False).head(top_n)
            top_index = totals.index.tolist()  # list of tuples (entry_id, player_name, team_name)
            # build long dataframe for plotly
            cum_df = cumulative_net.reset_index()
            # create manager label column
            cum_df["manager_label"] = cum_df["player_name"].astype(str) + " — " + cum_df["team_name"].astype(str)
            # keep only top managers
            cum_df = cum_df[cum_df["entry_id"].isin([i[0] for i in top_index])]
            long = cum_df.melt(id_vars=["entry_id","player_name","team_name","manager_label"], var_name="gameweek", value_name="cumulative_net")
            long["gameweek"] = long["gameweek"].astype(int)
            fig = px.line(long, x="gameweek", y="cumulative_net", color="manager_label", markers=True,
                          labels={"gameweek":"Gameweek","cumulative_net":"Cumulative Net Points"},
                          title="Cumulative Net Points by Manager")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough GW columns for plotting.")

    st.success("Processing complete.")

else:
    st.info("Upload a CSV (one row per manager per gameweek). App will use admin-defined months only.")
