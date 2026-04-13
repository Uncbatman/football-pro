import streamlit as st
import pandas as pd
import re
import requests
from pyairtable import Api

# Import custom modules
from prediction_engine import PredictionEngine
from value_detection import ValueDetector
from risk_management import KellyCalculator, BankrollManager
from analytics import BayesianUpdater, PostMortemAnalyzer, BrierScoreCalculator

# ============================================================================
# CONFIGURATION & SECRETS
# ============================================================================

AT_KEY = st.secrets["AIRTABLE_API_KEY"]
AT_BASE = st.secrets["AIRTABLE_BASE_ID"]
HF_TOKEN = st.secrets["HF_TOKEN"]

# Initialize Airtable
api = Api(AT_KEY)
target_table = api.table(AT_BASE, 'Matches')

# Initialize components
prediction_engine = PredictionEngine('football_model.pkl')
value_detector = ValueDetector(min_ev=0.05)
kelly_calculator = KellyCalculator(kelly_fraction=0.25)
bayesian_updater = BayesianUpdater(prior_confidence=0.8)
postmortem_analyzer = PostMortemAnalyzer()

# ============================================================================
# SESSION STATE & INITIALIZATION
# ============================================================================

if 'bankroll' not in st.session_state:
    st.session_state.bankroll = 1000.0

if 'bet_history' not in st.session_state:
    st.session_state.bet_history = []

# Initialize bankroll manager
bankroll_manager = BankrollManager(st.session_state.bankroll)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


class Match:
    """Parse match data from bulk input."""
    def __init__(self, home_team, away_team, home_odds=1.0, draw_odds=3.4, away_odds=3.8):
        self.home_team = home_team.strip()
        self.away_team = away_team.strip()
        self.home_odds = float(home_odds) if home_odds else 1.0
        self.draw_odds = float(draw_odds) if draw_odds else 3.4
        self.away_odds = float(away_odds) if away_odds else 3.8


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


def get_mock_market_odds(home_team: str = None, away_team: str = None) -> dict:
    """
    Get mock market odds in Decimal format.
    
    Returns:
        dict: {
            'home': float,
            'draw': float, 
            'away': float
        }
        
    Note:
        In production, connect to Odds API for real-time odds.
    """
    # Mock odds that vary slightly by team
    base_home = 2.10
    base_draw = 3.40
    base_away = 3.80
    
    return {
        'home': base_home,
        'draw': base_draw,
        'away': base_away
    }

# ============================================================================
# STREAMLIT APP - PAGE CONFIGURATION
# ============================================================================

st.set_page_config(page_title="🏆 AI Football Value Machine", layout="wide")

# Sidebar for configuration
with st.sidebar:
    st.title("⚙️ Settings")
    
    current_bankroll = st.number_input(
        "Current Bankroll ($)",
        value=st.session_state.bankroll,
        min_value=100.0,
        step=100.0
    )
    st.session_state.bankroll = current_bankroll
    
    kelly_fraction = st.slider(
        "Kelly Fraction (%)",
        min_value=5,
        max_value=100,
        value=25,
        step=5,
        help="Lower = safer, Higher = more aggressive"
    ) / 100
    
    min_ev = st.slider(
        "Min EV Threshold (%)",
        min_value=1,
        max_value=20,
        value=5,
        step=1,
        help="Minimum edge to consider a bet"
    ) / 100
    
    st.divider()
    
    # Show current status
    stats = bankroll_manager.get_statistics()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Bankroll", f"${current_bankroll:.2f}")
    with col2:
        st.metric("Bets Placed", stats['total_bets'])

# Fetch data from Airtable
teams_table = target_table.all()
stats_records = target_table.all()
team_names = sorted(
    [r["fields"]["Team Name"] for r in teams_table 
     if "Team Name" in r["fields"]]
)

# ============================================================================
# TAB 1: SINGLE MATCH PREDICTOR & VALUE FINDER
# ============================================================================

tab1, tab2, tab3 = st.tabs(
    ["🎯 Single Match Analyzer", "🚀 Bulk Analyzer", "📊 Analytics Dashboard"]
)

