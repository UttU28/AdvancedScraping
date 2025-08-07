import pandas as pd
import json

with open('aa.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

df = pd.DataFrame(data)

df.rename(columns={
    'providerName': 'Provider',
    'name': 'Name',
    'fullAddress': 'Address',
    'location': 'Location',
}, inplace=True)

sorted_df = df.sort_values(by='Provider')

grouped = []
for provider, group in sorted_df.groupby('Provider'):
    grouped.append(group)
    grouped.append(pd.DataFrame([['', '', '', '']], columns=group.columns))

final_df = pd.concat(grouped, ignore_index=True)

output_file = 'DataCentres Surrounding.xlsx'
with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    final_df.to_excel(writer, index=False, sheet_name='Data Centers')
    worksheet = writer.sheets['Data Centers']

print(f"Data successfully sorted and written to {output_file}.")
