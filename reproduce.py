#!/usr/bin/env python3
"""Recomputes the statistics reported in the paper from the aggregated counts in results/counts.json.

Usage: python3 reproduce.py        (Python 3.8+, standard library only; exits with status 1 if a value does not match)
Each line shows a statement of the paper, the value printed in the paper and the value recomputed here.
"""
import json
import sys
from math import comb
from pathlib import Path

from stats import binom_two_sided, chance_region, kappa, mcnemar_exact, power, wilson

HERE = Path(__file__).resolve().parent
D = json.load(open(HERE / "results" / "counts.json", encoding="utf-8"))
PASSAGES = [json.loads(line) for line in open(HERE / "regulation" / "passages.jsonl", encoding="utf-8")]
MODELS = ["gemma", "gpt", "gemini", "claude"]
failures = 0


def check(statement, paper, got, digits=None):
    """digits: decimals printed in the paper (None = exact comparison)."""
    global failures
    shown = round(got, digits) if digits is not None else got
    ok = shown == paper
    failures += not ok
    values = "" if paper is True else f": paper {paper}, recomputed {shown}"  # paper=True: a statement that must hold
    print(f"  [{'ok' if ok else 'MISMATCH'}] {statement}{values}")


def section(title):
    print(f"\n{title}")


correct = lambda c: c["tp"] + c["tn"]
rejections = lambda c: c["tp"] + c["fp"]
pmin = lambda pairs: min(mcnemar_exact(b, c) for b, c in pairs)

# ---------------------------------------------------------------------------------------------------------------------
section("Table 2. Correct decisions on the 40 cases (suggested rejections)")
TABLE2 = {  # as printed in the paper: Gemma, GPT-6 Luna, Gemini, Claude Haiku
    "text": [(20, 8), (20, 40), (20, 4), (20, 40)],
    "text_rag_fixed": [(21, 7), (20, 40), (20, 2), (20, 40)],
    "text_rag_case": [(21, 7), (20, 40), (22, 2), (20, 40)],
    "text_full_regulation": [(19, 5), (19, 37), (21, 3), (20, 40)],
    "text_checklist": [(18, 18), (20, 40), (16, 24), (20, 40)],
    "photos": [(15, 15), (20, 40), (18, 4), (20, 40)],
    "photos_rag_fixed": [(18, 6), (20, 40), (19, 3), (20, 40)],
    "photos_rag_case": [(19, 11), (20, 40), (19, 3), (21, 39)],
    "all_photos": [(14, 14), (20, 40), (21, 5), (20, 40)],
    "all_photos_checklist": [(15, 17), (20, 40), (20, 14), (20, 40)],
}
print(f"  {'condition':<22}" + "".join(f"{m:>10}" for m in MODELS) + "   exact binomial p against chance")
cells_ok = True
for cond, row in TABLE2.items():
    got = [(correct(D["decisions"][m][cond]), rejections(D["decisions"][m][cond])) for m in MODELS]
    cells_ok &= got == row
    ps = " ".join(f"{binom_two_sided(k, 40):.3f}" for k, _ in got)
    print(f"  {cond:<22}" + "".join(f"{f'{k} ({r})':>10}" for k, r in got) + f"   {ps}")
check("all 40 cells equal to the paper", True, cells_ok)
all_counts = [correct(D["decisions"][m][c]) for m in MODELS for c in TABLE2]
check("lowest and highest count of correct decisions", (14, 22), (min(all_counts), max(all_counts)))

section("Chance level (Metrics paragraph and caption of Table 2)")
lo, hi = wilson(20, 40)
check("95% Wilson interval of 20 correct of 40", (0.352, 0.648), (round(lo, 3), round(hi, 3)))
check("counts that the exact binomial test does not separate from chance", (14, 26), chance_region(40))
check("power to detect a true accuracy of 0.65 with 40 cases", 0.44, power(40, 0.65), 2)
n80 = next(n for n in range(40, 200) if power(n, 0.65) >= 0.8)
check("cases needed for a power of 0.8 ('about 90')", True, 85 <= n80 <= 95)
print(f"         smallest n with power >= 0.8: {n80} (power {power(n80, 0.65):.3f}); p of 14 correct of 40: {binom_two_sided(14, 40):.3f}")
check("no condition differs significantly from chance (p >= 0.05 in all 40 cells)", True, all(binom_two_sided(k, 40) >= 0.05 for k in all_counts))
r = D["rule_missing_category"]
check("accuracy of the rule that rejects cases with a missing category", 0.45, correct(r) / 40, 2)
check("rejected cases with every category (which the rule approves)", 15, r["fn"])

