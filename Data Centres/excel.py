import pandas as pd
import json

with open('m.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

df = pd.DataFrame(data)

df.rename(columns={
    'providerName': 'Provider',
    'name': 'Name',
    'fullAddress': 'Address',
    'location': 'Location',
    'url': 'URL',
    'phone': 'Phone'
}, inplace=True)

df['URL'] = df['URL'].apply(lambda x: f"https://www.datacenters.com{x}")

sorted_df = df.sort_values(by='Provider')

grouped = []
for provider, group in sorted_df.groupby('Provider'):
    grouped.append(group)
    grouped.append(pd.DataFrame([['', '', '', '', '', '']], columns=group.columns))

final_df = pd.concat(grouped, ignore_index=True)

output_file = 'DataCentres.xlsx'
with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    final_df.to_excel(writer, index=False, sheet_name='Data Centers')
    worksheet = writer.sheets['Data Centers']
    for idx, cell in enumerate(final_df['URL'], start=2):
        if cell:
            worksheet.cell(row=idx, column=5).hyperlink = cell

print(f"Data successfully sorted and written to {output_file}.")
