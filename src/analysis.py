"""
analysis.py — les calculs de l'étude sur la sous-nutrition dans le monde (données FAO).

Unités des fichiers (à bien garder en tête, c'est la principale source d'erreurs) :
  - population.csv          : Valeur en MILLIERS d'habitants
  - sous_nutrition.csv      : Valeur en MILLIONS de personnes, par période de 3 ans
                              ("<0.1" = moins de 100 000 personnes, valeur non chiffrée)
  - dispo_alimentaire.csv   : kcal/personne/jour, et quantités en MILLIERS de tonnes
  - aide_alimentaire.csv    : Valeur en TONNES

Convention : l'année 2017 correspond à la période "2016-2018" (moyenne sur 3 ans centrée sur 2017).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
YEAR = 2017
PERIOD = "2016-2018"
KCAL_NEED = 2500  # besoin énergétique moyen retenu (kcal/personne/jour), hypothèse ajustable

KCAL_COL = "Disponibilité alimentaire (Kcal/personne/jour)"
USES = {
    "Nourriture": "Alimentation humaine",
    "Traitement": "Transformation (huiles, sucre, boissons…)",
    "Aliments pour animaux": "Alimentation animale",
    "Autres Utilisations": "Autres utilisations",
    "Pertes": "Pertes",
    "Semences": "Semences",
}


# ─────────────────────────────────────────────────────────────
# Chargement
# ─────────────────────────────────────────────────────────────
@dataclass
class Data:
    population: pd.DataFrame
    dispo: pd.DataFrame
    sous_nutrition: pd.DataFrame
    aide: pd.DataFrame


def load_data(data_dir: Path = DATA_DIR) -> Data:
    sn = pd.read_csv(data_dir / "sous_nutrition.csv")
    # "<0.1" n'est pas un nombre : on le garde à part (colonne non_chiffre) et on met NaN dans Valeur
    sn["non_chiffre"] = sn["Valeur"].astype(str).str.startswith("<")
    sn["Valeur"] = pd.to_numeric(sn["Valeur"], errors="coerce")
    return Data(
        population=pd.read_csv(data_dir / "population.csv"),
        dispo=pd.read_csv(data_dir / "dispo_alimentaire.csv"),
        sous_nutrition=sn,
        aide=pd.read_csv(data_dir / "aide_alimentaire.csv").rename(columns={"Pays bénéficiaire": "Zone"}),
    )


def population_2017(d: Data) -> pd.Series:
    """Population 2017 par pays, en nombre d'habitants."""
    pop = d.population[d.population["Année"] == YEAR].set_index("Zone")["Valeur"]
    return pop * 1_000


def undernourished_2017(d: Data) -> pd.Series:
    """Nombre de personnes sous-alimentées par pays (période 2016-2018), en personnes. Sans les "<0.1"."""
    sn = d.sous_nutrition[d.sous_nutrition["Année"] == PERIOD].set_index("Zone")["Valeur"]
    return (sn * 1_000_000).dropna()


# ─────────────────────────────────────────────────────────────
# Question 1 — proportion de personnes sous-alimentées
# ─────────────────────────────────────────────────────────────
def q1_proportion(d: Data) -> dict:
    pop = population_2017(d)
    under = undernourished_2017(d)
    sn = d.sous_nutrition[d.sous_nutrition["Année"] == PERIOD]
    return {
        "sous_alimentes": under.sum(),
        "population_mondiale": pop.sum(),
        "proportion": under.sum() / pop.sum(),
        "pays_chiffres": int(sn["Valeur"].notna().sum()),
        "pays_moins_de_100k": int(sn["non_chiffre"].sum()),
        "pays_sans_donnee": int((sn["Valeur"].isna() & ~sn["non_chiffre"]).sum()),
    }


# ─────────────────────────────────────────────────────────────
# Questions 2 et 3 — nombre théorique de personnes nourries
# ─────────────────────────────────────────────────────────────
def kcal_per_country(d: Data, origin: str | None = None) -> pd.Series:
    """Disponibilité alimentaire par pays en kcal/personne/jour (tous produits, ou une origine)."""
    df = d.dispo if origin is None else d.dispo[d.dispo["Origine"] == origin]
    return df.groupby("Zone")[KCAL_COL].sum()


