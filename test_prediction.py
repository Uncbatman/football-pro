import pickle
import pandas as pd

# Load the brain we just built
with open('football_model.pkl', 'rb') as f:
    model = pickle.load(f)

# Mock stats: Home team scored 2, Away team scored 1 in recent games
# Format: [[home_goals, away_goals]]
test_match = pd.DataFrame([[2, 1]], columns=['home_goals', 'away_goals'])

# Get probabilities
probs = model.predict_proba(test_match)[0]

print(f"--- AI Prediction Test ---")
print(f"Draw Probability: {probs[0]*100:.2f}%")
print(f"Home Win Probability: {probs[1]*100:.2f}%")
print(f"Away Win Probability: {probs[2]*100:.2f}%")