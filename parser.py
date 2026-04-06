from typing import List

import streamlit as st
from groq import Groq
from pydantic import BaseModel, Field

# Initialize Groq client
client = Groq(api_key=st.secrets["GROQ_API_KEY"])


class SingleMatch(BaseModel):
    home_team: str
    away_team: str
    home_odds: float = Field(description="Decimal odds for home win")
    draw_odds: float = Field(description="Decimal odds for draw")
    away_odds: float = Field(description="Decimal odds for away win")


class MatchList(BaseModel):
    matches: List[SingleMatch]


def parse_bulk_odds(raw_text: str) -> List[SingleMatch]:
    """Extract match data and odds from raw text using Groq API."""
    return client.chat.completions.create(
        model="gpt-4o-mini",
        response_model=MatchList,
        messages=[
            {
                "role": "system",
                "content": "You are a betting data extractor. Convert the following messy text into a structured list of matches and their 1X2 decimal odds.",
            },
            {"role": "user", "content": raw_text},
        ],
    ).matches