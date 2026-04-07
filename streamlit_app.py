import streamlit as st
import pickle
import pandas as pd
import re
from pyairtable import Api
from huggingface_hub import InferenceClient

# ============================================================================
# CONFIGURATION & SECRETS
# ============================================================================

AT_KEY = st.secrets["AIRTABLE_API_KEY"]
AT_BASE = st.secrets["AIRTABLE_BASE_ID"]
HF_TOKEN = st.secrets["HF_TOKEN"]

# Initialize Airtable
api = Api(AT_KEY)
target_table = api.table(AT_BASE, 'Matches')

# Load the trained model
with open('football_model.pkl', 'rb') as f:
    model = pickle.load(f)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


class Match:
    """Parse match data from bulk input."""
    def __init__(self, home_team, away_team, home_odds):
        self.home_team = home_team.strip()
        self.away_team = away_team.strip()
        self.home_odds = float(home_odds.strip()) if home_odds else 1.0


def get_team_stats(team_name, teams_table, stats_records):
    """
    Fetches team stats from Airtable.
    
    If team is missing or has insufficient history, returns League Averages
    (1.35 scored, 1.35 conceded).
    
    Args:
        team_name (str): Name of the team
        teams_table (list): Team records from Airtable
        stats_records (list): Match statistics from Airtable
        
    Returns:
        tuple: (avg_scored, avg_conceded)
    """
    LEAGUE_AVG_SCORED = 1.35
    LEAGUE_AVG_CONCEDED = 1.35

    try:
        # Find the Airtable ID for the team name (case-insensitive)
        team_id = next(
            (r['id'] for r in teams_table 
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
        
        # Require at least 2 matches for reliable average
        if len(relevant_matches) < 2:
            return LEAGUE_AVG_SCORED, LEAGUE_AVG_CONCEDED
            
        avg_scored = sum(m['scored'] for m in relevant_matches) / len(relevant_matches)
        avg_conceded = sum(m['conceded'] for m in relevant_matches) / len(relevant_matches)
        
        return avg_scored, avg_conceded

    except Exception as e:
        st.sidebar.warning(f"Using default stats for {team_name} due to data gap.")
        return LEAGUE_AVG_SCORED, LEAGUE_AVG_CONCEDED


def get_mock_market_odds():
    """
    Get mock market odds in Decimal format.
    
    Returns:
        list: [Home Odds, Draw Odds, Away Odds]
        
    Note:
        In production, connect to Odds API for real-time odds.
    """
    return [2.10, 3.40, 3.80]

import re
import requests

def parse_bulk_odds(raw_text: str):
    if not raw_text.strip():
        return []

    token = st.secrets["HF_TOKEN"]
    
    # 1. NEW ROUTER URL
    api_url = "https://router.huggingface.co/hf-inference/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 2. Use the Chat Completion format (The Router prefers this)
    payload = {
        "model": "meta-llama/Llama-3.2-1B-Instruct",
        "messages": [
            {"role": "system", "content": "Extract football matches. Format: Home vs Away | Odds"},
            {"role": "user", "content": raw_text}
        ],
        "max_tokens": 500,
        "temperature": 0.1
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=10)
        
        if response.status_code != 200:
            st.error(f"HF Router Error {response.status_code}: {response.text}")
            return []

        result = response.json()
        ai_text = result['choices'][0]['message']['content']

        # ... (keep your existing parsing/regex logic here) ...
        parsed_matches = []
        for line in ai_text.strip().split('\n'):
            if " vs " in line.lower():
                try:
                    # Very simple splitting logic
                    parts = line.replace("-", "|").split("|")
                    teams = parts[0]
                    odds = parts[1] if len(parts) > 1 else "1.00"
                    
                    h, a = re.split(r' vs ', teams, flags=re.IGNORECASE)
                    
                    class Match:
                        def __init__(self, h, a, o):
                            self.home_team = h.strip()
                            self.away_team = a.strip()
                            self.odds = o.strip()
                    
                    parsed_matches.append(Match(h, a, odds))
                except:
                    continue
        
        return parsed_matches

    except Exception as e:
        st.error(f"Connection Failed: {e}")
        return []

        parsed_matches = []
        for line in response.strip().split('\n'):
            if " vs " in line.lower():
                try:
                    # Clean up the line
                    line = line.replace("-", "|").replace(":", "|")
                    parts = line.split("|")
                    teams_part = parts[0]
                    odds_part = parts[1] if len(parts) > 1 else "1.00"
                    
                    home, away = re.split(r' vs ', teams_part, flags=re.IGNORECASE)
                    parsed_matches.append(Match(home, away, odds_part))
                except:
                    continue
        
        return parsed_matches
        
    except Exception as e:
        st.error(f"Hugging Face Error: {e}")
        return []


# ============================================================================
# STREAMLIT APP - SINGLE MATCH PREDICTOR
# ============================================================================

st.set_page_config(page_title="AI Football Odds Tool", layout="centered")
st.title("⚽ AI-Powered Match Predictor")

# Fetch data from Airtable
teams_table = target_table.all()
stats_records = target_table.all()
team_names = sorted(
    [r["fields"]["Team Name"] for r in teams_table 
     if "Team Name" in r["fields"]]
)

# --- Team Selection ---
col1, col2 = st.columns(2)
with col1:
    home_team = st.selectbox("Home Team", team_names)
with col2:
    away_team = st.selectbox("Away Team", team_names)

# --- Match Analysis ---
if st.button("Analyze Match"):
    # Get team statistics from Airtable
    home_avg_scored, _ = get_team_stats(home_team, teams_table, stats_records)
    _, away_avg_conceded = get_team_stats(away_team, teams_table, stats_records)

    # Generate predictions
    input_data = pd.DataFrame(
        [[home_avg_scored, away_avg_conceded]], 
        columns=["home_goals", "away_goals"]
    )
    probs = model.predict_proba(input_data)[0]

    # Display prediction probabilities
    st.divider()
    st.subheader(f"{home_team} vs {away_team}")

    p1, p2, p3 = st.columns(3)
    p1.metric("Home Win", f"{probs[1] * 100:.1f}%")
    p2.metric("Draw", f"{probs[0] * 100:.1f}%")
    p3.metric("Away Win", f"{probs[2] * 100:.1f}%")

    # --- Market Comparison & Value Detection ---
    st.divider()
    st.subheader("📊 Market Comparison")

    market_odds = get_mock_market_odds()
    implied_probs = [
        1 / market_odds[0], 
        1 / market_odds[1], 
        1 / market_odds[2]
    ]

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

    # AI insight with team statistics
    st.info(
        f"**AI Insight:** {home_team} averages {home_avg_scored:.2f} goals/match, "
        f"while {away_team} concedes {away_avg_conceded:.2f}. "
        f"The model weighs these against historical league trends."
    )

    # --- Match Verdict ---
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


# ============================================================================
# BULK MATCH ANALYZER
# ============================================================================

st.divider()
st.title("🚀 Bulk Match Analyzer")

raw_input = st.text_area("Paste match list here (Team names and odds):", height=200)

if st.button("Analyze All Matches"):
    with st.spinner("AI is organizing the data..."):
        matches = parse_bulk_odds(raw_input)

        if not matches:
            st.warning("No matches could be parsed.")
        else:
            results_data = []
            
            for match in matches:
                # Fetch team statistics from Airtable
                h_scored, _ = get_team_stats(match.home_team, teams_table, stats_records)
                _, a_conceded = get_team_stats(match.away_team, teams_table, stats_records)

                # Run prediction model
                input_df = pd.DataFrame(
                    [[h_scored, a_conceded]], 
                    columns=["home_goals", "away_goals"]
                )
                probs = model.predict_proba(input_df)[0]

                # Detect value opportunities (AI_prob > implied_prob)
                value_home = "Value" if probs[1] > (1 / match.home_odds) else ""

                results_data.append(
                    {
                        "Match": f"{match.home_team} vs {match.away_team}",
                        "AI Home Win %": f"{probs[1] * 100:.1f}%",
                        "Market Odds": match.home_odds,
                        "Advice": value_home,
                    }
                )

            # Display results in table format
            st.table(pd.DataFrame(results_data))


# ============================================================================
# DISCLAIMER
# ============================================================================

st.markdown("---")
st.caption(
    """
    **Disclaimer:** This tool is for informational and entertainment purposes only.
    AI predictions are based on historical data and do not guarantee future results.
    Betting involves risk. Please gamble responsibly. 18+
    """
)