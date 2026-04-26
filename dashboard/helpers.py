import pandas as pd

def dataset_info(df):
    summary_data = []
    
    for col in df.columns:
        summary_data.append({
            'Column': col,
            'Type': df[col].dtype,
            'Unique Values': df[col].nunique(),
            '# Nulls': df[col].isnull().sum(),
            '% Nulls': round((df[col].isnull().sum() / len(df)) * 100,2)
        })
    
    # Returning a DataFrame makes it much easier to read!
    return pd.DataFrame(summary_data)

    