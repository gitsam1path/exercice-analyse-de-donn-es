"""Tests des calculs (lancer : pytest)."""

import pytest

from src import analysis as an


@pytest.fixture(scope="module")
def d():
    return an.load_data()


def test_population_mondiale_2017(d):
    # La somme des pays doit correspondre à la population mondiale (~7,55 milliards)
    assert an.population_2017(d).sum() == pytest.approx(7.548e9, rel=1e-3)


def test_q1_proportion(d):
    q1 = an.q1_proportion(d)
    assert q1["sous_alimentes"] == pytest.approx(535.7e6, rel=1e-3)
    assert q1["proportion"] == pytest.approx(0.071, abs=0.001)


def test_les_valeurs_inferieures_a_100k_ne_sont_pas_inventees(d):
    # "<0.1" doit rester non chiffré : la Dominique ne doit pas apparaître dans le classement
    top = an.q5_highest_proportion(d, n=20)
    assert "Dominique" not in set(top["Zone"])
    assert top.iloc[0]["Zone"] == "Haïti"


def test_q2_q3_personnes_nourries(d):
    total = an.people_fed(d)
    vegetal = an.people_fed(d, "vegetale")
    assert total["personnes_nourries"] == pytest.approx(8.37e9, rel=1e-2)
    assert vegetal["personnes_nourries"] == pytest.approx(6.90e9, rel=1e-2)
    assert vegetal["personnes_nourries"] < total["personnes_nourries"]


def test_q2_depend_du_besoin_calorique(d):
    assert an.people_fed(d, kcal_need=2000)["personnes_nourries"] > an.people_fed(d, kcal_need=2500)["personnes_nourries"]


def test_q4_parts(d):
    uses = an.q4_uses(d).set_index("Utilisation")["Part"]
    assert uses["Alimentation humaine"] == pytest.approx(0.495, abs=0.001)
    assert uses["Alimentation animale"] == pytest.approx(0.132, abs=0.001)
    assert uses["Pertes"] == pytest.approx(0.046, abs=0.001)


def test_q6_aide(d):
    top = an.q6_most_aid(d)
    assert top.iloc[0]["Zone"] == "République arabe syrienne"
    assert top.iloc[0]["tonnes"] == 1_858_943


def test_q7_disponibilite(d):
    most, least = an.q7_availability(d)
    assert most.iloc[0]["Zone"] == "Autriche"
    assert least.iloc[0]["Zone"] == "République centrafricaine"


def test_format_francais():
    assert an.fr(1234.56, 1) == "1 234,6"
    assert an.pct(0.071) == "7,1 %"
