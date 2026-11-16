#!/usr/bin/env python3
"""Simulator of the evaluated pipeline on synthetic dossiers (Python 3.8+, standard library only).

The real dossiers hold third-party documents and cannot be released. This script generates fictitious dossiers with the
same structure and runs on them the steps of the experiment: retrieval over the 49 passages of the regulation (queries
taken from each case, against the fixed query), prompt assembly for each condition, decision by a model, reading of the
recommendation line and the statistics of the paper.

  python3 simulator.py                               offline: lexical retrieval and a rule in place of the LLM
  python3 simulator.py --embed-url http://localhost:11434/v1 --embed-model bge-m3 \\
                       --llm-url http://localhost:11434/v1 --llm-model <model> --n 6 --conditions text,text_rag_case

Any OpenAI-compatible endpoint works (API key, if needed, in the environment variable LLM_API_KEY).
The numbers printed here describe the synthetic dossiers, not the cases of the paper (see reproduce.py for those).
"""
import argparse
import csv
import json
import math
import os
import random
import re
import statistics
import unicodedata
import urllib.request
from collections import Counter
from math import comb
from pathlib import Path

import prompts
from stats import binom_two_sided, mcnemar_exact, wilson

HERE = Path(__file__).resolve().parent
PASSAGES = [json.loads(line) for line in open(HERE / "regulation" / "passages.jsonl", encoding="utf-8")]
COUNTS = json.load(open(HERE / "results" / "counts.json", encoding="utf-8"))
GOLD = {c: set(v["gold_articles"]) for c, v in COUNTS["retrieval"]["categories"].items()}  # category -> articles of its requirement
PHOTOS = "REGISTROS_FOTOGRAFICOS"  # the photographic records are part of every case
CATEGORIES = [c for c in GOLD if c != PHOTOS]  # the eight document categories of the dossier

