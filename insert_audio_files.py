import pandas as pd

df = pd.read_csv('audio_files.csv')  # Replace with actual file path

def sql_escape(value):
    if pd.isnull(value):
        return 'NULL'
    if isinstance(value, str):
        value = value.replace("'", "''")
        return f"'{value}'"
    return str(value)

rows = []
for _, row in df.iterrows():
    values = [sql_escape(row[col]) for col in df.columns]
    row_str = f"({', '.join(values)})"
    rows.append(row_str)

insert_statement = f"INSERT INTO audio_files ({', '.join(df.columns)}) VALUES\n" + ",\n".join(rows) + ";"
print(insert_statement)