def people_fed(d: Data, origin: str | None = None, kcal_need: float = KCAL_NEED) -> dict:
    """
    Calories disponibles chaque jour dans le monde = Σ (kcal/pers/jour du pays × population du pays).
    Divisées par le besoin d'une personne → nombre de personnes qui pourraient être nourries.
    """
    kcal = kcal_per_country(d, origin)
    pop = population_2017(d)
    joined = pd.concat([kcal.rename("kcal"), pop.rename("pop")], axis=1, join="inner")
    total_kcal = (joined["kcal"] * joined["pop"]).sum()
    fed = total_kcal / kcal_need
    return {
        "personnes_nourries": fed,
        "part_population": fed / pop.sum(),
        "pays_utilises": len(joined),
        "kcal_besoin": kcal_need,
    }


# ─────────────────────────────────────────────────────────────
# Question 4 — utilisation de la disponibilité intérieure
# ─────────────────────────────────────────────────────────────
def q4_uses(d: Data) -> pd.DataFrame:
    total = d.dispo["Disponibilité intérieure"].sum()
    rows = [(label, d.dispo[col].sum(), d.dispo[col].sum() / total) for col, label in USES.items()]
    out = pd.DataFrame(rows, columns=["Utilisation", "Milliers de tonnes", "Part"])
    return out.sort_values("Part", ascending=False).reset_index(drop=True)


def q4_cereals(d: Data) -> pd.DataFrame:
    """Zoom céréales : quelle part va aux animaux plutôt qu'aux humains ?"""
    cereals = ["Blé", "Riz (Eq Blanchi)", "Orge", "Maïs", "Seigle", "Avoine", "Millet", "Sorgho", "Céréales, Autres"]
    c = d.dispo[d.dispo["Produit"].isin(cereals)]
    total = c["Disponibilité intérieure"].sum()
    return pd.DataFrame(
        {
            "Utilisation": ["Alimentation humaine", "Alimentation animale"],
            "Part": [c["Nourriture"].sum() / total, c["Aliments pour animaux"].sum() / total],
        }
    )


# ─────────────────────────────────────────────────────────────
# Questions 5 à 7 — classements de pays
# ─────────────────────────────────────────────────────────────
def q5_highest_proportion(d: Data, n: int = 10) -> pd.DataFrame:
    """Pays où la proportion de sous-alimentés est la plus forte en 2017 (valeurs chiffrées uniquement)."""
    under = undernourished_2017(d)
    pop = population_2017(d)
    df = pd.concat([under.rename("sous_alimentes"), pop.rename("population")], axis=1, join="inner")
    df["proportion"] = df["sous_alimentes"] / df["population"]
    return df.sort_values("proportion", ascending=False).head(n).reset_index(names="Zone")


def q6_most_aid(d: Data, n: int = 10) -> pd.DataFrame:
    """Pays ayant reçu le plus d'aide alimentaire depuis 2013 (en tonnes)."""
    total = d.aide.groupby("Zone")["Valeur"].sum().sort_values(ascending=False)
    df = total.head(n).rename("tonnes").reset_index()
    df["part_aide_totale"] = df["tonnes"] / total.sum()
    return df


def aid_by_year(d: Data) -> pd.DataFrame:
    return d.aide.groupby("Année")["Valeur"].sum().rename("tonnes").reset_index()


def aid_by_product(d: Data) -> pd.DataFrame:
    return d.aide.groupby("Produit")["Valeur"].sum().sort_values(ascending=False).rename("tonnes").reset_index()


def q7_availability(d: Data, n: int = 10) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pays ayant le plus et le moins de disponibilité alimentaire par habitant (kcal/personne/jour)."""
    kcal = kcal_per_country(d).rename("kcal").reset_index()
    return (
        kcal.sort_values("kcal", ascending=False).head(n).reset_index(drop=True),
        kcal.sort_values("kcal").head(n).reset_index(drop=True),
    )


def availability_vs_undernourishment(d: Data) -> pd.DataFrame:
    """Pour chaque pays : kcal disponibles par habitant et proportion de sous-alimentés (relation à visualiser)."""
    under = undernourished_2017(d)
    pop = population_2017(d)
    kcal = kcal_per_country(d)
    df = pd.concat([kcal.rename("kcal"), under.rename("sous_alimentes"), pop.rename("population")], axis=1, join="inner")
    df["proportion"] = df["sous_alimentes"] / df["population"]
    return df.reset_index(names="Zone")


# ─────────────────────────────────────────────────────────────
# Mise en forme
# ─────────────────────────────────────────────────────────────
def fr(x: float, decimals: int = 1) -> str:
    """Nombre au format français : 1 234,5."""
    return f"{x:,.{decimals}f}".replace(",", " ").replace(".", ",")


def pct(x: float, decimals: int = 1) -> str:
    return f"{fr(x * 100, decimals)} %"


def billions(x: float) -> str:
    return f"{fr(x / 1e9, 2)} milliards"