with tab1:
    st.title("⚽ Match Analyzer & Value Finder")
    st.write(
        "Analyze individual matches and discover betting value using AI predictions."
    )
    
    col1, col2 = st.columns(2)
    with col1:
        home_team = st.selectbox("Home Team", team_names, key="single_home")
    with col2:
        away_team = st.selectbox("Away Team", team_names, key="single_away")
    
    if st.button("🔍 Analyze Match", use_container_width=True):
        st.divider()
        
        # Step 1: Get team statistics
        home_avg_scored, _ = get_team_stats(home_team, teams_table, stats_records)
        _, away_avg_conceded = get_team_stats(away_team, teams_table, stats_records)
        
        # Step 2: Get predictions
        predictions = prediction_engine.predict_match(home_avg_scored, away_avg_conceded)
        
        # Step 3: Get market odds
        market_odds = get_mock_market_odds(home_team, away_team)
        
        # Step 4: Analyze for value
        analysis = value_detector.analyze_match(
            home_team,
            away_team,
            predictions,
            market_odds
        )
        
        # Display prediction confidence
        st.subheader(f"{home_team} vs {away_team}")
        
        pred_col1, pred_col2, pred_col3 = st.columns(3)
        pred_col1.metric("🏠 Home Win", f"{predictions['home_win'] * 100:.1f}%")
        pred_col2.metric("🤝 Draw", f"{predictions['draw'] * 100:.1f}%")
        pred_col3.metric("🚗 Away Win", f"{predictions['away_win'] * 100:.1f}%")
        
        # Display team statistics
        st.subheader("📈 Team Statistics")
        stat_col1, stat_col2 = st.columns(2)
        with stat_col1:
            st.write(f"**{home_team}** (Home)")
            st.write(f"- Avg Goals Scored: {home_avg_scored:.2f}")
        with stat_col2:
            st.write(f"**{away_team}** (Away)")
            st.write(f"- Avg Goals Conceded: {away_avg_conceded:.2f}")
        
        st.divider()
        
        # VALUE ANALYSIS SECTION
        st.subheader("💰 Value Analysis")
        
        if analysis['value_opportunities']:
            st.success("✅ **Value opportunities detected!**")
            
            for opp in analysis['value_opportunities']:
                with st.container(border=True):
                    col1, col2, col3, col4 = st.columns(4)
                    col1.write(f"**Outcome:** {opp['outcome']}")
                    col2.write(f"**Odds:** {opp['odds']:.2f}")
                    col3.write(f"**EV:** +{opp['ev']*100:.1f}%")
                    col4.write(f"**Confidence:** {opp['confidence']*100:.1f}%")
            
            # KELLY CRITERION STAKE SIZING
            st.subheader("🎲 Suggested Stakes (Using Kelly Criterion)")
            
            kelly_calc = KellyCalculator(kelly_fraction=kelly_fraction)
            bets = [
                {
                    'outcome': opp['outcome'],
                    'odds': opp['odds'],
                    'probability': opp['confidence']
                }
                for opp in analysis['value_opportunities']
            ]
            
            stakes = kelly_calc.calculate_multiple_stakes(current_bankroll, bets)
            
            stake_df = pd.DataFrame([
                {
                    'Outcome': s['outcome'],
                    'Odds': f"{s['odds']:.2f}",
                    'Your Probability': f"{s['probability']*100:.1f}%",
                    'Suggested Stake': f"${s['stake']:.2f}",
                    'EV per $1': f"+${s.get('kelly_frac', 0):.4f}"
                }
                for s in stakes if s['stake'] > 0
            ])
            
            if not stake_df.empty:
                st.dataframe(stake_df, use_container_width=True, hide_index=True)
                
                total_suggested = sum(s['stake'] for s in stakes)
                st.info(
                    f"💡 Total suggested stakes: ${total_suggested:.2f} "
                    f"({total_suggested/current_bankroll*100:.1f}% of bankroll)"
                )
            else:
                st.warning("No stakes meet safety threshold.")
        
        else:
            st.warning("❌ **No value opportunities found** - Expected value below threshold")
            st.write("Current implied probabilities match or exceed your predictions.")
        
        st.divider()
        
        # MARKET COMPARISON
        st.subheader("📊 Market Comparison")
        
        comparison_df = pd.DataFrame([
            {
                'Outcome': 'Home Win',
                'Your Probability': f"{predictions['home_win']*100:.1f}%",
                'Market Odds': f"{market_odds['home']:.2f}",
                'Implied Probability': f"{1/market_odds['home']*100:.1f}%",
                'Edge': f"{(predictions['home_win'] - 1/market_odds['home'])*100:+.1f}%"
            },
            {
                'Outcome': 'Draw',
                'Your Probability': f"{predictions['draw']*100:.1f}%",
                'Market Odds': f"{market_odds['draw']:.2f}",
                'Implied Probability': f"{1/market_odds['draw']*100:.1f}%",
                'Edge': f"{(predictions['draw'] - 1/market_odds['draw'])*100:+.1f}%"
            },
            {
                'Outcome': 'Away Win',
                'Your Probability': f"{predictions['away_win']*100:.1f}%",
                'Market Odds': f"{market_odds['away']:.2f}",
                'Implied Probability': f"{1/market_odds['away']*100:.1f}%",
                'Edge': f"{(predictions['away_win'] - 1/market_odds['away'])*100:+.1f}%"
            }
        ])
        
        st.dataframe(comparison_df, use_container_width=True, hide_index=True)
        
        st.divider()
        
        # VERDICT
        st.subheader("🎯 Match Verdict")
        
        outcomes = {
            "Home Win": predictions['home_win'],
            "Draw": predictions['draw'],
            "Away Win": predictions['away_win'],
        }
        most_likely = max(outcomes, key=outcomes.get)
        
        if most_likely == "Home Win":
            verdict_text = f"🏆 **Most Likely:** {home_team} to Win ({outcomes['Home Win']*100:.1f}%)"
        elif most_likely == "Away Win":
            verdict_text = f"🏆 **Most Likely:** {away_team} to Win ({outcomes['Away Win']*100:.1f}%)"
        else:
            verdict_text = f"🤝 **Most Likely:** Draw ({outcomes['Draw']*100:.1f}%)"
        
        st.success(verdict_text)
        
        model_conf = prediction_engine.get_model_confidence()
        bayesian_conf = bayesian_updater.get_confidence()
        st.info(
            f"**Model Confidence:** {model_conf*100:.1f}% | " 
            f"**Bayesian Confidence:** {bayesian_conf*100:.1f}%"
        )

