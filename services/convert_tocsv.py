import pandas as pd 
import json

def convert_to_csv(json_file: str, csv_file: str):
    with open(json_file, 'r') as file:
        data = json.load(file)
    
    # Normalize the JSON data and convert it to a DataFrame
    df = pd.json_normalize(data, sep='_')
    
    # Save the DataFrame to a CSV file
    df.to_csv(csv_file, index=False)
    print(f"CSV data saved to {csv_file}")
