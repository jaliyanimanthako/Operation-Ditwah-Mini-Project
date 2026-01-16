"""
Logistic Commander - Rescue Operation Planner

This script orchestrates disaster response logistics using:
1. Chain-of-Thought (CoT) reasoning for incident scoring
2. Tree-of-Thought (ToT) reasoning for strategic route planning

Input: ../output/Incidents.csv
Output: Console display of optimal rescue route
"""

import sys
import os
import time
import pandas as pd
sys.path.append("../..")

from cot_scoring import score_incident
from utils.prompts import render
from utils.llm_client import LLMClient
from utils.logging_utils import log_llm_call
from utils.router import pick_model, should_use_reasoning_model
from utils.examples import examples

# Configuration
INCIDENTS_FILE = '../data/Incidents.csv'
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def call_with_retry(client, messages, temperature, max_tokens):
    """Call LLM with retry logic for None responses and API errors."""
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat(messages, temperature=temperature, max_tokens=max_tokens)
            if response.get('text') is not None:
                return response, None
            print(f"[Retry {attempt + 1}/{MAX_RETRIES}] Got None response, retrying...")
            time.sleep(RETRY_DELAY)
        except Exception as e:
            last_error = str(e)
            print(f"[Retry {attempt + 1}/{MAX_RETRIES}] API error: {last_error[:50]}...")
            time.sleep(RETRY_DELAY)
    return response if 'response' in dir() else {'text': None}, last_error


def load_incidents(file_path):
    """Load incidents from CSV with error handling."""
    if not os.path.exists(file_path):
        return None, f"File not found: {file_path}"
    
    try:
        data = pd.read_csv(file_path)
        if data.empty:
            return None, "Incidents file is empty"
        return data, None
    except pd.errors.EmptyDataError:
        return None, "Incidents file is empty or malformed"
    except Exception as e:
        return None, str(e)


def tot_strategy(scores, client_reasoning):
    """Generate strategic plan using Tree-of-Thought reasoning."""
    
    print("\n" + "-" * 60)
    print("PHASE 2: STRATEGIC PLANNING (Tree-of-Thought)")
    print("-" * 60)
    
    # Validate scores
    if not scores:
        print("ERROR: No scores available for strategic planning.")
        print("Cannot generate rescue route without incident scores.")
        return None
    
    # Filter to only include score entries (not area entries)
    score_entries = {k: v for k, v in scores.items() if 'ID' in k and isinstance(v, (int, float))}
    if not score_entries:
        print("ERROR: No valid numeric scores found.")
        return None
    
    print(f"Planning route for {len(score_entries)} incidents...")
    print("Analyzing rescue routes using ToT reasoning...")
    print("Generating 3 strategy branches...")
    
    strategy = """You have a rescue boat at Ragama, explore the possibilities how you can save people with the given score in descending order, save the closest first, save the furthest first and choose the optimal route"""
    
    problem = f"""{strategy} 
    {scores}"""

    try:
        prompt_text, spec = render(
            'tot_reasoning.v1',
            role='strategic planner',
            problem=problem,
            branches='3'
        )
    except Exception as e:
        print(f"ERROR: Failed to render prompt: {e}")
        return None

    messages = [{'role': 'user', 'content': prompt_text}]
    print("Computing optimal rescue strategy...\n")
    
    response, error = call_with_retry(
        client_reasoning, 
        messages, 
        temperature=spec.temperature, 
        max_tokens=spec.max_tokens
    )

    print("=" * 60)
    print("STRATEGIC ASSESSMENT RESULT")
    print("=" * 60)
    
    result_text = response.get('text') if response else None
    
    if result_text is None:
        print("ERROR: Unable to generate strategic plan after multiple attempts.")
        if error:
            print(f"Last error: {error}")
        print("Please try running the script again.")
        return None
    else:
        print(result_text)
    
    print("\n" + "=" * 60)
    print("PLANNING COMPLETE")
    print("=" * 60)
    
    return result_text


def main():
    """Main function with comprehensive error handling."""
    
    print("\n" + "=" * 60)
    print("LOGISTIC COMMANDER - RESCUE OPERATION PLANNER")
    print("=" * 60)
    
    # Load incident data
    print("\nLoading incident data...")
    data, load_error = load_incidents(INCIDENTS_FILE)
    
    if load_error:
        print(f"ERROR: {load_error}")
        print("\nTroubleshooting:")
        print(f"  1. Ensure {INCIDENTS_FILE} exists")
        print("  2. Check the file has valid CSV format")
        print("  3. Run the data preparation script first")
        sys.exit(1)
    
    print(f"Loaded {len(data)} incidents from database.")
    
    # Initialize reasoning client
    print("\nInitializing reasoning model...")
    try:
        reasoning_model = pick_model('google', 'cot')
        client_reasoning = LLMClient('google', reasoning_model)
        print(f"Model loaded: {reasoning_model}")
    except Exception as e:
        print(f"ERROR: Failed to initialize LLM client: {e}")
        sys.exit(1)
    
    try:
        # Phase 1: Incident Scoring
        print("\n" + "-" * 60)
        print("PHASE 1: INCIDENT SCORING")
        print("-" * 60)
        
        scores = score_incident(data)
        
        if not scores:
            print("ERROR: No scores generated. Cannot proceed with planning.")
            sys.exit(1)
        
        # Phase 2: Strategic Planning
        result = tot_strategy(scores, client_reasoning)
        
        if result is None:
            print("\nWARNING: Strategic planning failed.")
            print("Scores were generated but route optimization failed.")
            sys.exit(1)
        
        # Success
        print("\n" + "=" * 60)
        print("MISSION PLANNING SUCCESSFUL")
        print("=" * 60)
        print("The rescue operation plan has been generated.")
        print("Review the strategic assessment above for the optimal route.")
        
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("INTERRUPTED BY USER (Ctrl+C)")
        print("=" * 60)
        print("Operation cancelled. Partial results may have been displayed.")
        sys.exit(0)
    
    except Exception as e:
        print(f"\nUNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