section("Tendencies of the models (Results)")
no_checklist = [c for c in TABLE2 if "checklist" not in c]
for m, paper in (("gemma", (0.10, 0.25)), ("gemini", (0.05, 0.15))):
    s = [D["decisions"][m][c]["tp"] / 20 for c in no_checklist]
    check(f"sensitivity of {m} without the checklist (min, max)", paper, (min(s), max(s)))
check("Claude Haiku: conditions in which it rejected all 40 cases", 9, sum(rejections(D["decisions"]["claude"][c]) == 40 for c in TABLE2))
check("GPT-6 Luna: conditions in which it rejected all 40 cases", 9, sum(rejections(D["decisions"]["gpt"][c]) == 40 for c in TABLE2))

section("Exact McNemar tests on the 40 cases")
within = {m: {k: v for k, v in D["mcnemar_within_model"][m].items()} for m in MODELS}
between = {m: D["mcnemar_gemma_vs_model"][m] for m in MODELS[1:]}
every = [v for m in within.values() for v in m.values()] + [v for m in between.values() for v in m.values()]
check(f"smallest p over the {len(every)} comparisons within a model or against Gemma (p >= 0.092)", 0.092, pmin(every), 3)
rag_pairs = ["text vs text_rag_case", "text_rag_fixed vs text_rag_case", "photos vs photos_rag_case", "photos_rag_fixed vs photos_rag_case"]
check("smallest p of retrieval from the case against no RAG or the fixed query (p >= 0.289)", 0.289,
      pmin([within[m][k] for m in MODELS for k in rag_pairs]), 3)
check("Gemma, text against photos in order and numbered (p = 0.18)", 0.18, mcnemar_exact(*within["gemma"]["text vs photos"]), 2)
check("Gemma accuracy with photos and without", (0.375, 0.5), (correct(D["decisions"]["gemma"]["photos"]) / 40, correct(D["decisions"]["gemma"]["text"]) / 40))

section("Variation between three runs (Gemini and Claude Haiku)")
rv = {k: v for k, v in D["run_variation"].items() if not k.startswith("_")}
check("cases whose decision changed: Gemini text, Gemini photos+RAG case, Claude text, Claude photos+RAG case", [5, 3, 0, 1],
      [rv[k]["cases_with_changed_decision"] for k in ("gemini text", "gemini photos_rag_case", "claude text", "claude photos_rag_case")])
runs = [k for v in rv.values() for k, _ in v["runs"]]
check("correct decisions per run (min, max)", (18, 21), (min(runs), max(runs)))

section("Retrieval (332 document categories present in the 40 dossiers)")
cats = D["retrieval"]["categories"]
total = sum(c["dossiers_with_category"] for c in cats.values())
hit_case = sum(c["hit_case_queries"] for c in cats.values())
hit_fixed = sum(c["hit_fixed_query_same_embeddings_same_k"] for c in cats.values())
hit_table = sum(c["hit_fixed_query_as_run_for_table"] for c in cats.values())
check("document categories evaluated", 332, total)
check("retrieval from the case: hits and rate", (235, 0.708), (hit_case, round(hit_case / total, 3)))
check("fixed query, same embeddings and number of passages: hits and rate", (161, 0.485), (hit_fixed, round(hit_fixed / total, 3)))
check("fixed query as run for Table 2 (other embeddings, 8 passages): hits and rate", (118, 0.355), (hit_table, round(hit_table / total, 3)))
check("abstract: 71% against 48%", (71, 48), (round(100 * hit_case / total), round(100 * hit_fixed / total)))
three = ["REGISTROS_TREINAMENTO_TRIPULACAO", "DOCUMENTO_TECNICO_MATERIAL_REVESTIMENTO", "DOCUMENTO_CONTROLE_PRAGAS"]
check("fixed query never finds the articles on training, lining material or pests", [0, 0, 0],
      [cats[c]["hit_fixed_query_same_embeddings_same_k"] for c in three])
check("retrieval from the case, three weakest categories (pests, training, lining)", [(3, 29), (13, 40), (14, 37)],
      [(cats[c]["hit_case_queries"], cats[c]["dossiers_with_category"]) for c in (three[2], three[0], three[1])])
labels = [p["label"] for p in PASSAGES]
check("passages in the index", 49, len(labels))


def random_rate(k):
    """Expected hit rate if k of the 49 passages were drawn at random (hypergeometric)."""
    exp = 0.0
    for c in cats.values():
        g = sum(label in c["gold_articles"] for label in labels)
        exp += c["dossiers_with_category"] * (1 - comb(49 - g, k) / comb(49, k))
    return exp / total


