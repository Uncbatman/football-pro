import streamlit as st
from pyairtable import Api

# Accessing secrets securely
AIRTABLE_API_KEY = st.secrets["AIRTABLE_API_KEY"]
AIRTABLE_BASE_ID = st.secrets["AIRTABLE_BASE_ID"]
HF_TOKEN = st.secrets["HF_TOKEN"]

# Initialize Airtable with secrets
api = Api(AIRTABLE_API_KEY)
table = api.table(AIRTABLE_BASE_ID, 'Table Name')

# Load the trained Model
with open('football_model.pkl', 'rb') as f:
    model = pickle.load(f)

# --- Helper: Feature Extraction ---
def get_team_stats(team_name, team_records, stats_records):
    """
    Fetches stats from Airtable. 
    If team is missing or has no history, returns League Averages (1.3 scored, 1.2 conceded).
    """
    # Standard EPL averages as a fallback safety net
    LEAGUE_AVG_SCORED = 1.35 
    LEAGUE_AVG_CONCEDED = 1.35

    try:
        # 1. Find the Airtable ID for the team name
        # We use .lower() to handle spelling/case sensitivity issues
        team_id = next(
            (r['id'] for r in team_records 
             if r['fields'].get('Team Name', '').lower() == team_name.lower()), 
            None
        )
        
        if not team_id:
            return LEAGUE_AVG_SCORED, LEAGUE_AVG_CONCEDED
        
        relevant_matches = []
        for r in stats_records:
            f = r['fields']
            # Home matches
            if team_id in f.get('Home Team', []):
                relevant_matches.append({
                    'scored': f.get('Home Goals', 0), 
                    'conceded': f.get('Away Goals', 0)
                })
            # Away matches
            elif team_id in f.get('Away Team', []):
                relevant_matches.append({
                    'scored': f.get('Away Goals', 0), 
                    'conceded': f.get('Home Goals', 0)
                })
        
        # 2. Check if we have enough data (at least 2 matches)
        if len(relevant_matches) < 2:
            return LEAGUE_AVG_SCORED, LEAGUE_AVG_CONCEDED
            
        avg_scored = sum(m['scored'] for m in relevant_matches) / len(relevant_matches)
        avg_conceded = sum(m['conceded'] for m in relevant_matches) / len(relevant_matches)
        
        return avg_scored, avg_conceded

    except Exception as e:
        # If anything else goes wrong, don't crash the app
        st.sidebar.warning(f"Using default stats for {team_name} due to data gap.")
        return LEAGUE_AVG_SCORED, LEAGUE_AVG_CONCEDED

# --- Market Odds ---
def get_mock_market_odds():
    """Get mock market odds (Decimal: [Home, Draw, Away]).
    
    In production, connect to Odds API.
    """
    return [2.10, 3.40, 3.80]


# --- App UI ---
st.set_page_config(page_title="AI Football Odds Tool", layout="centered")
st.title("⚽ AI-Powered Match Predictor")

# Fetch data from Airtable
team_records = teams_table.all()
stats_records = stats_table.all()
team_names = sorted(
    [r["fields"]["Team Name"] for r in team_records if "Team Name" in r["fields"]]
)

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
    input_data = pd.DataFrame(
        [[home_avg_scored, away_avg_conceded]], columns=["home_goals", "away_goals"]
    )
    probs = model.predict_proba(input_data)[0]

    # Display predictions
    st.divider()
    st.subheader(f"{home_team} vs {away_team}")

    p1, p2, p3 = st.columns(3)
    p1.metric("Home Win", f"{probs[1] * 100:.1f}%")
    p2.metric("Draw", f"{probs[0] * 100:.1f}%")
    p3.metric("Away Win", f"{probs[2] * 100:.1f}%")

    # Market comparison and value detection
    st.divider()
    st.subheader("📊 Market Comparison")

    market_odds = get_mock_market_odds()
    implied_probs = [1 / market_odds[0], 1 / market_odds[1], 1 / market_odds[2]]

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

    # AI insight
    st.info(
        f"**AI Insight:** {home_team} averages {home_avg_scored:.2f} goals/match, "
        f"while {away_team} concedes {away_avg_conceded:.2f}. "
        f"The model weights these against historical league trends."
    )

    # Verdict
    st.divider()
    outcomes = {
        "Home Win": probs[1],
        "Draw": probs[0],
        "Away Win": probs[2],
    }
    most_likely = max(outcomes, key=outcomes.get)

    if most_likely == "Home Win":
        verdict_text = f"🏆 **Most Likely Outcome: {home_team} to Win**"
    elif most_likely == "Away Win":
        verdict_text = f"🏆 **Most Likely Outcome: {away_team} to Win**"
    else:
        verdict_text = "🤝 **Most Likely Outcome: A Draw**"

    st.subheader(verdict_text)


# --- Bulk Match Analyzer ---
st.divider()
st.title("🚀 Bulk Match Analyzer")
raw_input = st.text_area("Paste match list here (Team names and odds):", height=200)

if st.button("Analyze All Matches"):
    with st.spinner("AI is organizing the data..."):
        matches = parse_bulk_odds(raw_input)

        results_data = []
        for match in matches:
            # Fetch team stats from Airtable
            h_scored, _ = get_team_stats(match.home_team, team_records, stats_records)
            _, a_conceded = get_team_stats(match.away_team, team_records, stats_records)

            # Run prediction
            input_df = pd.DataFrame(
                [[h_scored, a_conceded]], columns=["home_goals", "away_goals"]
            )
            probs = model.predict_proba(input_df)[0]

            # Check for value (implied_prob = 1 / odds)
            value_home = "Value" if probs[1] > (1 / match.home_odds) else ""

            results_data.append(
                {
                    "Match": f"{match.home_team} vs {match.away_team}",
                    "AI Home Win %": f"{probs[1] * 100:.1f}%",
                    "Market Odds": match.home_odds,
                    "Advice": value_home,
                }
            )

        # Display results
        st.table(pd.DataFrame(results_data))


# --- Disclaimer ---
st.markdown("---")
st.caption(
    """
    **Disclaimer:** This tool is for informational and entertainment purposes only.
    AI predictions are based on historical data and do not guarantee future results.
    Betting involves risk. Please gamble responsibly. 18+
    """
)