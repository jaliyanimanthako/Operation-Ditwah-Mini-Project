"""
Description:
    This script performs automated classification of text messages using a 
    Large Language Model (LLM). It reads messages from a text file and 
    classifies each message based on three key attributes. 

Input:
    - Text file containing messages (one per line)
    - Location: ../data/Sample Messages.txt

Output:
    - Excel file: ../output/classified_messages.xlsx
    - Columns: District, Intent, Priority
"""

import sys
import os
import re
import time
sys.path.append("..")

from utils.prompts import render
from utils.llm_client import LLMClient
from utils.router import pick_model
from utils.examples import examples
from utils.csv_maker import read_text_file

# Configuration
INPUT_FILE = '../data/Sample Messages.txt'
OUTPUT_FILE = '../output/classified_messages.xlsx'
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Valid values for validation
VALID_INTENTS = ['Info', 'Rescue', 'Supply', 'Other', 'None']
VALID_PRIORITIES = ['High', 'Low', 'None']


def validate_response(response_text):
    """Validate that the LLM response matches expected format."""
    if not response_text:
        return False, "Empty response"
    
    # Check for expected format: District: X | Intent: Y | Priority: Z
    pattern = r'District:\s*\w+.*\|\s*Intent:\s*\w+.*\|\s*Priority:\s*\w+'
    if not re.search(pattern, response_text, re.IGNORECASE):
        return False, "Response doesn't match expected format"
    
    return True, None


def message_classification(text):
    """Classify a message with retry logic and error handling."""
    model = pick_model('google', 'reason')
    client = LLMClient('google', model)
    prompt_text, spec = render(
        'few_shot.v1',
        role='message classifier',
        examples=examples,
        query=f'Review: {text}',
        constraints='Follow the pattern in examples: provide District: [Name] | Intent: [Category] | Priority: [High/Low], If any field is not applicable, use None. Do not add any explanations. Intent should be one of [Info, Rescue, Supply, Other].',
        format='District: {{district}} | Intent: {{intent}} | Priority: {{priority}}'
    )

    messages = [{'role': 'user', 'content': prompt_text}]
    
    # Retry logic for API calls
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat(messages, temperature=0.2)
            result = response.get('text')
            
            if result is not None:
                # Validate response format
                is_valid, error_msg = validate_response(result)
                if is_valid:
                    return result, None
                else:
                    last_error = error_msg
            else:
                last_error = "LLM returned None"
                
            if attempt < MAX_RETRIES - 1:
                print(f"    [Retry {attempt + 1}/{MAX_RETRIES}] {last_error}, retrying...")
                time.sleep(RETRY_DELAY)
                
        except Exception as e:
            last_error = str(e)
            if attempt < MAX_RETRIES - 1:
                print(f"    [Retry {attempt + 1}/{MAX_RETRIES}] API error: {last_error[:50]}...")
                time.sleep(RETRY_DELAY)
    
    return None, last_error


def ensure_output_directory(output_path):
    """Create output directory if it doesn't exist."""
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")


def main():
    """Main function with comprehensive error handling."""
    
    print("\n" + "=" * 60)
    print("MESSAGE CLASSIFICATION PIPELINE")
    print("=" * 60)
    
    # Check if input file exists
    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        print("Please ensure the file exists and the path is correct.")
        sys.exit(1)
    
    # Ensure output directory exists
    ensure_output_directory(OUTPUT_FILE)
    
    # Read the file with proper encoding handling
    print(f"\nLoading messages from: {INPUT_FILE}")
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        print("Warning: UTF-8 decoding failed, trying with latin-1 encoding...")
        with open(INPUT_FILE, 'r', encoding='latin-1') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"ERROR: Could not read file: {e}")
        sys.exit(1)
    
    # Handle empty file
    if not lines:
        print("WARNING: Input file is empty. Nothing to process.")
        sys.exit(0)
    
    total_lines = len(lines)
    print(f"Found {total_lines} messages to process\n")
    print("-" * 60)
    
    # Progress tracking
    success_count = 0
    skip_count = 0
    error_count = 0
    
    try:
        # Process each line
        for i, line in enumerate(lines, 1):
            text = line.strip()
            
            # Skip empty lines
            if not text:
                skip_count += 1
                continue
            
            print(f"[{i}/{total_lines}] Processing: {text[:50]}{'...' if len(text) > 50 else ''}")
            
            result, error = message_classification(text)
            
            if result is None:
                error_count += 1
                print(f"          ERROR: {error}")
                continue
            
            print(f"          Result: {result}")
            
            try:
                read_text_file(result, separator='|', columns=['District', 'Intent', 'Priority'], output_file=OUTPUT_FILE)
                success_count += 1
            except Exception as e:
                error_count += 1
                print(f"          ERROR saving result: {e}")
    
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("INTERRUPTED BY USER (Ctrl+C)")
        print("=" * 60)
        print(f"Partial results saved to: {OUTPUT_FILE}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("PROCESSING COMPLETE")
    print("=" * 60)
    print(f"  Total messages:    {total_lines}")
    print(f"  Successfully processed: {success_count}")
    print(f"  Skipped (empty):   {skip_count}")
    print(f"  Errors:            {error_count}")
    print(f"\n  Output saved to: {OUTPUT_FILE}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()