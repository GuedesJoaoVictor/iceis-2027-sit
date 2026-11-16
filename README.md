# Supplementary material

Anonymized artifact of a submission under double-blind review: a feasibility study of a RAG platform that assists
analysts with technical opinions for hygiene-sanitary certification of fishing vessels.

This file explains what the artifact contains and why. **To run it, follow [TUTORIAL.md](TUTORIAL.md)**: two commands,
Python 3.8 or later, nothing to install.

## What the artifact is for

1. **Checking the statistics of the paper.** `reproduce.py` recomputes every reported statistic from aggregated
   counts and compares each one with the value printed in the paper.
2. **Seeing the experiment run.** `simulator.py` executes the steps of the experiment on fictitious dossiers, offline
   or with real models.

## What is included and what is not

| Included | Not included |
|---|---|
| Aggregated counts of every run reported in the paper (`results/counts.json`) | The 40 dossiers, their photographs and the analysts' opinions |
| The regulatory corpus as indexed, 49 passages (`regulation/passages.jsonl`); the ordinances are public | The answers of the models, which quote the dossiers |
| The prompt of every condition, verbatim (`prompts.py`) | Case-level outcomes; only counts are released |
| A simulator of the pipeline on fictitious dossiers (`simulator.py`) | The repository of the platform |

## Why the real cases are not here

The 40 cases are real certification requests. Their dossiers hold third-party documents (of vessel owners,
responsible technicians and suppliers), the photographs belong to the same requests, and the answers of the models
quote these documents. None of this can be published.

The artifact therefore releases counts only: confusion matrices (rejection is the positive class), the discordant
pairs of the McNemar tests and 2x2 agreement counts. They are enough to recompute every test of the paper without
case-level data.

Two values cannot be recomputed from counts, because they depend on the number of passages retrieved for each case,
and are reported as computed by the authors: the hits of the fixed query "with as many passages as each case"
(161 of 332) and the corresponding random baseline (0.340). For both, `reproduce.py` recomputes the nearest
quantities that the counts allow: 157 of 332 for a fixed top 8 or top 10, from the published ranking of the fixed
query, and 0.285 for a random draw of eight passages, which is the other baseline printed in the paper.

## Why the repository of the platform is not here

The platform described in the paper is a Java 21 service with PostgreSQL and pgvector, an object store and model
providers. Its repository is not part of this artifact, for three reasons.

1. **It would not make the experiment reproducible.** The results depend on the real dossiers and photographs. With
   the platform alone, a reviewer could deploy it but could not reproduce any number of the paper.
2. **Double-blind review.** A repository identifies who develops it in many places: commit history, build
   coordinates, addresses of the hosting organization, documentation and configuration files. Removing all of them
   reliably from a whole code base is error-prone, and a single leftover would break the anonymity of the submission.
3. **Cost for the reviewer.** Running it means deploying an application, a database with a vector extension, an
   object store and a model server before any result appears.

Instead, the artifact isolates what determines the outcome of the experiment in one file of about 350 lines,
`simulator.py`, which runs without installing anything. The next section states what it reproduces and what it does
not.

## How the simulator relates to the platform

| Step of the experiment | In the study | In the simulator |
|---|---|---|
| Dossier | Text assembled from the attachments of a real case, one `### CATEGORY \| file` section per document | Fictitious dossier with the same structure |
| Regulatory corpus | 49 passages, split per article | The same 49 passages |
| Queries taken from the case | One per section of the dossier, plus one for its header | Same construction (`section_queries`) |
| Retrieval | Top 2 passages per query; top 8 for the fixed query; cosine similarity | Same. Offline, TF-IDF vectors stand in for the embedding model; with `--embed-model bge-m3`, the embedding model of the study is used |
| Prompt | Template of the condition | The same templates (`prompts.py`) |
| Model | Local and hosted vision-language models | Any OpenAI-compatible endpoint. Offline, the completeness rule of the paper (reject when a document category is missing) stands in for the model |
| Decision | Read from the final recommendation line | Same |
| Statistics | Wilson interval, exact binomial and McNemar tests | Same (`stats.py`) |
| Photographs | Sent to the model as numbered images | Not simulated; the prompts are in `prompts.py` and the outcomes in `results/counts.json` |
| Draft opinions | Compared item by item with the analysts' opinions | Not simulated; the prompts are in `prompts.py` and the counts in `results/counts.json` |
| Document processing, storage, task and review API, provider adapters | Platform | Not reproduced |

