from typing import List

from pydantic import BaseModel, Field
from huggingface_hub import InferenceClient
import streamlit as st


class SingleMatch(BaseModel):
    """Represents a single match with odds."""
    home_team: str
    away_team: str
    home_odds: float = Field(description="Decimal odds for home win")
    draw_odds: float = Field(description="Decimal odds for draw")
    away_odds: float = Field(description="Decimal odds for away win")


class MatchList(BaseModel):
    """List of matches with odds."""
    matches: List[SingleMatch]


def get_hf_client() -> InferenceClient:
    """Initialize and return HuggingFace Inference client."""
    return InferenceClient(
        "meta-llama/Llama-3.2-3B-Instruct",
        token=st.secrets["HF_TOKEN"]
    )


def parse_bulk_odds(raw_text: str) -> str:
    """
    Extract match data and odds from raw text using HuggingFace Llama model.

    Args:
        raw_text: Messy text containing match and odds information

    Returns:
        JSON string with extracted match data
    """
    client = get_hf_client()
    response = client.text_generation(
        f"Extract match data into JSON: {raw_text}",
        max_new_tokens=500,
    )
    return response