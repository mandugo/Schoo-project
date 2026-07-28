import pandas as pd


# File esistente
file_input = "data/scuole_coordinate.csv"


# Legge il file
df = pd.read_csv(
    file_input,
    encoding="utf-8"
)



def assegna_grado(riga):

    codice = str(riga["Codice"]).upper()
    nome = str(riga["Nome"]).upper()


    # Infanzia
    if codice.startswith("TOAA"):
        return "Infanzia"


    # Primaria
    if codice.startswith("TOEE"):
        return "Primaria"


    # Secondaria di primo grado
    if codice.startswith("TOMM"):
        return "Secondaria di primo grado"


    # Istituti comprensivi
    if (
        "ISTITUTO COMPRENSIVO" in nome
        or "I.C." in nome
        or "IC " in nome
    ):
        return "Istituti comprensivi"


    # Tutto ciò che rimane
    return "Secondaria di secondo grado"



# Aggiunge la colonna Grado

df["Grado"] = df.apply(
    assegna_grado,
    axis=1
)



# Ordine finale colonne

df = df[
    [
        "Distretto",
        "Codice",
        "Nome",
        "Indirizzo",
        "Grado",
        "Latitudine",
        "Longitudine"
    ]
]



# Sovrascrive il file

df.to_csv(
    file_input,
    index=False,
    encoding="utf-8"
)



print("Aggiornamento completato!")
print()

print(df["Grado"].value_counts())