# ============================================================================
# TAB 2: BULK MATCH ANALYZER
# ============================================================================

with tab2:
    st.title("🚀 Bulk Match Analyzer")
    st.write("Analyze multiple matches at once and find all value opportunities.")
    
    raw_input = st.text_area(
        "Paste match list here (format: Team A vs Team B | Odds)",
        height=150,
        placeholder="Example:\nManchester United vs Liverpool | 2.10 | 3.40 | 3.80\nArsenal vs Chelsea | 1.95 | 3.50 | 4.00"
    )
    
    if st.button("🔍 Analyze All Matches", use_container_width=True):
        if raw_input.strip():
            with st.spinner("Analyzing matches..."):
                # Simple parser for bulk input
                matches = []
                for line in raw_input.strip().split('\n'):
                    if " vs " in line.lower():
                        try:
                            parts = line.split('|')
                            teams = parts[0].strip()
                            h, a = re.split(r' vs ', teams, flags=re.IGNORECASE)
                            
                            home_o = float(parts[1].strip()) if len(parts) > 1 else 2.10
                            draw_o = float(parts[2].strip()) if len(parts) > 2 else 3.40
                            away_o = float(parts[3].strip()) if len(parts) > 3 else 3.80
                            
                            matches.append(Match(h, a, home_o, draw_o, away_o))
                        except:
                            continue
                
                if not matches:
                    st.error("No matches could be parsed.")
                else:
                    results_data = []
                    
                    for match in matches:
                        # Get team stats
                        h_scored, _ = get_team_stats(match.home_team, teams_table, stats_records)
                        _, a_conceded = get_team_stats(match.away_team, teams_table, stats_records)
                        
                        # Get predictions
                        predictions = prediction_engine.predict_match(h_scored, a_conceded)
                        
                        # Analyze for value
                        market_odds = {
                            'home': match.home_odds,
                            'draw': match.draw_odds,
                            'away': match.away_odds
                        }
                        
                        analysis = value_detector.analyze_match(
                            match.home_team,
                            match.away_team,
                            predictions,
                            market_odds
                        )
                        
                        # Find best opportunity
                        best_opp = None
                        best_ev = -1
                        if analysis['value_opportunities']:
                            best_opp = max(
                                analysis['value_opportunities'],
                                key=lambda x: x['ev']
                            )
                            best_ev = best_opp['ev']
                        
                        results_data.append({
                            'Match': f"{match.home_team} vs {match.away_team}",
                            'Best Value': best_opp['outcome'] if best_opp else "None",
                            'EV': f"{best_ev*100:+.1f}%" if best_ev > 0 else "—",
                            'Confidence': f"{best_opp['confidence']*100:.1f}%" if best_opp else "—",
                            'Status': '✅ VALUE' if best_ev > 0 else '❌ No Value'
                        })
                    
                    results_df = pd.DataFrame(results_data)
                    st.dataframe(results_df, use_container_width=True, hide_index=True)
                    
                    # Ranked by EV
                    st.subheader("🏆 Ranked by Expected Value")
                    sorted_results = sorted(
                        results_data,
                        key=lambda x: float(x['EV'].replace('%', '').replace('+', '') if x['EV'] != '—' else -1),
                        reverse=True
                    )
                    st.dataframe(
                        pd.DataFrame(sorted_results),
                        use_container_width=True,
                        hide_index=True
                    )
        else:
            st.warning("Please paste match data to analyze.")

