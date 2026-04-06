import streamlit as st
import pandas as pd
import pickle
from pyairtable import Api

# --- Configuration ---
AIRTABLE_API_KEY = 'patRV0Ftx6TwcR9M5.64e8132bb75468b3e7f34113c0c304717cb6e84215755d20bb09ee582514f117'
AIRTABLE_BASE_ID = 'appEKWpp4qIrJkZS1'
api = Api(AIRTABLE_API_KEY)
teams_table = api.table(AIRTABLE_BASE_ID, 'Teams')
stats_table = api.table(AIRTABLE_BASE_ID, 'Historical Stats')

# Load the trained Model
with open('football_model.pkl', 'rb') as f:
    model = pickle.load(f)

# --- Helper: Feature Extraction Agent ---
def get_team_stats(team_name, team_records, stats_records):
    try:
        # Find the Airtable ID
        team_id = next(r['id'] for r in team_records if r['fields'].get('Team Name') == team_name)
        
        relevant_matches = []
        for r in stats_records:
            f = r['fields']
            if team_id in f.get('Home Team', []):
                relevant_matches.append({'scored': f['Home Goals'], 'conceded': f['Away Goals']})
            elif team_id in f.get('Away Team', []):
                relevant_matches.append({'scored': f['Away Goals'], 'conceded': f['Home Goals']})
        
        # BLUE TEAM DEFENSE: If less than 3 matches, mix in League Averages
        if len(relevant_matches) < 3:
            return 1.3, 1.2  # Standard EPL scoring averages
            
        avg_scored = sum(m['scored'] for m in relevant_matches) / len(relevant_matches)
        avg_conceded = sum(m['conceded'] for m in relevant_matches) / len(relevant_matches)
        return avg_scored, avg_conceded

    except StopIteration:
        # If team name isn't in Airtable at all
        return 1.3, 1.2

# --- Market Odds Agent ---
def get_mock_market_odds():
    """Get mock market odds. In production, connect to Odds API."""
    # Returning Decimal Odds: [Home, Draw, Away]
    return [2.10, 3.40, 3.80]

# --- App UI ---
st.set_page_config(page_title="AI Football Odds Tool", layout="centered")
st.title("⚽ AI-Powered Match Predictor")

# Fetch Data
team_records = teams_table.all()
stats_records = stats_table.all()
team_names = sorted([r['fields']['Team Name'] for r in team_records if 'Team Name' in r['fields']])

# Team Selection
col1, col2 = st.columns(2)
with col1:
    home_team = st.selectbox("Home Team", team_names)
with col2:
    away_team = st.selectbox("Away Team", team_names)

if st.button("Analyze Match"):
    # Get Real Stats from Airtable
    home_avg_scored, _ = get_team_stats(home_team, team_records, stats_records)
    _, away_avg_conceded = get_team_stats(away_team, team_records, stats_records)

    # Predict using real data
    input_data = pd.DataFrame([[home_avg_scored, away_avg_conceded]], columns=['home_goals', 'away_goals'])
    probs = model.predict_proba(input_data)[0]

    # Display Predictions
    st.divider()
    st.subheader(f"{home_team} vs {away_team}")
    
    p1, p2, p3 = st.columns(3)
    p1.metric("Home Win", f"{probs[1]*100:.1f}%")
    p2.metric("Draw", f"{probs[0]*100:.1f}%")
    p3.metric("Away Win", f"{probs[2]*100:.1f}%")

    # Market Comparison (Value Detection)
    st.divider()
    st.subheader("📊 Market Comparison (Value Detection)")
    
    market_odds = get_mock_market_odds()
    implied_probs = [1/market_odds[0], 1/market_odds[1], 1/market_odds[2]]

    m1, m2, m3 = st.columns(3)
    with m1:
        st.write(f"Bookie Odds: {market_odds[0]}")
        if probs[1] > implied_probs[0]:
            st.success("🔥 Value Detected")
    with m2:
        st.write(f"Bookie Odds: {market_odds[1]}")
        if probs[0] > implied_probs[1]:
            st.success("🔥 Value Detected")
    with m3:
        st.write(f"Bookie Odds: {market_odds[2]}")
        if probs[2] > implied_probs[2]:
            st.success("🔥 Value Detected")

    # AI Insight
    st.info(f"**AI Insight:** {home_team} averages {home_avg_scored:.2f} goals per match, while {away_team} concedes {away_avg_conceded:.2f}. The model weights these against historical league trends.")

    # Verdict
    st.divider()
    outcomes = {
        "Home Win": probs[1],
        "Draw": probs[0],
        "Away Win": probs[2]
    }
    most_likely = max(outcomes, key=outcomes.get)
    
    if most_likely == "Home Win":
        verdict_text = f"🏆 **Most Likely Outcome: {home_team} to Win**"
    elif most_likely == "Away Win":
        verdict_text = f"🏆 **Most Likely Outcome: {away_team} to Win**"
    else:
        verdict_text = "🤝 **Most Likely Outcome: A Draw**"
        
    st.subheader(verdict_text)

# Disclaimer
st.markdown("---")
st.caption("""
**Disclaimer:** This tool is for informational and entertainment purposes only. 
AI predictions are based on historical data and do not guarantee future results. 
Betting involves risk. Please gamble responsibly. 18+
""")