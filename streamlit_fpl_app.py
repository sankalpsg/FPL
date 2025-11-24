import streamlit as st
import pandas as pd
import requests
import plotly.express as px

st.set_page_config(page_title="FPL Monthly Winners (API)", layout="wide")

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

LEAGUE_ID = 665400

st.title("FPL Monthly Winners — Direct API")
st.markdown("Data is fetched live from FPL APIs. Months are admin-defined.")

# -----------------------------
# Fetch League Entries
# -----------------------------
@st.cache_data(show_spinner=True)
def fetch_league_entries(league_id):
    url = f"https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/"
    r = requests.get(url)
    data = r.json()
    entries = []
    for e in data['standings']['results']:
        entries.append({
            'entry_id': e['entry'],
            'player_name': e['player_name'],
            'team_name': e['entry_name']
        })
    return pd.DataFrame(entries)

# -----------------------------
# Fetch Manager History
# -----------------------------
@st.cache_data(show_spinner=True)
def fetch_manager_history(entry_id):
    url = f"https://fantasy.premierleague.com/api/entry/{entry_id}/history/"
    r = requests.get(url)
    data = r.json()
    rows = []
    for gw in data['current']:
        rows.append({
            'entry_id': entry_id,
            'gameweek': gw['event'],
            'event_points': gw['points'],
            'transfer_cost': gw['event_transfers_cost'],
            'total_points': gw['total_points'],
            'net_points': gw['points'] - gw['event_transfers_cost']
        })
    return pd.DataFrame(rows)

# -----------------------------
# Main Data Fetch
# -----------------------------
st.info("Fetching league data from FPL API...")
league_df = fetch_league_entries(LEAGUE_ID)
all_gw_data = []

for idx, row in league_df.iterrows():
    gw_data = fetch_manager_history(row['entry_id'])
    gw_data = gw_data.merge(row.to_frame().T, on='entry_id')
    all_gw_data.append(gw_data)

full_df = pd.concat(all_gw_data, ignore_index=True)

st.success("All data fetched!")

# -----------------------------
# Monthly Aggregation
# -----------------------------
month_tables = []
for month_name, (start_gw, end_gw) in CUSTOM_MONTHS.items():
    month_df = full_df[(full_df['gameweek'] >= start_gw) & (full_df['gameweek'] <= end_gw)]
    summary = (
        month_df.groupby(['entry_id','player_name','team_name'])
        .agg(month_gross=('event_points','sum'),
             month_transfer_cost=('transfer_cost','sum'),
             month_net=('net_points','sum'))
        .reset_index()
    )
    summary['month_rank'] = summary['month_net'].rank(method='dense', ascending=False).astype(int)
    summary = summary.sort_values(['month_rank','month_net'], ascending=[True, False]).reset_index(drop=True)
    month_tables.append((month_name, summary))

# -----------------------------
# Combined Overall Table
# -----------------------------
combined_series = []
for month_name, df_month in month_tables:
    combined_series.append(df_month.set_index('entry_id')['month_net'].rename(month_name))

combined_df = pd.concat(combined_series, axis=1).fillna(0)
managers = full_df[['entry_id','player_name','team_name']].drop_duplicates().set_index('entry_id')
combined_df = combined_df.merge(managers, left_index=True, right_index=True)
combined_df['total_net_across_months'] = combined_df[[m[0] for m in month_tables]].sum(axis=1)
combined_df['overall_rank'] = combined_df['total_net_across_months'].rank(method='dense', ascending=False).astype(int)
combined_df = combined_df.sort_values(['overall_rank','total_net_across_months'], ascending=[True, False]).reset_index()

# -----------------------------
# Streamlit UI
# -----------------------------
st.header("Monthly Leaderboards")
tabs = st.tabs([m[0] for m in month_tables] + ['Combined', 'Net Points per GW'])

for i, (month_name, df_month) in enumerate(month_tables):
    with tabs[i]:
        st.subheader(f"{month_name} — GW {CUSTOM_MONTHS[month_name][0]} to {CUSTOM_MONTHS[month_name][1]}")
        st.dataframe(df_month[['month_rank','player_name','team_name','month_net','month_gross','month_transfer_cost']].rename(
            columns={'month_rank':'Rank','player_name':'Manager','team_name':'Team','month_net':'Net Points',
                     'month_gross':'Gross Points','month_transfer_cost':'Transfer Cost'}))

with tabs[-2]:
    st.subheader("Combined Months Leaderboard")
    st.dataframe(combined_df)
    st.download_button("Download Combined CSV", combined_df.to_csv(index=False).encode('utf-8'), file_name='combined_fpl_net.csv')

with tabs[-1]:
    st.subheader("Net Points per Gameweek")
    gw_pivot = full_df.pivot_table(index=['player_name','team_name'], columns='gameweek', values='net_points', fill_value=0)
    st.dataframe(gw_pivot)
    st.download_button("Download GW Net Points CSV", gw_pivot.reset_index().to_csv(index=False).encode('utf-8'), file_name='net_points_per_gw.csv')

# -----------------------------
# Cumulative Net Points Chart
# -----------------------------
st.header("Cumulative Net Points by GW")
cumulative = full_df.pivot_table(index=['player_name','team_name'], columns='gameweek', values='net_points', aggfunc='sum', fill_value=0)
cumulative = cumulative.cumsum(axis=1)

fig = px.line(cumulative.reset_index().melt(id_vars=['player_name','team_name'], var_name='Gameweek', value_name='Cumulative Net Points'),
              x='Gameweek', y='Cumulative Net Points', color='player_name', hover_data=['team_name'])
st.plotly_chart(fig, use_container_width=True)