# ============================================================================
# TAB 3: ANALYTICS DASHBOARD
# ============================================================================

with tab3:
    st.title("📊 Analytics Dashboard")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Bets", bankroll_manager.get_statistics()['total_bets'])
    with col2:
        stats = bankroll_manager.get_statistics()
        st.metric(
            "Win Rate",
            f"{stats['win_rate']:.1f}%" if stats['total_bets'] > 0 else "—"
        )
    with col3:
        stats = bankroll_manager.get_statistics()
        st.metric(
            "ROI",
            f"{stats['roi']:+.1f}%" if stats['total_bets'] > 0 else "—"
        )
    
    st.divider()
    
    st.subheader("🧠 Model Learning")
    bayesian_conf = bayesian_updater.get_confidence()
    st.metric("Bayesian Confidence", f"{bayesian_conf*100:.1f}%")
    st.write(
        f"Model confidence adjusts based on prediction surprises. "
        f"Current level: {'High' if bayesian_conf > 0.75 else 'Medium' if bayesian_conf > 0.5 else 'Low'}"
    )
    
    st.divider()
    
    st.subheader("📈 Bankroll Evolution")
    
    if bankroll_manager.history:
        history_df = pd.DataFrame(bankroll_manager.history)
        st.line_chart(history_df.set_index('timestamp')['potential_return'] if 'timestamp' in history_df else history_df)
    else:
        st.info("No betting history yet. Place bets to see evolution.")
    
    st.divider()
    
    st.subheader("⚠️ Risk Assessment")
    
    stats = bankroll_manager.get_statistics()
    risk = stats.get('ruin_risk', 0)
    
    if risk > 50:
        st.error(f"🔴 High Ruin Risk: {risk:.1f}%")
    elif risk > 25:
        st.warning(f"🟡 Moderate Ruin Risk: {risk:.1f}%")
    else:
        st.success(f"🟢 Low Ruin Risk: {risk:.1f}%")

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.markdown(
    """
    **⚡ Active Inference Football Prediction System**
    
    Powered by Bayesian uncertainty modeling, Kelly Criterion risk management, and real-time value detection.
    
    ---
    
    **Disclaimer:** This tool is for informational and entertainment purposes only.
    AI predictions are based on historical data and do not guarantee future results.
    Betting involves risk. Please gamble responsibly. 18+
    """
)
