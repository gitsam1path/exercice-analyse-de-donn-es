"""
Tableau de bord Streamlit — la sous-nutrition dans le monde (données FAO).
Lancer :  streamlit run app.py
Les calculs sont dans src/analysis.py ; ce fichier ne fait que l'affichage.
"""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import analysis as an
from src.analysis import fr, pct

st.set_page_config(page_title="Sous-nutrition dans le monde", page_icon="🌍", layout="wide")

GREEN, RED, BLUE, GREY, ORANGE = "#3d9970", "#d1495b", "#2e86ab", "#9aa0a6", "#edae49"
LAYOUT = dict(template="plotly_white", margin=dict(l=10, r=10, t=50, b=10), font=dict(size=13))

st.markdown(
    """
    <style>
      .block-container { padding-top: 2rem; max-width: 1200px; }
      .hero { padding: 1.6rem 1.8rem; border-radius: 16px; color: #fff;
              background: linear-gradient(120deg, #0f3d3e 0%, #1f7a5c 55%, #3d9970 100%); }
      .hero h1 { margin: 0 0 .4rem; font-size: 2.1rem; }
      .hero p { margin: 0; opacity: .93; font-size: 1.05rem; }
      .answer { border-left: 4px solid #1f7a5c; background: #eef7f2; padding: .8rem 1rem;
                border-radius: 0 8px 8px 0; margin: .4rem 0 1rem; }
      div[data-testid="stMetricValue"] { font-size: 1.7rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def answer(text: str):
    st.markdown(f'<div class="answer">{text}</div>', unsafe_allow_html=True)


def hbar(df, x, y, color, title, text, xaxis):
    fig = px.bar(df, x=x, y=y, orientation="h", text=text, title=title)
    fig.update_traces(marker_color=color, textposition="outside", cliponaxis=False)
    fig.update_layout(**LAYOUT, yaxis=dict(autorange="reversed", title=""), xaxis_title=xaxis,
                      height=60 + 38 * len(df))
    return fig


@st.cache_data
def load():
    return an.load_data()


d = load()

with st.sidebar:
    st.markdown("## 🌍 Sous-nutrition")
    st.caption("Analyse de données FAO · 2013-2017")
    need = st.slider("Besoin énergétique d'une personne (kcal/jour)", 1800, 3000, an.KCAL_NEED, step=50,
                     help="Hypothèse utilisée pour les questions 2 et 3.")
    st.divider()
    st.markdown("**Auteur** : Elie Samson Kombiwo")
    st.markdown("[Code source sur GitHub](https://github.com/gitsam1path/exercice-analyse-de-donn-es)")

q1 = an.q1_proportion(d)
fed = an.people_fed(d, kcal_need=need)
veg = an.people_fed(d, "vegetale", kcal_need=need)
uses = an.q4_uses(d)

st.markdown(
    """
    <div class="hero">
      <h1>🌍 La sous-nutrition dans le monde</h1>
      <p>Produit-on assez de nourriture pour nourrir tout le monde ? Et où sont les personnes qui ont faim ?
         Sept questions, quatre jeux de données de la FAO.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.write("")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Sous-alimentés en 2017", f"{fr(q1['sous_alimentes'] / 1e6, 0)} M", pct(q1["proportion"]) + " de la population",
          delta_color="off")
k2.metric("Personnes qui pourraient être nourries", f"{fr(fed['personnes_nourries'] / 1e9, 2)} Md",
          f"{pct(fed['part_population'], 0)} de la population", delta_color="normal")
k3.metric("Part de la nourriture donnée aux animaux", pct(uses.set_index("Utilisation").loc["Alimentation animale", "Part"]))
most, least = an.q7_availability(d)
k4.metric("Écart de disponibilité entre pays", f"× {fr(most.iloc[0]['kcal'] / least.iloc[0]['kcal'], 1)}",
          f"{fr(most.iloc[0]['kcal'], 0)} vs {fr(least.iloc[0]['kcal'], 0)} kcal/jour", delta_color="off")

t1, t2, t3, t4, t5 = st.tabs(
    ["1 · Combien ont faim ?", "2-3 · Assez pour tous ?", "4 · Où va la nourriture ?", "5-7 · Quels pays ?", "✅ Conclusion"]
)

