"""
Crisis Event Pipeline

This script processes news feed text files to extract and validate
structured crisis event data using Pydantic models and LLM extraction.

Input: ../../data/News Feed.txt
Output: output/flood_report.xlsx
"""

import sys
import os
import time
import logging
import pandas as pd
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, Literal

from extract_json import extract_json

# Configuration
INPUT_FILE = '../data/News Feed.txt'
OUTPUT_FILE = '../output/flood_report.xlsx'
API_DELAY = 6  # seconds between API calls (rate limiting)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class CrisisEvent(BaseModel):
    """Pydantic model for validating crisis event data."""
    
    district: Literal[
        "Ampara", "Anuradhapura", "Badulla", "Batticaloa", "Colombo", 
        "Galle", "Gampaha", "Hambantota", "Jaffna", "Kalutara", 
        "Kandy", "Kegalle", "Kilinochchi", "Kurunegala", "Mannar", 
        "Matale", "Matara", "Monaragala", "Mullaitivu", "Nuwara Eliya", 
        "Polonnaruwa", "Puttalam", "Ratnapura", "Trincomalee", "Vavuniya"
    ]

    flood_level_meters: Optional[float] = None
    victim_count: Optional[int] = Field(default=0, alias="vicLm_count")
    main_need: Optional[str] = Field(default="None")
    status: Literal["Critical", "Warning", "Stable"]


def ensure_output_directory(output_path):
    """Create output directory if it doesn't exist."""
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")


def run_pipeline(input_file: str, output_file: str):
    """Run the crisis event extraction pipeline with comprehensive error handling."""
    
    print("\n" + "=" * 60)
    print("CRISIS EVENT EXTRACTION PIPELINE")
    print("=" * 60)
    
    # Check input file exists
    if not os.path.exists(input_file):
        print(f"\nERROR: Input file not found: {input_file}")
        print("Please ensure the file exists and the path is correct.")
        return False
    
    # Ensure output directory exists
    ensure_output_directory(output_file)
    
    valid_events = []
    total_lines = 0
    success_count = 0
    validation_errors = 0
    processing_errors = 0

    try:
        # Count total lines first
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
            total_lines = len(lines)
        
        if total_lines == 0:
            print("WARNING: Input file is empty.")
            return False
        
        print(f"\nProcessing {total_lines} news items...")
        print("-" * 60)
        
        for i, clean_line in enumerate(lines, 1):
            print(f"\n[{i}/{total_lines}] Processing: {clean_line[:50]}{'...' if len(clean_line) > 50 else ''}")
            
            try:
                # Extract JSON from text
                print("    Extracting structured data...")
                clean_json = extract_json(clean_line)
                
                if clean_json is None:
                    print("    WARNING: No JSON extracted")
                    processing_errors += 1
                    continue
                
                # Validate with Pydantic
                print("    Validating...")
                event = CrisisEvent.model_validate_json(clean_json)
                valid_events.append(event.model_dump())
                success_count += 1
                print(f"    SUCCESS: {event.district} - {event.status}")
                
                # Rate limiting
                if i < total_lines:
                    print(f"    Waiting {API_DELAY}s (rate limiting)...")
                    time.sleep(API_DELAY)
            
            except ValidationError as e:
                validation_errors += 1
                error_details = e.errors()[0] if e.errors() else {}
                field = error_details.get('loc', ['unknown'])[0]
                msg = error_details.get('msg', 'Unknown error')
                print(f"    VALIDATION ERROR: {field} - {msg}")
                logging.warning(f"Line {i} failed validation: {e.json()}")
                
            except RuntimeError as e:
                processing_errors += 1
                print(f"    PROCESSING ERROR: {e}")
                logging.warning(f"Line {i} could not be processed: {e}")
                
            except Exception as e:
                processing_errors += 1
                print(f"    UNEXPECTED ERROR: {e}")
                logging.warning(f"Line {i} failed: {e}")

        # Save results
        print("\n" + "-" * 60)
        print("SAVING RESULTS")
        print("-" * 60)
        
        if valid_events:
            df = pd.DataFrame(valid_events)
            
            # Check if openpyxl is available for Excel
            try:
                df.to_excel(output_file, index=False)
                print(f"SUCCESS! Report saved to: {output_file}")
            except ModuleNotFoundError:
                # Fallback to CSV if openpyxl not installed
                csv_file = output_file.replace('.xlsx', '.csv')
                df.to_csv(csv_file, index=False)
                print(f"Note: openpyxl not installed, saved as CSV: {csv_file}")
        else:
            print("WARNING: No valid events found to save.")

    except FileNotFoundError:
        print(f"ERROR: The file {input_file} was not found.")
        return False
        
    except UnicodeDecodeError:
        print("ERROR: File encoding issue. Try converting to UTF-8.")
        return False
        
    except KeyboardInterrupt:
        print("\n\nINTERRUPTED BY USER (Ctrl+C)")
        if valid_events:
            print(f"Saving {len(valid_events)} events collected so far...")
            df = pd.DataFrame(valid_events)
            df.to_excel(output_file.replace('.xlsx', '_partial.xlsx'), index=False)
            print(f"Partial results saved.")
        return False
        
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}")
        logging.exception("Pipeline failed")
        return False
    
    # Print summary
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"  Total items processed: {total_lines}")
    print(f"  Successfully extracted: {success_count}")
    print(f"  Validation errors:     {validation_errors}")
    print(f"  Processing errors:     {processing_errors}")
    print("=" * 60 + "\n")
    
    return True


if __name__ == "__main__":
    run_pipeline(INPUT_FILE, OUTPUT_FILE)
