"""
Chain-of-Thought Reasoning for Crisis Scenarios

This script reads crisis scenarios from a text file and analyzes them using
Chain-of-Thought reasoning with temperature stress testing.

Input: ../../data/Scenarios.txt
Output: ../../data/cot_results.txt
"""

import sys
import os
import time
sys.path.append("../..")

from utils.prompts import render
from utils.llm_client import LLMClient
from utils.router import pick_model

# Configuration
SCENARIOS_FILE = "../data/Scenarios.txt"
OUTPUT_FILE = "../output/cot_results.txt"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def call_with_retry(client, messages, temperature, max_tokens):
    """Call LLM with retry logic for None responses."""
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat(messages, temperature=temperature, max_tokens=max_tokens)
            if response.get('text') is not None:
                return response
            print(f"    [Retry {attempt + 1}/{MAX_RETRIES}] Got None response, retrying...")
            time.sleep(RETRY_DELAY)
        except Exception as e:
            print(f"    [Retry {attempt + 1}/{MAX_RETRIES}] API error: {str(e)[:50]}...")
            time.sleep(RETRY_DELAY)
    return response  # Return last response even if None


def ensure_output_directory(output_path):
    """Create output directory if it doesn't exist."""
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")


def parse_scenarios(file_path):
    """Parse scenarios from file with proper error handling."""
    scenarios = []
    current_scenario = []
    
    for line in open(file_path, 'r', encoding='utf-8'):
        if line.startswith("SCENARIO"):
            if current_scenario:
                scenarios.append("".join(current_scenario))
            current_scenario = [line]
        else:
            current_scenario.append(line)
    
    # Don't forget the last scenario
    if current_scenario:
        scenarios.append("".join(current_scenario))
    
    return scenarios