# --------------------------------------------------------------------------------------------------- synthetic dossiers
# One document per category: [0] supports the requirement, [1] has a content defect. All names and data are fictitious.
DOCS = {
    "PROGRAMA_AUTOCONTROLE": (
        "PROGRAMA DE AUTOCONTROLE - {vessel}\n1. Objetivo: descrever os procedimentos de boas práticas higiênico-sanitárias a bordo.\n"
        "2. Higienização: convés, porão e utensílios lavados com água potável e sanitizados com solução clorada ao fim de cada viagem, com registro em planilha.\n"
        "3. Conservação do pescado: acondicionamento em gelo em escamas logo após a captura; temperatura monitorada a cada 6 horas.\n"
        "4. Água e gelo: água potável da rede pública e gelo de fábrica registrada.\n"
        "5. Controle de pragas: inspeção visual antes de cada viagem e desinsetização semestral por empresa licenciada.\n"
        "6. Treinamento: tripulação treinada anualmente em higiene pessoal e manipulação do pescado.\nResponsável técnico: Técnico Fictício {num}.",
        "PROGRAMA DE AUTOCONTROLE (modelo)\nEmbarcação: [preencher]\n1. Objetivo: [descrever]\n2. Higienização: [descrever os procedimentos]\n"
        "3. Conservação do pescado: [descrever]\n4. Água e gelo: [descrever]\nDocumento modelo, sem os procedimentos da embarcação."),
    "DECLARACAO_RESPONSABILIDADE": (
        "DECLARAÇÃO DE RESPONSABILIDADE\nEu, Responsável Fictício {num}, responsável pela embarcação {vessel}, declaro que as informações prestadas são "
        "verdadeiras e que a embarcação cumpre os requisitos higiênico-sanitários da Portaria SAP/MAPA nº 310/2020, comprometendo-me a manter as "
        "condições verificadas e a permitir a fiscalização.\nPorto Fictício, {date}. Assinado.",
        "DECLARAÇÃO DE RESPONSABILIDADE\nEu, ____________, responsável pela embarcação Embarcação Fictícia 000, declaro que as informações prestadas "
        "são verdadeiras.\nSem data e sem assinatura."),
    "REGISTROS_TREINAMENTO_TRIPULACAO": (
        "REGISTRO DE TREINAMENTO DA TRIPULAÇÃO\nEmbarcação: {vessel}\nData: {date}. Carga horária: 4 h.\n"
        "Assuntos: higiene pessoal; lavagem das mãos; manipulação e acondicionamento do pescado em gelo; limpeza e sanitização do convés e do porão; controle de pragas.\n"
        "Instrutor: Técnico Fictício {num}\nLista de presença: Tripulante A (assinado), Tripulante B (assinado), Tripulante C (assinado).",
        "REGISTRO DE TREINAMENTO\nData: ____\nAssuntos: boas práticas.\nLista de presença: em branco.\nSem o nome da embarcação."),
    "REGISTROS_CONTROLE_BORDO": (
        "PLANILHA DE CONTROLE A BORDO - {vessel}\nViagem iniciada em {date}.\nHigienização do porão: realizada antes da saída, responsável Tripulante A.\n"
        "Temperatura do pescado (°C): 06h 1,2 | 12h 0,8 | 18h 1,0 | 24h 0,9\nReposição de gelo: 12h e 24h.\nCloro residual da água (mg/L): 0,5\nOcorrências: nenhuma.",
        "PLANILHA DE CONTROLE A BORDO\nEmbarcação: ______ Viagem: ______\nHigienização do porão: [ ] realizada. Responsável: ______\n"
        "Temperatura do pescado (°C): ____ | ____ | ____\nReposição de gelo: ______\nPlanilha em branco, sem registros."),
    "DOCUMENTO_TECNICO_MATERIAL_REVESTIMENTO": (
        "LAUDO TÉCNICO DO MATERIAL DE REVESTIMENTO\nEmbarcação: {vessel}\nO porão e as superfícies que entram em contato com o pescado são revestidos com "
        "fibra de vidro e resina com acabamento atóxico, formando superfície lisa, impermeável, resistente à corrosão e de fácil limpeza e desinfecção. "
        "Urnas e caixas em polietileno de grau alimentício.\nResponsável técnico: Técnico Fictício {num}.",
        "FICHA DE PRODUTO\nTinta anti-incrustante para casco. Uso externo. Contém biocidas. Não indicada para superfícies em contato com alimentos.\n"
        "O documento não descreve o revestimento do porão."),
    "LAUDO_ANALISE_POTABILIDADE": (
        "LAUDO DE ANÁLISE DE POTABILIDADE DA ÁGUA\nLaboratório Fictício de Análises\nAmostra: água do reservatório da embarcação {vessel}, coletada em {date}.\n"
        "Coliformes totais: ausência em 100 mL. Escherichia coli: ausência em 100 mL. Cloro residual livre: 0,6 mg/L. Turbidez: 0,4 uT. pH: 7,1.\n"
        "Conclusão: a amostra atende ao padrão de potabilidade.",
        "LAUDO DE ANÁLISE DE ÁGUA\nLaboratório Fictício de Análises\nAmostra: ponto de coleta não identificado.\n"
        "Coliformes totais: presença em 100 mL. Cloro residual livre: não detectado.\nConclusão: a amostra não atende ao padrão de potabilidade."),
    "DECLARACAO_FORNECEDOR_AGUA_POTAVEL": (
        "DECLARAÇÃO DO FORNECEDOR DE ÁGUA E GELO\nA Fábrica de Gelo Fictícia declara que fornece à embarcação {vessel} água potável da rede pública e gelo "
        "em escamas produzido com água potável.\nNota fiscal fictícia nº {num}, de {date}: 2.000 kg de gelo em escamas.",
        "NOTA FISCAL fictícia nº {num}\nProduto: óleo diesel marítimo, 800 L.\nO documento não trata de água nem de gelo."),
    "DOCUMENTO_CONTROLE_PRAGAS": (
        "CERTIFICADO DE CONTROLE DE PRAGAS E ROEDORES\nDedetizadora Fictícia, com licença sanitária e licença ambiental vigentes.\n"
        "Serviço: desinsetização e desratização da embarcação {vessel} em {date}.\nProdutos: gel inseticida e iscas raticidas em porta-iscas, registrados no órgão competente.\n"
        "Validade: 6 meses.",
        "RECIBO\nRecebi o valor referente à aplicação de veneno em uma embarcação.\nSem identificação da empresa, da licença ou dos produtos usados."),
}


