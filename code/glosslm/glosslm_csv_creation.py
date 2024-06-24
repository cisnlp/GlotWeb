from datasets import load_dataset
import pandas as pd

dataset = load_dataset("lecslab/glosslm-corpus-split")
df_train = pd.DataFrame(dataset['train'])

# Save the DataFrame as a CSV file
df_train.to_csv('glosslm-corpus-split.csv', index=False)
