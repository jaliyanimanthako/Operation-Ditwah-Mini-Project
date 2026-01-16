"""
Chain-of-Thought Incident Scoring Module

This module scores disaster incidents based on severity criteria using
Chain-of-Thought reasoning to analyze each incident.

Used by: logistic_commander.py
"""

import sys
import os
import time
sys.path.append("../..")

from utils.prompts import render
from utils.llm_client import LLMClient
from utils.logging_utils import log_llm_call
from utils.router import pick_model, should_use_reasoning_model
from utils.examples import examples
from utils.csv_maker import read_text_file
import pandas as pd

# Configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
DEFAULT_SCORE = 5  # Default score when extraction fails


def call_with_retry(client, messages, temperature, max_tokens):
    """Call LLM with retry logic for None responses and API errors."""
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat(messages, temperature=temperature, max_tokens=max_tokens)
            if response.get('text') is not None:
                return response, None
            print(f"    [Retry {attempt + 1}/{MAX_RETRIES}] Got None response, retrying...")
            time.sleep(RETRY_DELAY)
        except Exception as e:
            last_error = str(e)
            print(f"    [Retry {attempt + 1}/{MAX_RETRIES}] API error: {last_error[:50]}...")
            time.sleep(RETRY_DELAY)
    return response if 'response' in dir() else {'text': None}, last_error


def initialize_clients():
    """Initialize LLM clients with error handling."""
    try:
        reasoning_model = pick_model('google', 'cot')
        client_reasoning = LLMClient('google', reasoning_model)
        
        general_model = pick_model('google', 'general')
        client_general = LLMClient('google', general_model)
        
        return client_reasoning, client_general, None
    except Exception as e:
        return None, None, str(e)


# Scoring criteria
CRITERIA = """
Based on the given incident, provide a mark for that, start with basic score of 5 for each incident and then add or subtract based on the following criteria:
1. If the age is less than 5 or more than 60, add 2 to the score
2. If there is a life threat or need a rescue add 3 to the score
3. If there is a need of Medicine (Insulin) add 1 to the score
"""


def extract_numeric_score(score_text):
    """Extract numeric score from text, handling various formats."""
    if score_text is None:
        return DEFAULT_SCORE
    
    # Clean the text
    cleaned = score_text.strip().lower()
    
    # Handle 'none' or empty
    if cleaned in ['none', '', 'null']:
        return DEFAULT_SCORE
    
    # Try to extract digits
    import re
    numbers = re.findall(r'\d+', cleaned)
    if numbers:
        score = int(numbers[0])
        # Sanity check: score should be between 0 and 15
        if 0 <= score <= 15:
            return score
    
    return DEFAULT_SCORE


def score_incident(data):
    """Score incidents with comprehensive error handling."""
    
    # Initialize clients
    client_reasoning, client_general, init_error = initialize_clients()
    if init_error:
        print(f"ERROR: Failed to initialize LLM clients: {init_error}")
        return {}
    
    # Handle empty dataframe
    if data is None or data.empty:
        print("WARNING: No incident data provided.")
        return {}
    
    scores = {}
    total_incidents = len(data)
    success_count = 0
    error_count = 0
    
    print("\n" + "=" * 60)
    print("INCIDENT SCORING PROCESS")
    print("=" * 60)
    print(f"Total incidents to process: {total_incidents}")
    print("-" * 60)
    
    # Required columns check
    required_cols = ['ID', 'Area', 'Time', 'People', 'Ages', 'Main Need', 'Message']
    missing_cols = [col for col in required_cols if col not in data.columns]
    if missing_cols:
        print(f"WARNING: Missing columns in data: {missing_cols}")
        print("Some incident details may be incomplete.")
    
    for index, row in data.iterrows():
        try:
            incident_id = row.get('ID', f'Unknown-{index}')
            area = row.get('Area', 'Unknown')
            
            print(f"\n[{index + 1}/{total_incidents}] Processing incident ID: {incident_id} | Area: {area}")
            print("    Analyzing with CoT reasoning model...")
            
            # Build incident string safely
            incident = f"Time: {row.get('Time', 'N/A')}, Area: {area}, People: {row.get('People', 'N/A')}, Ages: {row.get('Ages', 'N/A')}, Main Need: {row.get('Main Need', 'N/A')}, Message: {row.get('Message', 'N/A')}"
            problem = f"{CRITERIA}\nIncident: {incident}"
            
            prompt_text, spec = render(
                'cot_reasoning.v1',
                role='damage controlling officer',
                problem=problem
            )

            general_prompt_text, general_spec = render(
                'zero_shot.v1',
                role='score extractor',
                instruction='Extract the score from the given text',
                constraints='Return only the score as a single number',
                format='Only digits'
            )

            # Call reasoning model
            messages = [{'role': 'user', 'content': problem}]
            response, error = call_with_retry(client_reasoning, messages, temperature=0, max_tokens=spec.max_tokens)
            
            reasoning_text = response.get('text') if response else None
            if reasoning_text is None:
                reasoning_text = f"Unable to analyze - defaulting to base score of {DEFAULT_SCORE}"
                print(f"    Warning: Reasoning model failed, using default")
            
            print("    Extracting score...")

            # Call score extraction model
            general_messages = [{'role': 'user', 'content': f"{general_prompt_text} Text: {reasoning_text}"}]
            general_response, error = call_with_retry(client_general, general_messages, temperature=0, max_tokens=general_spec.max_tokens)
            
            score_text = general_response.get('text') if general_response else None
            final_score = extract_numeric_score(score_text)
            
            if score_text is None or final_score == DEFAULT_SCORE:
                print(f"    Warning: Using default score: {DEFAULT_SCORE}")
            
            scores[f"Incident ID {incident_id}"] = final_score
            scores[f"Incident Area {area}"] = area
            print(f"    Score assigned: {final_score}")
            success_count += 1
            
        except Exception as e:
            error_count += 1
            print(f"    ERROR processing incident: {e}")
            # Use default score on error
            scores[f"Incident ID {row.get('ID', index)}"] = DEFAULT_SCORE
    
    print("\n" + "-" * 60)
    print("SCORING COMPLETE!")
    print("-" * 60)
    print(f"Successfully scored: {success_count}/{total_incidents}")
    print(f"Errors: {error_count}")
    print("Final Scores:", {k: v for k, v in scores.items() if 'ID' in k})
    print("=" * 60 + "\n")
    
    return scores