def generate(n, seed):
    """n fictitious cases, half approved and half rejected. Rejected cases have 1 to 3 defective documents. Whole
    categories are missing in both classes, at the rates the paper reports for the real sample (7 of 20 approved and
    5 of 20 rejected dossiers), so a completeness rule does not separate the classes here either."""
    rng = random.Random(seed)
    cases = []
    for i in range(1, n + 1):
        rejected = i % 2 == 0
        present = list(CATEGORIES)
        if rng.random() < (5 / 20 if rejected else 7 / 20):
            dropped = rng.sample(CATEGORIES, rng.choice((1, 2)))
            present = [c for c in present if c not in dropped]
        defects = set(rng.sample(present, min(len(present), rng.choice((1, 2, 3))))) if rejected else set()
        fields = {"vessel": f"Embarcação Fictícia {i:03d}", "num": f"{i:03d}", "date": f"{rng.randint(1, 28):02d}/{rng.randint(1, 6):02d}/2026"}
        text = (f"DOSSIÊ SINTÉTICO S{i:03d} (dados fictícios, gerados por simulator.py)\n"
                "Solicitação de Certificado Oficial de Boas Práticas Higiênico-Sanitárias a Bordo\n"
                f"Embarcação: {fields['vessel']}. Comprimento: {rng.randint(9, 24)} m. Conservação do pescado a bordo: gelo.\n"
                f"Registros fotográficos: {rng.randint(4, 60)} fotos anexadas ao processo (não incluídas no simulador).\n\n")
        for c in present:
            text += f"### {c} | {c.lower()}_s{i:03d}.pdf\n{DOCS[c][c in defects].format(**fields)}\n\n"
        cases.append({"case": f"S{i:03d}", "label": "rejected" if rejected else "approved", "text": text, "present": present,
                      "missing": [c for c in CATEGORIES if c not in present], "defects": sorted(defects)})
    return cases


# ------------------------------------------------------------------------------------------------------------ retrieval
def section_queries(text, max_chars=2000):
    """Queries taken from the case, as in the platform: one per `### LABEL | file` section of the dossier (sections with
    the same label are merged), made of the label in plain words and the beginning of the section, plus one for the
    text before the first section (the dossier header)."""
    heads = list(re.finditer(r"(?m)^### ([^|\n]+?)\s*(?:\|[^\n]*)?$", text))
    if not heads:
        return []
    sections = {}
    for h, nxt in zip(heads, heads[1:] + [None]):
        label = h.group(1).strip()
        sections[label] = sections.get(label, "") + text[h.end():nxt.start() if nxt else len(text)].strip() + "\n"
    header = text[:heads[0].start()].strip()
    return ([header[:max_chars]] if header else []) + [(k.replace("_", " ").lower() + "\n" + v.strip())[:max_chars] for k, v in sections.items()]


def tokens(text):
    plain = "".join(ch for ch in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(ch) != "Mn")
    return re.findall(r"[a-z0-9]{3,}", plain)


class Lexical:
    """Offline stand-in for the embedding model: TF-IDF vectors (weights learned from the 49 passages), cosine similarity."""
    name = "lexical TF-IDF (offline stand-in for bge-m3)"

    def __init__(self):
        df = Counter(t for p in PASSAGES for t in set(tokens(p["text"])))
        self.idf = {t: math.log((len(PASSAGES) + 1) / (n + 1)) + 1 for t, n in df.items()}

    def embed(self, texts):
        out = []
        for text in texts:
            v = {t: (1 + math.log(n)) * self.idf[t] for t, n in Counter(tokens(text)).items() if t in self.idf}
            norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
            out.append({t: x / norm for t, x in v.items()})
        return out