# ── Q1 ────────────────────────────────────────────────────────
with t1:
    st.subheader("Q1 · Proportion de personnes sous-alimentées en 2017")
    answer(
        f"<b>{pct(q1['proportion'])}</b> de la population mondiale, soit <b>{fr(q1['sous_alimentes'] / 1e6, 1)} millions</b> "
        f"de personnes sur {an.billions(q1['population_mondiale'])}, était en état de sous-nutrition en 2017."
    )
    c1, c2 = st.columns([2, 3])
    fig = go.Figure(go.Pie(labels=["Sous-alimentés", "Reste de la population"],
                           values=[q1["sous_alimentes"], q1["population_mondiale"] - q1["sous_alimentes"]],
                           hole=0.62, marker_colors=[RED, "#e8ecef"], sort=False, textinfo="percent"))
    fig.update_layout(**LAYOUT, height=330, showlegend=True, legend=dict(orientation="h", y=-0.1),
                      annotations=[dict(text=f"<b>{fr(q1['sous_alimentes'] / 1e6, 0)} M</b>", x=0.5, y=0.5, showarrow=False, font_size=20)])
    c1.plotly_chart(fig, use_container_width=True)
    c2.markdown(
        f"""
**Méthode**
- 2017 correspond à la période **2016-2018** du fichier de sous-nutrition (moyenne sur 3 ans).
- Les valeurs sont en **millions** de personnes, la population en **milliers** : tout est converti en nombre de personnes.
- **{q1['pays_moins_de_100k']} pays** sont notés `<0.1` (moins de 100 000 personnes) et **{q1['pays_sans_donnee']}** n'ont pas de donnée.
  On ne les invente pas : le résultat est donc une **estimation basse**.

⚠️ La version initiale de l'exercice faisait la **moyenne** des valeurs par pays (6,3) : ce chiffre mélangeait
des millions de personnes et n'était pas une proportion.
        """
    )

# ── Q2-Q3 ─────────────────────────────────────────────────────
with t2:
    st.subheader("Q2-Q3 · Combien de personnes pourrait-on nourrir ?")
    answer(
        f"Avec un besoin de <b>{fr(need, 0)} kcal/jour</b>, la disponibilité alimentaire mondiale pourrait nourrir "
        f"<b>{an.billions(fed['personnes_nourries'])}</b> de personnes (<b>{pct(fed['part_population'], 0)}</b> de la population), "
        f"et les seuls produits végétaux <b>{an.billions(veg['personnes_nourries'])}</b> ({pct(veg['part_population'], 0)})."
    )
    labels = ["Population mondiale", "Nourries (tous produits)", "Nourries (végétal seul)"]
    vals = [q1["population_mondiale"] / 1e9, fed["personnes_nourries"] / 1e9, veg["personnes_nourries"] / 1e9]
    fig = go.Figure(go.Bar(x=vals, y=labels, orientation="h", marker_color=[GREY, GREEN, ORANGE],
                           text=[f"{fr(v, 2)} Md" for v in vals], textposition="outside", cliponaxis=False))
    fig.update_layout(**LAYOUT, height=260, yaxis=dict(autorange="reversed"), xaxis_title="Milliards de personnes",
                      title="Production disponible vs population")
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(
        """
**Méthode** : pour chaque pays, kcal/personne/jour (tous produits) × population → kcal disponibles chaque jour.
On additionne tous les pays, puis on divise par le besoin d'une personne. **Faites varier ce besoin dans la barre latérale** :
la production mondiale couvre toute la population tant que le besoin reste sous **≈ 2 770 kcal/jour**.

➜ **La faim n'est pas un problème de quantité produite, mais de répartition.**
        """
    )

# ── Q4 ────────────────────────────────────────────────────────
with t3:
    st.subheader("Q4 · Utilisation de la disponibilité intérieure")
    shares = uses.set_index("Utilisation")["Part"]
    answer(
        f"Seulement <b>{pct(shares['Alimentation humaine'])}</b> de la disponibilité intérieure sert directement à "
        f"l'alimentation humaine. <b>{pct(shares['Alimentation animale'])}</b> nourrit les animaux et "
        f"<b>{pct(shares['Pertes'])}</b> est perdue."
    )
    c1, c2 = st.columns([3, 2])
    colors = [GREEN if u == "Alimentation humaine" else RED if u in ("Alimentation animale", "Pertes") else GREY for u in uses["Utilisation"]]
    fig = hbar(uses.assign(pct=uses["Part"] * 100, label=uses["Part"].map(pct)), "pct", "Utilisation", colors,
               "Répartition de la disponibilité intérieure mondiale", "label", "%")
    fig.update_traces(marker_color=colors)
    c1.plotly_chart(fig, use_container_width=True)
    cer = an.q4_cereals(d).set_index("Utilisation")["Part"]
    fig = go.Figure(go.Pie(labels=["Humains", "Animaux", "Autres"],
                           values=[cer["Alimentation humaine"], cer["Alimentation animale"], 1 - cer.sum()],
                           hole=0.55, marker_colors=[GREEN, RED, GREY], sort=False))
    fig.update_layout(**LAYOUT, height=330, title="Zoom : les céréales")
    c2.plotly_chart(fig, use_container_width=True)
    st.caption("Unités : milliers de tonnes. « Transformation » = produits transformés en huiles, sucre, boissons, etc.")

