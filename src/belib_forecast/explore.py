import requests
import pandas as pd

URL = (
    "https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/"
    "belib-points-de-recharge-pour-vehicules-electriques-disponibilite-temps-reel/"
    "exports/json"
)

response = requests.get(URL, timeout=60)
response.raise_for_status()
records = response.json()

df = pd.DataFrame(records)

print(f"Nombre de points de recharge : {len(df)}\n")
print("Colonnes :", list(df.columns), "\n")
print("Exemple d'une ligne :")
print(df.iloc[0].to_dict(), "\n")

# repérer automatiquement la colonne de statut
status_cols = [c for c in df.columns if "statut" in c.lower() or "status" in c.lower()]
for col in status_cols:
    print(f"Valeurs de '{col}' :")
    print(df[col].value_counts(), "\n")