class Api:
    """Embeddings from an OpenAI-compatible endpoint (for instance bge-m3 served by Ollama, as in the paper)."""

    def __init__(self, url, model):
        self.url, self.model, self.name = url.rstrip("/"), model, f"{model} at {url}"

    def embed(self, texts):
        out = []
        for i in range(0, len(texts), 8):
            data = post(self.url + "/embeddings", {"model": self.model, "input": texts[i:i + 8]})["data"]
            for d in sorted(data, key=lambda d: d["index"]):
                norm = math.sqrt(sum(x * x for x in d["embedding"])) or 1.0
                out.append([x / norm for x in d["embedding"]])
        return out


def similarity(a, b):
    if isinstance(a, dict):
        return sum(x * b.get(t, 0.0) for t, x in a.items())
    return sum(x * y for x, y in zip(a, b))


def top(query_vec, passage_vecs, k):
    return sorted(range(len(PASSAGES)), key=lambda i: -similarity(query_vec, passage_vecs[i]))[:k]


def retrieve_case(text, embedder, passage_vecs, k=2):
    """Top k passages of each query taken from the case, joined without repetition."""
    found = []
    for qv in embedder.embed(section_queries(text)):
        found += [i for i in top(qv, passage_vecs, k) if i not in found]
    return found


def context(indices):
    return "\n\n".join(f"[Source: {PASSAGES[i]['file']}, {PASSAGES[i]['label']}] {PASSAGES[i]['text']}" for i in indices)


def retrieval_report(cases, case_sets, fixed_ranking):
    def hits(sets):
        h = t = 0
        for c, s in zip(cases, sets):
            labels = {PASSAGES[i]["label"] for i in s}
            for cat in c["present"] + [PHOTOS]:
                h += bool(labels & GOLD[cat])
                t += 1
        return h, t

    def expected_random():
        e = t = 0
        for c, s in zip(cases, case_sets):
            for cat in c["present"] + [PHOTOS]:
                g = sum(p["label"] in GOLD[cat] for p in PASSAGES)
                e += 1 - comb(len(PASSAGES) - g, len(s)) / comb(len(PASSAGES), len(s))
                t += 1
        return e / t

    sizes = [len(s) for s in case_sets]
    rows = [("queries from the case (top 2 per query)", case_sets),
            ("fixed query, as many passages as the case", [fixed_ranking[:len(s)] for s in case_sets]),
            ("fixed query, top 8", [fixed_ranking[:8] for _ in cases])]
    print(f"  passages per case: median {statistics.median(sizes)}, {min(sizes)} to {max(sizes)}")
    print(f"  {'strategy':<44}{'articles found':>16}{'rate':>7}{'distinct sets':>15}")
    for name, sets in rows:
        h, t = hits(sets)
        print(f"  {name:<44}{f'{h} of {t}':>16}{h / t:>7.3f}{len({frozenset(s) for s in sets}):>15}")
    print(f"  {'random draw of as many passages (expected)':<44}{'':>16}{expected_random():>7.3f}")


# ------------------------------------------------------------------------------------------------------------ decisions
def post(url, body):
    headers = {"Content-Type": "application/json"}
    if os.environ.get("LLM_API_KEY"):
        headers["Authorization"] = "Bearer " + os.environ["LLM_API_KEY"]
    with urllib.request.urlopen(urllib.request.Request(url, json.dumps(body).encode(), headers), timeout=3600) as r:
        return json.load(r)


def rule_model(prompt):
    """Offline stand-in for the LLM: the completeness rule of the paper (reject when a document category is missing)."""
    dossier = prompt.split("\nDOSSIE:\n", 1)[1]
    missing = [c for c in CATEGORIES if f"### {c} " not in dossier]
    lines = [f"{c.replace('_', ' ').lower()}: {'NAO VERIFICAVEL' if c in missing else 'ATENDE'}" for c in CATEGORIES]
    return "\n".join(lines) + f"\nRECOMENDACAO: {'INDEFERIR' if missing else 'DEFERIR'}"


def decision(answer):
    """Read from the final recommendation line ("DEFERIR", approve, is contained in "INDEFERIR", reject)."""
    found = re.findall(r"RECOMENDACAO:\s*(DEFERIR|INDEFERIR)", answer.upper().replace("Ç", "C").replace("Ã", "A"))
    return {"DEFERIR": "approved", "INDEFERIR": "rejected"}[found[-1]] if found else None


