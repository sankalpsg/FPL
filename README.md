# FPL Mini-League Monthly Rankings App

This Streamlit app fetches your mini-league data directly from the Fantasy Premier League API and displays monthly rankings and cumulative net points.


## Deployment on Streamlit Cloud


1. Fork or clone this repo to your GitHub account.
2. Go to [https://share.streamlit.io/](https://share.streamlit.io/).
3. Click **New App**, select your repo and branch, and set the file path to `streamlit_fpl_api_app.py`.
4. Click **Deploy**.
5. Share the generated URL with your league members.


## Features
- Monthly net points and rankings (admin-defined months)
- Overall leaderboard
- Cumulative net points chart
- Downloadable CSV for combined months


## Admin Instructions
- To change months, edit `CUSTOM_MONTHS` in `streamlit_fpl_api_app.py`.
- The league ID is set in `LEAGUE_ID`.
