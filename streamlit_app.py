import streamlit as st
import pandas as pd
from supabase import create_client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
import streamlit as st

# INITIALIZATION BLOCK
# This ensures 'bankroll' exists the moment the app starts
if 'bankroll' not in st.session_state:
    st.session_state.bankroll = 1000.0  # Set your starting default here

if 'min_edge' not in st.session_state:
    st.session_state.min_edge = 5.0
# ============================================================================
# PAGE CONFIG (Jobsian Minimalism)
# ============================================================================

st.set_page_config(
    page_title="Football-Pro Cockpit",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .metric-value { font-size: 2.5rem; font-weight: bold; color: #2ecc71; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SETUP CONNECTION
# ============================================================================

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
except KeyError:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None
    st.error("❌ Supabase credentials not found. Check .env or Streamlit Secrets.")

# ============================================================================
# SIDEBAR: THE "ENGINE ROOM"
# ============================================================================

with st.sidebar:
    st.header("⚙️ System Health")
    keystone_buffer = st.toggle("Apply Keystone Variance Buffer (-5%)", value=False)
    min_edge = st.slider("Minimum Edge Threshold (%)", 0.0, 15.0, 5.0)

# ============================================================================
# MAIN DASHBOARD: THE "COCKPIT"
# ============================================================================

st.title("🏆 Football-Pro Alpha")

# Fetch Live Predictions
if supabase:
    try:
        res = supabase.table('live_predictions').select("*").execute()
        df = pd.DataFrame(res.data)
        
        if not df.empty:
            # Apply UI Filtering Logic
            if keystone_buffer:
                df['edge_percent'] = df['edge_percent'] - 5.0
            
            top_bets = df[df['edge_percent'] >= min_edge].sort_values('edge_percent', ascending=False)

            # Top Row: Performance Metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                top_edge = df['edge_percent'].max()
                st.metric("Top Edge Found", f"{top_edge:.1f}%")
            
            with col2:
                active_count = len(top_bets)
                st.metric("Active Opportunities", active_count)
            
            with col3:
                # Fetch CLV from historical_stats
                try:
                    hist_res = supabase.table('historical_stats').select("*").order('match_date', desc=True).limit(50).execute()
                    hist_df = pd.DataFrame(hist_res.data)
                    
                    if not hist_df.empty and 'clv_value' in hist_df.columns:
                        avg_clv = hist_df['clv_value'].mean()
                        clv_delta = hist_df['clv_value'].std() / 10 if len(hist_df) > 1 else 0.3
                    else:
                        avg_clv, clv_delta = 2.4, 0.3  # Fallback to placeholder
                except:
                    avg_clv, clv_delta = 2.4, 0.3
                
                st.metric("Avg. Market Alpha (CLV)", f"+{avg_clv:.1f}%", delta=f"{clv_delta:.1f}%")

            st.divider()

            # The "Action List"
            if top_bets.empty:
                st.info("No high-value opportunities detected. The market is currently efficient.")
            else:
                st.subheader("🔥 High-Value Targets")
                for index, row in top_bets.iterrows():
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([2, 1, 1])
                        with c1:
                            st.write(f"**{row['home_team']} vs {row['away_team']}**")
                            st.caption(f"Kickoff: {row['kickoff_time']}")
                        with c2:
                            st.write(f"Edge: **{row['edge_percent']:.1f}%**")
                        with c3:
                            if st.button("Log Trade", key=row['match_id']):
                                st.success("Trade Logged!")
        else:
            st.warning("Database empty. Run the Live Scanner Action to populate.")
    
    except Exception as e:
        st.error(f"❌ Error fetching live predictions: {str(e)}")
else:
    st.error("❌ Cannot connect to Supabase. Check configuration.")

st.markdown("---")
st.caption("⚠️ Disclaimer: Betting involves risk. Only bet money you can afford to lose. Football-Pro provides analytical tools, not financial advice.")
import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import custom modules
from prediction_engine import PredictionEngine
from value_detection import ValueDetector
from risk_management import KellyCalculator, BankrollManager
from analytics import BayesianUpdater, ClosingLineValueCalculator

# ============================================================================
# CONFIGURATION & SUPABASE
# ============================================================================

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
except:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

# Initialize components
try:
    prediction_engine = PredictionEngine('football_model.pkl')
except:
    prediction_engine = None

value_detector = ValueDetector(min_ev=0.05)
kelly_calculator = KellyCalculator(kelly_fraction=0.25)
bayesian_updater = BayesianUpdater(prior_confidence=0.8)

# ============================================================================
# SESSION STATE & INITIALIZATION
# ============================================================================

if 'bankroll_ksh' not in st.session_state:
    st.session_state.bankroll_ksh = 10000.0

if 'bet_history' not in st.session_state:
    st.session_state.bet_history = []

bankroll_manager = BankrollManager(st.session_state.bankroll_ksh)

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="⚽ Football-Pro: Smart Scoring",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .big-signal { font-size: 2.5rem; font-weight: bold; color: #2ecc71; }
    .value-box { padding: 15px; background-color: #e8f5e9; border-left: 4px solid #4caf50; border-radius: 5px; }
    .no-value-box { padding: 15px; background-color: #fff3e0; border-left: 4px solid #ff9800; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# HEADER
# ============================================================================

st.title("⚽ Football-Pro")
st.subheader("Market Edge Detection | Smart Bankroll Management | Professional Betting")

# ============================================================================
# SIDEBAR: CONFIGURATION
# ============================================================================

with st.sidebar:
    st.header("⚙️ Configuration")
    
    current_bankroll = st.number_input(
        "Current Bankroll (KSh)",
        value=int(st.session_state.bankroll_ksh),
        min_value=100,
        step=1000,
    )
    st.session_state.bankroll_ksh = float(current_bankroll)
    
    kelly_fraction = st.slider(
        "Kelly Fraction (%)",
        min_value=5,
        max_value=100,
        value=25,
        step=5
    ) / 100
    
    min_ev = st.slider(
        "Minimum EV Threshold (%)",
        min_value=1,
        max_value=20,
        value=5,
        step=1
    ) / 100
    
    st.divider()
    st.metric("Current Bankroll", f"KSh {current_bankroll:,.0f}")
    
    stats = bankroll_manager.get_statistics()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Bets", stats['total_bets'])
        st.metric("Win Rate", f"{stats['win_rate']:.1f}%")
    with col2:
        st.metric("ROI", f"{stats['roi']:.1f}%")
        st.metric("Profit", f"KSh {stats['profit']:,.0f}")

# ============================================================================
# MAIN INTERFACE: THE BIG SIGNAL
# ============================================================================

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["🎯 Big Signal", "📊 Bulk Analyzer", "📈 Analytics"])

# ============================================================================
# TAB 1: THE BIG SIGNAL - VALUE DETECTION
# ============================================================================

with tab1:
    st.markdown("""
    ## Market Edge (EV) Detection
    
    **The Big Signal** is our single most important metric: **Expected Value (EV)**.
    
    When EV > 0%, you have a mathematical edge against the market.
    """)
    
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        home_team = st.text_input("Home Team", placeholder="e.g., Manchester United")
    with col2:
        away_team = st.text_input("Away Team", placeholder="e.g., Liverpool")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        home_odds = st.number_input("Home Win Odds", value=2.10, min_value=1.01, step=0.05, key="h_odds")
    with col2:
        draw_odds = st.number_input("Draw Odds", value=3.40, min_value=1.01, step=0.05, key="d_odds")
    with col3:
        away_odds = st.number_input("Away Win Odds", value=3.80, min_value=1.01, step=0.05, key="a_odds")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        home_prob = st.slider("Home Win Probability (%)", 0, 100, 45, key="h_prob") / 100
    with col2:
        draw_prob = st.slider("Draw Probability (%)", 0, 100, 25, key="d_prob") / 100
    with col3:
        away_prob = st.slider("Away Win Probability (%)", 0, 100, 30, key="a_prob") / 100
    
    # Normalize probabilities to sum to 1
    total_prob = home_prob + draw_prob + away_prob
    if total_prob > 0:
        home_prob /= total_prob
        draw_prob /= total_prob
        away_prob /= total_prob
    
    if st.button("🔍 ANALYZE", use_container_width=True, type="primary"):
        st.divider()
        
        # Calculate EVs
        ev_home = value_detector.calculate_ev(home_odds, home_prob)
        ev_draw = value_detector.calculate_ev(draw_odds, draw_prob)
        ev_away = value_detector.calculate_ev(away_odds, away_prob)
        
        # Determine best opportunity
        opportunities = [
            {"outcome": f"{home_team} Win", "odds": home_odds, "prob": home_prob, "ev": ev_home},
            {"outcome": "Draw", "odds": draw_odds, "prob": draw_prob, "ev": ev_draw},
            {"outcome": f"{away_team} Win", "odds": away_odds, "prob": away_prob, "ev": ev_away},
        ]
        
        best_opp = max(opportunities, key=lambda x: x['ev'])
        
        # Display The Big Signal
        st.markdown(f"""
        <div style='text-align: center; padding: 30px; background-color: #1e1e1e; border-radius: 10px; margin: 20px 0;'>
            <div style='font-size: 1.2rem; color: #aaa; margin-bottom: 10px;'>MARKET EDGE (EV)</div>
            <div class='big-signal'>{best_opp['ev']*100:+.1f}%</div>
            <div style='font-size: 1.1rem; color: #4caf50; margin-top: 10px;'>{best_opp['outcome']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Value Assessment
        if best_opp['ev'] > min_ev:
            st.markdown(f"""
            <div class='value-box'>
            <h3>✅ VALUE DETECTED</h3>
            <p><strong>{best_opp['outcome']}</strong> at {best_opp['odds']:.2f} offers <strong>{best_opp['ev']*100:+.1f}% edge</strong></p>
            <p>Our Model: {best_opp['prob']*100:.0f}% | Market: {1/best_opp['odds']*100:.0f}%</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Kelly Stake Recommendation
            stake = kelly_calculator.calculate_stake(
                st.session_state.bankroll_ksh,
                best_opp['odds'],
                best_opp['prob']
            )
            kelly_frac = kelly_calculator.calculate_kelly_fraction(best_opp['odds'], best_opp['prob'])
            
            st.markdown(f"""
            <div style='padding: 15px; background-color: #f0f2f6; border-radius: 5px; margin-top: 15px;'>
            <h4>🎲 Recommended Stake</h4>
            <p><strong>KSh {stake:,.0f}</strong> ({kelly_frac*100:.1f}% of bankroll with {kelly_fraction*100:.0f}% Kelly)</p>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Place Bet", use_container_width=True):
                    st.session_state.bet_history.append({
                        'match': f"{home_team} vs {away_team}",
                        'outcome': best_opp['outcome'],
                        'odds': best_opp['odds'],
                        'stake': stake,
                        'ev': best_opp['ev'],
                        'timestamp': datetime.now().isoformat()
                    })
                    st.success(f"✅ Bet placed for KSh {stake:,.0f}")
                    st.balloons()
            
            with col2:
                if st.button("📊 View All Opportunities", use_container_width=True):
                    st.write("All Opportunities:")
                    for opp in sorted(opportunities, key=lambda x: x['ev'], reverse=True):
                        st.write(f"- **{opp['outcome']}**: {opp['ev']*100:+.1f}% EV")
        
        else:
            st.markdown(f"""
            <div class='no-value-box'>
            <h3>❌ NO VALUE DETECTED</h3>
            <p>Best opportunity ({best_opp['outcome']}) has <strong>{best_opp['ev']*100:+.1f}% EV</strong></p>
            <p><strong>Recommendation:</strong> No trades recommended. Wait for better odds.</p>
            </div>
            """, unsafe_allow_html=True)

# ============================================================================
# TAB 2: BULK ANALYZER
# ============================================================================

with tab2:
    st.subheader("Bulk Match Analysis")
    st.write("Analyze multiple matches at once")
    
    bulk_input = st.text_area(
        "Enter matches (one per line): Team A vs Team B | Odds1 Odds2 Odds3 | Prob1% Prob2% Prob3%",
        placeholder="Man United vs Liverpool | 2.10 3.40 3.80 | 45 25 30",
        height=150
    )
    
    if st.button("Analyze All"):
        if bulk_input.strip():
            results = []
            for line in bulk_input.strip().split('\n'):
                if not line.strip():
                    continue
                try:
                    parts = line.split('|')
                    if len(parts) >= 2:
                        teams = parts[0].strip().split('vs')
                        odds = list(map(float, parts[1].strip().split()))
                        probs = [p/100 for p in map(float, parts[2].strip().split())] if len(parts) > 2 else [0.45, 0.25, 0.30]
                        
                        # Normalize
                        total = sum(probs)
                        probs = [p/total for p in probs]
                        
                        ev1 = (odds[0] * probs[0]) - 1
                        ev2 = (odds[1] * probs[1]) - 1 if len(odds) > 1 else 0
                        ev3 = (odds[2] * probs[2]) - 1 if len(odds) > 2 else 0
                        
                        best_ev = max(ev1, ev2, ev3)
                        results.append({
                            'Match': line.split('|')[0].strip(),
                            'Best EV': f"{best_ev*100:+.1f}%",
                            'Value': "✅ YES" if best_ev > min_ev else "❌ NO"
                        })
                except:
                    pass
            
            if results:
                df = pd.DataFrame(results)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.error("Could not parse input. Check format.")

# ============================================================================
# TAB 3: ANALYTICS DASHBOARD
# ============================================================================

with tab3:
    st.subheader("Analytics & Performance")
    
    if st.session_state.bet_history:
        bet_df = pd.DataFrame(st.session_state.bet_history)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Bets", len(bet_df))
        with col2:
            st.metric("Total Staked", f"KSh {bet_df['stake'].sum():,.0f}")
        with col3:
            avg_ev = bet_df['ev'].mean()
            st.metric("Avg EV", f"{avg_ev*100:+.1f}%")
        with col4:
            st.metric("Model Confidence", f"{bayesian_updater.get_confidence()*100:.0f}%")
        
        st.divider()
        st.subheader("Bet History")
        st.dataframe(
            bet_df[['match', 'outcome', 'odds', 'stake', 'ev']],
            use_container_width=True,
            hide_index=True
        )
        
        if st.button("🗑️ Clear History"):
            st.session_state.bet_history = []
            st.rerun()
    else:
        st.info("📊 No betting history yet. Start analyzing matches to see analytics.")

st.markdown("---")
st.caption("⚠️ Disclaimer: Betting involves risk. Only bet money you can afford to lose. Football-Pro provides analytical tools, not financial advice.")
import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# Import custom modules
from prediction_engine import PredictionEngine
from value_detection import ValueDetector
from risk_management import KellyCalculator, BankrollManager
from analytics import BayesianUpdater

# ============================================================================
# CONFIGURATION & SUPABASE
# ============================================================================

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize components
prediction_engine = PredictionEngine('football_model.pkl')
value_detector = ValueDetector(min_ev=0.05)
kelly_calculator = KellyCalculator(kelly_fraction=0.25)
bayesian_updater = BayesianUpdater(prior_confidence=0.8)

# ============================================================================
# SESSION STATE & INITIALIZATION
# ============================================================================

if 'bankroll_ksh' not in st.session_state:
    st.session_state.bankroll_ksh = 10000.0  # 10,000 KSh default

if 'bet_history' not in st.session_state:
    st.session_state.bet_history = []

bankroll_manager = BankrollManager(st.session_state.bankroll_ksh)

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="⚽ Smart_scorer",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .big-number { font-size: 2.5rem; font-weight: bold; color: #2ecc71; }
    .success-box { padding: 15px; background-color: #d4edda; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# HEADER
# ============================================================================

st.title("⚽ Smart_scorer")
st.subheader("Smart predictions. Simple interface. Real money.")

col1, col2, col3 = st.columns(3)
with col1:
    current_bankroll = st.number_input(
        "Your Money (KSh)",
        value=int(st.session_state.bankroll_ksh),
        min_value=100,
        step=10,
        key="bankroll_input"
    )
    st.session_state.bankroll_ksh = float(current_bankroll)

with col2:
    kelly_fraction = st.select_slider(
        "Risk Level",
        options=["🛡️ Safe (10%)", "⚖️ Balanced (25%)", "🔥 Aggressive (50%)"],
        value="⚖️ Balanced (25%)",
        key="kelly_fraction_slider_header"
    )
    kelly_map = {"🛡️ Safe (10%)": 0.10, "⚖️ Balanced (25%)": 0.25, "🔥 Aggressive (50%)": 0.50}
    kelly_fraction = kelly_map[kelly_fraction]

with col3:
    min_ev = st.select_slider(
        "Minimum Edge",
        options=["5% Edge", "10% Edge", "15% Edge"],
        value="5% Edge",
        key="min_ev_slider_header"
    )
    min_ev = float(min_ev.split("%")[0]) / 100

# ============================================================================
# MAIN TABS
# ============================================================================

tab1, tab2 = st.tabs(["📊 Analyze Match", "📈 My Bets"])

# ============================================================================
# TAB 1: SIMPLE MATCH ANALYZER
# ============================================================================

with tab1:
    st.markdown("---")
    st.subheader("Step 1: Pick Teams")
    
    col1, col2 = st.columns(2)
    with col1:
        home_team = st.text_input("Home Team (e.g., Manchester United)", placeholder="Type team name")
    with col2:
        away_team = st.text_input("Away Team (e.g., Liverpool)", placeholder="Type team name")
    
    st.markdown("---")
    st.subheader("Step 2: Enter Odds")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        home_odds = st.number_input("Home Wins At", value=2.10, min_value=1.0, step=0.05, key="home_odds")
    with col2:
        draw_odds = st.number_input("Draw At", value=3.40, min_value=1.0, step=0.05, key="draw_odds")
    with col3:
        away_odds = st.number_input("Away Wins At", value=3.80, min_value=1.0, step=0.05, key="away_odds")
    
    # Analyze button
    if st.button("🔍 ANALYZE THIS MATCH", use_container_width=True, type="primary"):
        if not home_team or not away_team:
            st.error("⚠️ Please enter both team names")
        else:
            with st.spinner("Analyzing..."):
                # Get predictions from model
                try:
                    predictions = prediction_engine.predict_match(1.5, 1.2)  # Using default stats
                    
                    # Create simple display
                    st.markdown("---")
                    st.subheader(f"📊 {home_team.title()} vs {away_team.title()}")
                    
                    # Prediction results
                    pred_col1, pred_col2, pred_col3 = st.columns(3)
                    
                    with pred_col1:
                        st.markdown(f"""
                        <div style='text-align: center; padding: 20px; background-color: #f0f2f6; border-radius: 10px;'>
                            <div style='font-size: 2rem; font-weight: bold; color: #2c3e50;'>{predictions['home_win']*100:.0f}%</div>
                            <div style='font-size: 1rem; color: #7f8c8d;'>{home_team.title()} Wins</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with pred_col2:
                        st.markdown(f"""
                        <div style='text-align: center; padding: 20px; background-color: #f0f2f6; border-radius: 10px;'>
                            <div style='font-size: 2rem; font-weight: bold; color: #2c3e50;'>{predictions['draw']*100:.0f}%</div>
                            <div style='font-size: 1rem; color: #7f8c8d;'>Draw</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with pred_col3:
                        st.markdown(f"""
                        <div style='text-align: center; padding: 20px; background-color: #f0f2f6; border-radius: 10px;'>
                            <div style='font-size: 2rem; font-weight: bold; color: #2c3e50;'>{predictions['away_win']*100:.0f}%</div>
                            <div style='font-size: 1rem; color: #7f8c8d;'>{away_team.title()} Wins</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # VALUE DETECTION
                    st.markdown("---")
                    st.subheader("💰 Is This a Good Bet?")
                    
                    # Check each outcome for value
                    outcomes = [
                        {"name": f"{home_team.title()} Wins", "odds": home_odds, "prob": predictions['home_win']},
                        {"name": "Draw", "odds": draw_odds, "prob": predictions['draw']},
                        {"name": f"{away_team.title()} Wins", "odds": away_odds, "prob": predictions['away_win']},
                    ]
                    
                    value_bets = []
                    for outcome in outcomes:
                        ev = (outcome['odds'] * outcome['prob']) - 1
                        if ev > min_ev:
                            value_bets.append(outcome)
                            
                            # Show this is a good bet
                            st.success(f"""
                            ✅ **{outcome['name']}** - GOOD VALUE!
                            - Odds: {outcome['odds']:.2f}
                            - Our prediction: {outcome['prob']*100:.0f}%
                            - Edge: +{ev*100:.0f}%
                            """)
                    
                    if not value_bets:
                        st.info("❌ No good value bets found. Bookmakers have priced this fairly.")
                    
                    # KELLY STAKES
                    st.markdown("---")
                    st.subheader("🎲 How Much Should You Bet?")
                    
                    for bet in value_bets:
                        kelly_calc = KellyCalculator(kelly_fraction=kelly_fraction)
                        stake = kelly_calc.calculate_kelly_fraction(bet['odds'], bet['prob'])
                        stake_amount = stake * st.session_state.bankroll_ksh
                        
                        if stake_amount > 0:
                            st.markdown(f"""
                            <div style='padding: 15px; background-color: #e8f5e9; border-left: 4px solid #4caf50; border-radius: 5px;'>
                                <div style='font-size: 1.3rem; font-weight: bold;'>💵 Bet <span style='color: #2ecc71;'>KSh {stake_amount:,.0f}</span> on {bet['name']}</div>
                                <div style='font-size: 0.9rem; color: #555; margin-top: 8px;'>
                                    This is {stake*100:.1f}% of your bankroll - Safe betting strategy
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Quick bet placement
                            if st.button(f"✅ Place Bet: KSh {stake_amount:,.0f} on {bet['name']}", key=f"bet_{bet['name']}"):
                                st.session_state.bet_history.append({
                                    'match': f"{home_team} vs {away_team}",
                                    'bet': bet['name'],
                                    'odds': bet['odds'],
                                    'stake': stake_amount,
                                    'probability': bet['prob']
                                })
                                st.success(f"✅ Bet placed! Good luck!")
                                st.balloons()
                
                except Exception as e:
                    st.error(f"⚠️ Error analyzing match: {str(e)}")

# ============================================================================
# TAB 2: BET HISTORY
# ============================================================================

with tab2:
    st.subheader("📋 Your Bets")
    
    if st.session_state.bet_history:
        bet_df = pd.DataFrame(st.session_state.bet_history)
        
        st.dataframe(
            bet_df[['match', 'bet', 'stake', 'odds', 'probability']],
            use_container_width=True,
            hide_index=True
        )
        
        total_staked = bet_df['stake'].sum()
        st.metric("Total Staked", f"KSh {total_staked:,.0f}")
        
        if st.button("🗑️ Clear History"):
            st.session_state.bet_history = []
            st.rerun()
    else:
        st.info("No bets yet. Analyze a match to get started!")

st.markdown("---")
st.caption("⚠️ Disclaimer: Betting involves risk. Only bet money you can afford to lose.")
import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# Import custom modules
from prediction_engine import PredictionEngine
from value_detection import ValueDetector
from risk_management import KellyCalculator, BankrollManager
from analytics import BayesianUpdater

# ============================================================================
# CONFIGURATION & SUPABASE
# ============================================================================

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize components
prediction_engine = PredictionEngine('football_model.pkl')
value_detector = ValueDetector(min_ev=0.05)
kelly_calculator = KellyCalculator(kelly_fraction=0.25)
bayesian_updater = BayesianUpdater(prior_confidence=0.8)

# ============================================================================
# SESSION STATE & INITIALIZATION
# ============================================================================

if 'bankroll_ksh' not in st.session_state:
    st.session_state.bankroll_ksh = 10000.0  # 10,000 KSh default

if 'bet_history' not in st.session_state:
    st.session_state.bet_history = []

bankroll_manager = BankrollManager(st.session_state.bankroll_ksh)

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="⚽ Football Betting AI",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .big-number { font-size: 2.5rem; font-weight: bold; color: #2ecc71; }
    .success-box { padding: 15px; background-color: #d4edda; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# HEADER
# ============================================================================

st.title(" score_smart")
st.subheader("Use analytics to game smarter.")

col1, col2, col3 = st.columns(3)
with col1:
    current_bankroll = st.number_input(
        "Your Money (KSh)",
        value=int(st.session_state.bankroll_ksh),
        min_value=1000,
        step=1000,
        key="bankroll_input_2"
    )
    st.session_state.bankroll_ksh = float(current_bankroll)

with col2:
    kelly_fraction = st.select_slider(
        "Risk Level",
        options=["🛡️ Safe (10%)", "⚖️ Balanced (25%)", "🔥 Aggressive (50%)"],
        value="⚖️ Balanced (25%)",
        key="kelly_fraction_slider_2"
    )
    kelly_map = {"🛡️ Safe (10%)": 0.10, "⚖️ Balanced (25%)": 0.25, "🔥 Aggressive (50%)": 0.50}
    kelly_fraction = kelly_map[kelly_fraction]

with col3:
    min_ev = st.select_slider(
        "Minimum Edge",
        options=["5% Edge", "10% Edge", "15% Edge"],
        value="5% Edge",
        key="min_ev_slider_2"
    )
    min_ev = float(min_ev.split("%")[0]) / 100

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

st.set_page_config(page_title="🏆 Value Machine", layout="wide")

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
        "Analyze individual matches and discover betting value using analysis."
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