def citations(answer, indices):
    """[Source: file, Art. N] markers that give a file and an article (or annex), and how many of them point to a
    passage that was in the prompt. As in the paper, this checks the existence of the source, not its relevance."""
    marks = re.findall(r"\[Source:\s*([^,\]]+?),\s*(?:Art\.?\s*(\d+)|ANEXO\s+([IVX]+))", answer, flags=re.I)
    sent = {(PASSAGES[i]["file"], PASSAGES[i]["label"]) for i in indices}
    return len(marks), sum((f.strip(), f"Art. {n}" if n else f"ANEXO {x.upper()}") in sent for f, n, x in marks)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    text_conditions = [c for c, (_, _, photos) in prompts.CONDITIONS.items() if photos is None]
    ap.add_argument("--n", type=int, default=40, help="number of synthetic cases (default 40)")
    ap.add_argument("--seed", type=int, default=2027)
    ap.add_argument("--out", default="out", help="output folder (default out/)")
    ap.add_argument("--conditions", default=",".join(text_conditions), help="comma-separated, among: " + ", ".join(text_conditions))
    ap.add_argument("--embed-url", help="OpenAI-compatible base URL for embeddings (default: offline lexical retrieval)")
    ap.add_argument("--embed-model", default="bge-m3")
    ap.add_argument("--llm-url", help="OpenAI-compatible base URL for the model (default: offline completeness rule)")
    ap.add_argument("--llm-model")
    ap.add_argument("--max-tokens", type=int, default=16384)
    ap.add_argument("--reasoning-effort", help="sent as reasoning_effort when given (the study ran with reasoning off: none)")
    a = ap.parse_args()
    conditions = a.conditions.split(",")
    assert all(c in text_conditions for c in conditions), f"conditions must be among {text_conditions}"
    out = Path(a.out)
    (out / "cases").mkdir(parents=True, exist_ok=True)
    (out / "runs").mkdir(exist_ok=True)
    (out / "example_prompts").mkdir(exist_ok=True)

    cases = generate(a.n, a.seed)
    for c in cases:
        (out / "cases" / f"{c['case']}.txt").write_text(c["text"], encoding="utf-8")
    with open(out / "labels.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["case", "label", "missing_categories", "defective_documents"])
        w.writerows([c["case"], c["label"], " ".join(c["missing"]), " ".join(c["defects"])] for c in cases)
    n_rej = sum(c["label"] == "rejected" for c in cases)
    print(f"Synthetic cases: {len(cases)} ({len(cases) - n_rej} approved, {n_rej} rejected) written to {out / 'cases'}; "
          f"with a missing category: {sum(bool(c['missing']) and c['label'] == 'approved' for c in cases)} approved, "
          f"{sum(bool(c['missing']) and c['label'] == 'rejected' for c in cases)} rejected")

    embedder = Api(a.embed_url, a.embed_model) if a.embed_url else Lexical()
    passage_vecs = embedder.embed([p["text"] for p in PASSAGES])
    fixed_ranking = top(embedder.embed([prompts.INSTRUCTIONS])[0], passage_vecs, len(PASSAGES))
    case_sets = [retrieve_case(c["text"], embedder, passage_vecs) for c in cases]
    print(f"\nRetrieval over the {len(PASSAGES)} passages of the regulation, embeddings: {embedder.name}")
    retrieval_report(cases, case_sets, fixed_ranking)
    if a.embed_url and "bge-m3" in a.embed_model:
        ours, paper = [PASSAGES[i]["label"] for i in fixed_ranking], COUNTS["retrieval"]["fixed_query_ranking_bge_m3"]
        same = next((i for i, (x, y) in enumerate(zip(ours, paper)) if x != y), len(paper))
        print(f"  fixed query: the first {same} of the {len(paper)} positions of the ranking equal the ranking obtained in the study")

    model_name = f"{a.llm_model} at {a.llm_url}" if a.llm_url else "completeness rule (offline stand-in for the LLM)"
    print(f"\nDecisions, model: {model_name}")
    print(f"  {'condition':<22}{'correct':>9}{'rejections':>12}{'no decision':>13}   accuracy [95% Wilson]   p against chance   citations (in the prompt)")
    right = {}
    for cond in conditions:
        template, ctx_mode, _ = prompts.CONDITIONS[cond]
        rows, marks, marks_ok, cut = [], 0, 0, 0
        for c, case_set in zip(cases, case_sets):
            indices = {"fixed": fixed_ranking[:8], "case": case_set, "full": list(range(len(PASSAGES))), None: []}[ctx_mode]
            prompt = (template.replace("{{instructions}}", prompts.INSTRUCTIONS).replace("{{context}}", context(indices))
                      .replace("{{document_text}}", c["text"]))
            if c is cases[0]:
                (out / "example_prompts" / f"{cond}.txt").write_text(prompt, encoding="utf-8")
            if a.llm_url:
                body = {"model": a.llm_model, "temperature": 0, "max_tokens": a.max_tokens, "messages": [{"role": "user", "content": prompt}]}
                if a.reasoning_effort:
                    body["reasoning_effort"] = a.reasoning_effort
                choice = post(a.llm_url.rstrip("/") + "/chat/completions", body)["choices"][0]
                answer = choice["message"].get("content") or ""
                cut += choice.get("finish_reason") == "length"
            else:
                answer = rule_model(prompt)
            m, ok = citations(answer, indices)
            marks, marks_ok = marks + m, marks_ok + ok
            rows.append({"case": c["case"], "label": c["label"], "decision": decision(answer),
                         "retrieved": [f"{PASSAGES[i]['file']}, {PASSAGES[i]['label']}" for i in indices], "answer": answer})
        with open(out / "runs" / f"{cond}.jsonl", "w", encoding="utf-8") as f:
            f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
        right[cond] = [r["decision"] == r["label"] for r in rows]  # a response without a decision counts as an error
        k, lo_hi = sum(right[cond]), wilson(sum(right[cond]), len(rows))
        print(f"  {cond:<22}{k:>9}{sum(r['decision'] == 'rejected' for r in rows):>12}{sum(r['decision'] is None for r in rows):>13}"
              f"   {k / len(rows):.3f} [{lo_hi[0]:.3f}, {lo_hi[1]:.3f}]{binom_two_sided(k, len(rows)):>15.3f}"
              f"   {f'{marks} ({marks_ok})' if ctx_mode else '-':>12}")
        if cut:
            print(f"    warning: {cut} answer(s) cut by the token limit; raise the context window of the server "
                  "(Ollama: OLLAMA_CONTEXT_LENGTH=65536) or --max-tokens")
    for x, y in zip(conditions, conditions[1:]):
        b, c2 = sum(p and not q for p, q in zip(right[x], right[y])), sum(q and not p for p, q in zip(right[x], right[y]))
        print(f"  exact McNemar, {x} against {y}: only the first correct {b}, only the second {c2}, p = {mcnemar_exact(b, c2):.3f}")
    print(f"\nPrompts of the first case in {out / 'example_prompts'}, answers in {out / 'runs'}.")

    # self-check of the generator, the retrieval and the citation logic
    assert all(len(c["missing"]) <= 2 and (c["label"] == "rejected") == bool(c["defects"]) for c in cases)
    assert citations("[Source: a.txt, Art. 9, I] [Source: a.txt, ANEXO I, 2.7] [Source: b.txt, Art. 9]", []) == (3, 0)
    f0, l0 = PASSAGES[0]["file"], PASSAGES[0]["label"]
    assert citations(f"[Source: {f0}, {l0}, item 1.1] [Source: {f0}, Art. 999]", [0]) == (2, 1)
    assert section_queries("header\n### A_B | f.pdf\nx\n### C\ny\n### A_B | g.pdf\nz") == ["header", "a b\nx\nz", "c\ny"]
    assert all(set(top(embedder.embed([p["text"]])[0], passage_vecs, 1)) <= {i for i, q in enumerate(PASSAGES) if q["text"] == p["text"]}
               for p in PASSAGES[:3]), "a passage must retrieve itself"


if __name__ == "__main__":
    main()