check("random draw of eight passages", 0.285, random_rate(8), 3)
ranking = D["retrieval"]["fixed_query_ranking_bge_m3"]
for k in (8, 10):
    hits = sum(c["dossiers_with_category"] for c in cats.values() if set(ranking[:k]) & set(c["gold_articles"]))
    print(f"         not in the paper: fixed query with the top {k} of its bge-m3 ranking: {hits} of {total} ({hits / total:.3f}); "
          f"random draw of {k}: {random_rate(k):.3f}")
print(f"         the random baseline 'as many passages as each case' ({D['retrieval']['random_baseline_same_k_as_each_case']}) "
      "needs the number of passages of each case and is reported as computed by the authors")

section("Requirement level (items of the analysts' opinions, 39 cases)")
rl = D["requirement_level"]
check("items, flagged by the analysts, of which requests for supplements", (351, 129, 99),
      (rl["reference_items"], rl["flagged_by_analysts"], rl["of_which_requests_for_supplements"]))
check("share of flagged items", 0.37, rl["flagged_by_analysts"] / rl["reference_items"], 2)
rows = {m: [(v["both"] / v["model"], v["both"] / v["analyst"], kappa(v["items"], v["analyst"], v["model"], v["both"])) for v in rl[m].values()] for m in MODELS}
rng = lambda ms, i, d: (round(min(x[i] for m in ms for x in rows[m]), d), round(max(x[i] for m in ms for x in rows[m]), d))
check("Gemma and Gemini: recall (min, max)", (0.01, 0.09), rng(["gemma", "gemini"], 1, 2))
check("Gemma and Gemini: Cohen's kappa (min, max)", (-0.013, 0.059), rng(["gemma", "gemini"], 2, 3))
check("GPT-6 Luna and Claude Haiku: recall (min, max)", (0.39, 0.64), rng(["gpt", "claude"], 1, 2))
check("GPT-6 Luna and Claude Haiku: precision (min, max)", (0.37, 0.47), rng(["gpt", "claude"], 0, 2))
check("GPT-6 Luna and Claude Haiku: Cohen's kappa (min, max)", (0.057, 0.223), rng(["gpt", "claude"], 2, 3))

section("Draft opinions (first 20 cases)")
dr = D["drafts"]
a, b = dr["items"]["no_retrieval"], dr["items"]["rag_case"]
check("decision equal to the analyst's, without and with retrieval", (8, 12), (dr["decision_equal_to_analyst"]["no_retrieval"], dr["decision_equal_to_analyst"]["rag_case"]))
check("McNemar between the two drafts (p = 0.125)", 0.125, mcnemar_exact(*dr["mcnemar_decision"]), 3)
check("neither differs from always rejecting, 10 of 20 (p >= 0.05)", True, min(binom_two_sided(8, 20), binom_two_sided(12, 20)) >= 0.05)
print(f"         exact binomial p of 8 and of 12 of 20 against 0.5: {binom_two_sided(8, 20):.3f}, {binom_two_sided(12, 20):.3f}")
check("items compared, flagged by analysts, by drafts (both)", (411, 71, 19, 3, 21, 4), (a["items"], a["analyst"], a["model"], a["both"], b["model"], b["both"]))
check("Cohen's kappa of the two drafts", (-0.007, 0.009), (round(kappa(a["items"], a["analyst"], a["model"], a["both"]), 3), round(kappa(b["items"], b["analyst"], b["model"], b["both"]), 3)))
check("analysts' requests for supplements, assessed as conforming by the drafts", (54, 51, 50),
      (a["analyst_requests_for_supplements"], a["of_which_draft_conforming"], b["of_which_draft_conforming"]))

section("First round (20 cases, photos unordered, fixed query)")
fr = D["first_round"]
for m, paper in (("gemma", (0.4, 0.55)), ("qwen", (0.2, 0.4))):
    acc = [correct(c) / 20 for c in fr[m]["decisions"].values()]
    check(f"accuracy of {m} (min, max)", paper, (min(acc), max(acc)))
ps = [mcnemar_exact(*v) for m in ("gemma", "qwen") for v in fr[m]["mcnemar"].values()]
check("McNemar p for the effect of photos and of RAG (min, max)", (0.34, 1.0), (round(min(ps), 2), round(max(ps), 2)))
nd = [c["no_decision"] for c in fr["qwen"]["decisions"].values()]
check("Qwen responses without a recommendation line per condition (min, max)", (1, 7), (min(nd), max(nd)))

print(f"\n{'ALL VALUES MATCH THE PAPER' if not failures else f'{failures} VALUE(S) DO NOT MATCH'}")
sys.exit(1 if failures else 0)
