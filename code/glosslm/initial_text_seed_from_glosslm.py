import pandas as pd
import numpy as np

def get_closest_to_median(group):
    # Ensure all values in 'transcription' are strings and handle NaN values
    group['transcription'] = group['transcription'].astype(str).fillna('')
    # Calculate the string lengths
    group['str_length'] = group['transcription'].apply(len)
    # Calculate the median string length
    median_length = group['str_length'].median()
    # Calculate the absolute difference from the median
    group['diff_from_median'] = (group['str_length'] - median_length).abs()
    # Sort by the difference and take the two rows closest to the median
    closest_rows = group.nsmallest(2, 'diff_from_median')
    return closest_rows

df = pd.read_csv('glosslm_train_with_iso.csv')
# Apply the function to each group
result = df.groupby('iso_code').apply(get_closest_to_median).reset_index(drop=True)

# Drop the temporary columns used for calculation
result = result.drop(columns=['str_length', 'diff_from_median'])

glosslm_samples = result[['iso_code','transcription']]

glosslm_samples.to_csv('glosslm_samples.txt', sep='\t', index=False, header=False)