One check ties the simulator to the platform. With `bge-m3`, the simulator ranks the 49 passages for the fixed query
and compares the ranking with the one the platform produced in the study, published in `results/counts.json`. In our
run all 49 positions were equal, so both return the same passages for the same query. The script repeats this
comparison whenever it runs with `bge-m3`.

## How to read the numbers

- **`reproduce.py` is about the paper.** Each line shows a statement, the value printed in the paper and the value
  recomputed from the counts. The script exits with status 1 if any of them differs.
- **`simulator.py` is about fictitious dossiers.** Its accuracy and retrieval rates describe the synthetic cases, not
  the cases of the paper. The fictitious documents are short and their defects are explicit, so accuracy on them says
  nothing about the real cases.
- **How the synthetic cases are built.** Half are labeled approved and half rejected. Rejected cases contain one to
  three documents with a content defect, such as a blank control sheet, an unsigned statement or a water report that
  fails. Whole document categories are missing in both classes, at the rates the paper reports for the real sample
  (7 of 20 approved and 5 of 20 rejected dossiers). A completeness rule therefore does not separate the synthetic
  classes either, as in the paper.

## Names used in the files

| `counts.json` and `simulator.py` | Row of Table 2 |
|---|---|
| `text` | Text |
| `text_rag_fixed`, `text_rag_case` | + RAG, fixed; + RAG, case |
| `text_full_regulation` | + full reg. |
| `text_checklist` | + checklist |
| `photos`, `photos_rag_fixed`, `photos_rag_case` | Photos (30); + RAG, fixed; + RAG, case |
| `all_photos`, `all_photos_checklist` | All photos; + checklist |

Models: `gemma` (Gemma 4 26B-A4B), `gpt` (GPT-6 Luna), `gemini` (Gemini 3.5 Flash-Lite), `claude` (Claude Haiku 5.5)
and `qwen` (Qwen3-VL-8B, first round only).

The document categories keep the identifiers of the submission form:

| Identifier | Meaning |
|---|---|
| `PROGRAMA_AUTOCONTROLE` | Self-control program |
| `DECLARACAO_RESPONSABILIDADE` | Statement of responsibility |
| `REGISTROS_TREINAMENTO_TRIPULACAO` | Crew training records |
| `REGISTROS_CONTROLE_BORDO` | On-board control records |
| `DOCUMENTO_TECNICO_MATERIAL_REVESTIMENTO` | Lining material document |
| `LAUDO_ANALISE_POTABILIDADE` | Water potability report |
| `DECLARACAO_FORNECEDOR_AGUA_POTAVEL` | Water supplier declaration |
| `DOCUMENTO_CONTROLE_PRAGAS` | Pest control document |
| `REGISTROS_FOTOGRAFICOS` | Photographic records |

The prompts, the dossiers and the regulation are in Portuguese, the language of the cases.

## Files

| File | Content |
|---|---|
| `TUTORIAL.md` | Step-by-step instructions |
| `reproduce.py` | Recomputes the statistics of the paper from `results/counts.json` |
| `stats.py` | Exact binomial test, power, Wilson interval, exact McNemar test, Cohen's kappa |
| `simulator.py` | Synthetic dossiers, retrieval, prompts, decision and statistics |
| `prompts.py` | Prompt templates of every condition and of the draft opinions, verbatim |
| `regulation/passages.jsonl` | The 49 passages of the regulatory corpus, one JSON object per line (`file`, `label`, `text`) |
| `results/counts.json` | Aggregated counts of the study |
