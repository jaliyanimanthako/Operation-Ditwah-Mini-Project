"""
JSON Extraction Module for Crisis Events

This module extracts structured JSON data from unstructured text
describing flood/disaster events using LLM-based extraction.

Used by: Crisisevent.py
"""

import sys
import time
import json
sys.path.append("../../")

from utils.prompts import render
from utils.llm_client import LLMClient
from utils.logging_utils import log_llm_call
from utils.router import pick_model, should_use_reasoning_model
from utils.examples import examples
from utils.csv_maker import read_text_file

# Configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Initialize client once (more efficient than per-call)
_client = None

def get_client():
    """Get or create LLM client (singleton pattern)."""
    global _client
    if _client is None:
        try:
            general_model = pick_model('google', 'general')
            _client = LLMClient('google', general_model)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize LLM client: {e}")
    return _client


def validate_json(json_str):
    """Validate that the string is valid JSON."""
    try:
        parsed = json.loads(json_str)
        return True, parsed, None
    except json.JSONDecodeError as e:
        return False, None, str(e)


def extract_json(text):
    """Extract structured JSON from text with retry logic and validation."""
    
    if not text or not text.strip():
        return None
    
    schema = """
    {
    "district": "String (Must be one of the 25 Sri Lankan districts)",
    "flood_level_meters": "Float or null (Use null if not mentioned)",
    "vicLm_count": "Integer",
    "main_need": "String (The most urgent requirement mentioned)",
    "status": "String (MUST be exactly 'Critical', 'Warning', or 'Stable')"
    }
    """

    try:
        prompt_text, spec = render(
            'json_extract.v1',
            role='damage controlling officer',
            schema=schema,
            text=text
        )
    except Exception as e:
        raise RuntimeError(f"Failed to render prompt: {e}")

    client = get_client()
    messages = [{'role': 'user', 'content': prompt_text}]
    
    # Retry logic
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat(messages, temperature=0, max_tokens=spec.max_tokens)
            result_text = response.get('text')
            
            if result_text is None:
                last_error = "LLM returned None"
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                continue
            
            # Clean the response
            clean_json = result_text.replace("```json", "").replace("```", "").strip()
            
            # Validate JSON
            is_valid, parsed, error = validate_json(clean_json)
            if is_valid:
                return clean_json
            else:
                last_error = f"Invalid JSON: {error}"
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                continue
                
        except Exception as e:
            last_error = str(e)
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            continue
    
    # All retries failed
    raise RuntimeError(f"JSON extraction failed after {MAX_RETRIES} attempts: {last_error}")