def main():
    """Main function with comprehensive error handling."""
    
    print("\n" + "=" * 60)
    print("CHAIN-OF-THOUGHT SCENARIO ANALYSIS")
    print("=" * 60)
    
    # Check if input file exists
    if not os.path.exists(SCENARIOS_FILE):
        print(f"\nERROR: Scenarios file not found: {SCENARIOS_FILE}")
        print("Please ensure the file exists and the path is correct.")
        sys.exit(1)
    
    # Ensure output directory exists
    ensure_output_directory(OUTPUT_FILE)
    
    # Initialize the LLM client
    print("\nInitializing reasoning model...")
    try:
        reasoning_model = pick_model('google', 'cot')
        client_reasoning = LLMClient('google', reasoning_model)
        print(f"Model loaded: {reasoning_model}")
    except Exception as e:
        print(f"ERROR: Failed to initialize LLM client: {e}")
        sys.exit(1)
    
    # Parse scenarios
    print(f"\nLoading scenarios from: {SCENARIOS_FILE}")
    try:
        scenarios = parse_scenarios(SCENARIOS_FILE)
    except UnicodeDecodeError:
        print("Warning: UTF-8 decoding failed, trying with latin-1 encoding...")
        scenarios = parse_scenarios(SCENARIOS_FILE.replace('utf-8', 'latin-1'))
    except Exception as e:
        print(f"ERROR: Could not read scenarios file: {e}")
        sys.exit(1)
    
    # Handle empty scenarios
    if not scenarios:
        print("WARNING: No scenarios found in the file.")
        print("Ensure scenarios start with 'SCENARIO' keyword.")
        sys.exit(0)
    
    print(f"Found {len(scenarios)} scenarios to process\n")
    
    # Progress tracking
    success_count = 0
    error_count = 0
    
    try:
        # Open output file for writing
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as out_f:
            
            def write_output(text):
                """Helper to print and write to file"""
                print(text)
                out_f.write(text + "\n")
            
            # Header
            write_output("=" * 80)
            write_output("CHAIN-OF-THOUGHT REASONING RESULTS")
            write_output("=" * 80)
            write_output("")
            
            for scenario_num, problem in enumerate(scenarios, 1):
                # Scenario header
                write_output("-" * 80)
                write_output(f"PROBLEM {scenario_num} of {len(scenarios)}")
                write_output("-" * 80)
                write_output(problem.strip())
                write_output("")
                
                prompt_text, spec = render(
                    'cot_reasoning.v1',
                    role='damage controlling officer',
                    problem=problem
                )

                instruction = """
                Identify the immediate life threat, immediate health threat, and any other critical issues. Then provide a plan to address them.
                """

                full_prompt = f"""text: {prompt_text}

                instruction: {instruction}"""

                messages = [{'role': 'user', 'content': full_prompt}]

                # Temperature 1 tests
                write_output("")
                write_output(f"{'─' * 40}")
                write_output(f"TEMPERATURE 1 STRESS TEST (Problem {scenario_num})")
                write_output(f"{'─' * 40}")
                
                for run in range(3):
                    print(f"  Running temperature=1 test {run + 1}/3...")
                    response = call_with_retry(client_reasoning, messages, temperature=1, max_tokens=spec.max_tokens)
                    
                    result_text = response.get('text') if response else None
                    
                    write_output("")
                    write_output(f"► Run {run + 1}:")
                    
                    if result_text is None:
                        write_output("[ERROR: No response received from LLM]")
                        error_count += 1
                    else:
                        write_output(result_text)
                        success_count += 1
                    
                    write_output("")

                # Temperature 0 test
                write_output(f"{'─' * 40}")
                write_output(f"TEMPERATURE 0 TEST (Problem {scenario_num})")
                write_output(f"{'─' * 40}")
                
                print(f"  Running temperature=0 deterministic test...")
                response = call_with_retry(client_reasoning, messages, temperature=0, max_tokens=spec.max_tokens)
                
                result_text = response.get('text') if response else None
                
                write_output("")
                write_output(f"► Deterministic Run:")
                
                if result_text is None:
                    write_output("[ERROR: No response received from LLM]")
                    error_count += 1
                else:
                    write_output(result_text)
                    success_count += 1
                
                write_output("")
                
            # Footer
            write_output("=" * 80)
            write_output("END OF RESULTS")
            write_output("=" * 80)
    
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("INTERRUPTED BY USER (Ctrl+C)")
        print("=" * 60)
        print(f"Partial results saved to: {OUTPUT_FILE}")
    
    except Exception as e:
        print(f"\nERROR during processing: {e}")
        error_count += 1
    
    # Print summary
    print("\n" + "=" * 60)
    print("PROCESSING COMPLETE")
    print("=" * 60)
    print(f"  Scenarios processed: {len(scenarios)}")
    print(f"  Successful LLM calls: {success_count}")
    print(f"  Failed LLM calls:     {error_count}")
    print(f"\n  Results saved to: {OUTPUT_FILE}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()


"""
================================================================================
TEMPERATURE COMPARISON ANALYSIS: Safe Mode (Temp 0.0) vs Chaos Mode (Temp 1.0)
================================================================================

In terms of Consistency, Safe Mode (Temp 0.0) is highly structured and follows a rigid 
hierarchy of needs (Life > Health > Welfare). In contrast, Chaos Mode (Temp 1.0) is 
variable—while the core logic remains sound, the "flavor" and specific action steps 
shift between runs.

Regarding Drift and Hallucination, Safe Mode focuses strictly on provided facts such as 
blocked roads, rising water, and medical status. Chaos Mode exhibits minor drift: Run 1 
suggested "Air Rescue" or "Amphibious Task Force," while Run 3 suggested "Medical supply 
drops." These are logical leaps not explicitly requested in the original scenario.

For Detail Sensitivity, Safe Mode is very literal—it addresses the "2-hour battery" vs. 
"30-minute generator" as a mathematical safety margin. Chaos Mode demonstrates creative 
problem solving: Run 1 (Scenario A) suggested the uncle use a "belt or cloth to lash 
himself to the tree"—a creative detail not found in the Safe output.
================================================================================
"""