# ── Q5-Q7 ─────────────────────────────────────────────────────
with t4:
    st.subheader("Q5 · Les pays où la proportion de sous-alimentés est la plus forte (2017)")
    top = an.q5_highest_proportion(d)
    answer(f"En <b>Haïti</b>, près d'une personne sur deux (<b>{pct(top.iloc[0]['proportion'], 0)}</b>) est sous-alimentée, "
           "suivie de la Corée du Nord et de Madagascar.")
    st.plotly_chart(hbar(top.assign(p=top["proportion"] * 100, label=top["proportion"].map(pct)), "p", "Zone", RED,
                         "Top 10 — % de la population sous-alimentée", "label", "%"), use_container_width=True)
    st.caption("Les pays notés « <0.1 » sont exclus : leur attribuer une valeur ferait apparaître à tort de très petits pays en tête.")

    st.subheader("Q6 · Les pays ayant reçu le plus d'aide alimentaire depuis 2013")
    aid = an.q6_most_aid(d)
    answer(f"La <b>Syrie</b> a reçu <b>{fr(aid.iloc[0]['tonnes'] / 1e6, 2)} million de tonnes</b>, soit "
           f"<b>{pct(aid.iloc[0]['part_aide_totale'], 0)}</b> de l'aide mondiale. Les 3 premiers pays en concentrent "
           f"{pct(aid['part_aide_totale'].head(3).sum(), 0)} : l'aide va surtout aux pays en guerre ou en crise.")
    c1, c2 = st.columns([3, 2])
    c1.plotly_chart(hbar(aid.assign(mt=aid["tonnes"] / 1e6, label=(aid["tonnes"] / 1e6).map(lambda x: fr(x, 2))), "mt", "Zone",
                         BLUE, "Top 10 des bénéficiaires (2013-2016)", "label", "Millions de tonnes"), use_container_width=True)
    year = an.aid_by_year(d)
    fig = px.bar(year, x=year["Année"].astype(str), y=year["tonnes"] / 1e6, title="Aide totale par année")
    fig.update_traces(marker_color=BLUE)
    fig.update_layout(**LAYOUT, height=440, xaxis_title="", yaxis_title="Millions de tonnes")
    c2.plotly_chart(fig, use_container_width=True)

    st.subheader("Q7 · Le plus et le moins de nourriture par habitant")
    answer(f"Un habitant de l'<b>Autriche</b> dispose de <b>{fr(most.iloc[0]['kcal'], 0)} kcal/jour</b>, deux fois plus "
           f"qu'un habitant de <b>République centrafricaine</b> ({fr(least.iloc[0]['kcal'], 0)} kcal/jour).")
    c1, c2 = st.columns(2)
    for col, df, color, title in [(c1, most, GREEN, "Le plus de kcal/personne/jour"), (c2, least, RED, "Le moins de kcal/personne/jour")]:
        fig = hbar(df.assign(label=df["kcal"].map(lambda k: fr(k, 0))), "kcal", "Zone", color, title, "label", "kcal/personne/jour")
        fig.add_vline(x=need, line_dash="dash", annotation_text=f"besoin {fr(need, 0)}")
        fig.update_xaxes(range=[0, 4300])
        col.plotly_chart(fig, use_container_width=True)

    rel = an.availability_vs_undernourishment(d)
    fig = px.scatter(rel, x="kcal", y=rel["proportion"] * 100, size="population", hover_name="Zone", size_max=45,
                     title=f"Moins de nourriture disponible, plus de sous-nutrition (r = {fr(rel['kcal'].corr(rel['proportion']), 2)})",
                     labels={"kcal": "Disponibilité (kcal/personne/jour)", "y": "% de sous-alimentés"})
    fig.update_traces(marker=dict(color=BLUE, opacity=0.6, line=dict(width=1, color="white")))
    fig.update_layout(**LAYOUT, height=420)
    st.plotly_chart(fig, use_container_width=True)

# ── Conclusion ────────────────────────────────────────────────
with t5:
    st.subheader("Ce qu'il faut retenir")
    st.markdown(
        f"""
| Question | Réponse |
|---|---|
| **Q1** · Proportion de sous-alimentés (2017) | **{pct(q1['proportion'])}** de la population, ~{fr(q1['sous_alimentes'] / 1e6, 0)} millions de personnes |
| **Q2** · Personnes nourries par la disponibilité mondiale | **{an.billions(fed['personnes_nourries'])}** ({pct(fed['part_population'], 0)}), besoin de {fr(need, 0)} kcal/jour |
| **Q3** · Idem, produits végétaux seuls | **{an.billions(veg['personnes_nourries'])}** ({pct(veg['part_population'], 0)}) |
| **Q4** · Utilisation de la disponibilité intérieure | {pct(shares['Alimentation humaine'])} humains · {pct(shares['Alimentation animale'])} animaux · {pct(shares['Pertes'])} pertes |
| **Q5** · Pays les plus touchés | Haïti, Corée du Nord, Madagascar |
| **Q6** · Pays les plus aidés depuis 2013 | Syrie, Éthiopie, Yémen |
| **Q7** · Disponibilité par habitant | + Autriche · − République centrafricaine |

**Le monde produit assez pour nourrir tout le monde : la faim est d'abord un problème de répartition**, aggravé par
l'usage d'une partie des céréales pour l'alimentation animale, par les pertes, et par les crises qui orientent l'aide.
        """
    )
