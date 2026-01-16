import pandas as pd
import os

def read_text_file(string, separator='|', columns=None, output_file=None, has_header=False):
    """
    Parse a string, list of strings, or text file with either:
    - key: value pairs (e.g., "District: Matale | Intent: Rescue")
    - table-style data (e.g., "ID | Time | Area" with has_header=True)
    
    Args:
        string: Can be a single string, list of strings, or path to a text file
        separator: Delimiter between columns/key:value pairs (default: '|')
        columns: Optional column names (auto-extracted from keys or header if not provided)
        output_file: Optional path to save as CSV or Excel file
        has_header: If True, treats first line as column headers and rest as data values
    
    Example:
        Key-value: read_text_file("District: Matale | Intent: Rescue")
        Table:     read_text_file("data.txt", has_header=True)
    """
    # Handle None or empty input
    if string is None or string == '':
        return pd.DataFrame(columns=columns if columns else [])
    
    # Check if input is a file path
    if isinstance(string, str) and os.path.isfile(string):
        with open(string, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
    # Handle single string input by wrapping in a list
    elif isinstance(string, str):
        lines = [string]
    else:
        lines = string
    
    if not lines:
        return pd.DataFrame(columns=columns if columns else [])
    
    # Table-style parsing (first line = headers, rest = data)
    if has_header:
        # Extract columns from first line if not provided
        if columns is None:
            columns = [col.strip() for col in lines[0].split(separator)]
        
        # Parse data lines (skip header)
        data = []
        for line in lines[1:]:
            values = [val.strip() for val in line.split(separator)]
            row = dict(zip(columns, values))
            data.append(row)
        
        df = pd.DataFrame(data, columns=columns)
    else:
        # Key-value pair parsing (original behavior)
        data = []
        extracted_columns = None
        
        for line in lines:
            parts = [part.strip() for part in line.strip().split(separator)]
            row = {}
            for part in parts:
                if ':' in part:
                    key, value = part.split(':', 1)
                    row[key.strip()] = value.strip()
                else:
                    # If no colon, use the part as-is (fallback)
                    row[part] = part
            
            # Extract column names from the first row if not provided
            if extracted_columns is None:
                extracted_columns = list(row.keys())
            
            data.append(row)
        
        # Use provided columns or extracted columns
        final_columns = columns if columns else extracted_columns
        df = pd.DataFrame(data, columns=final_columns)
    
    if output_file:
        # Create parent directories if they don't exist
        parent_dir = os.path.dirname(output_file)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
        
        file_exists = os.path.exists(output_file)
        _, ext = os.path.splitext(output_file)
        
        if ext.lower() in ['.xlsx', '.xls']:
            # Excel file - need to read existing, concat, and rewrite
            if file_exists:
                existing_df = pd.read_excel(output_file)
                df = pd.concat([existing_df, df], ignore_index=True)
            df.to_excel(output_file, index=False)
        else:
            # CSV file - can append directly
            df.to_csv(output_file, mode='a', index=False, header=not file_exists)
    return df


