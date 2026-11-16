# Tutorial

Steps 1 to 4 take about five minutes and need only Python 3.8 or later: no packages, no model, no network. Steps 5
and 6 are optional and use real models. What each file is, and why the real cases and the platform are not included,
is explained in [README.md](README.md).

| Step | What you do | Needs |
|---|---|---|
| 1 | Get the files | A browser |
| 2 | Check the statistics of the paper | Python |
| 3 | Run the experiment on fictitious dossiers | Python |
| 4 | Look inside one case: dossier, queries, passages, prompt | Python |
| 5 | Repeat step 3 with real models (optional) | Ollama, or another OpenAI-compatible endpoint |
| 6 | Vary the run (optional) | Python |

## 1. Get the files

Download the repository as a zip with the download button of the anonymous page, unzip it and open a terminal in the
unzipped folder. All commands below are run from that folder. On Windows, type `python` instead of `python3`.

## 2. Check the statistics of the paper

```
python3 reproduce.py
```

It runs in about a second and prints one block per part of the paper. The first block rebuilds Table 2 from the
confusion matrices in `results/counts.json`:

```
Table 2. Correct decisions on the 40 cases (suggested rejections)
  condition                  gemma       gpt    gemini    claude   exact binomial p against chance
  text                      20 (8)   20 (40)    20 (4)   20 (40)   1.000 1.000 1.000 1.000
  text_rag_fixed            21 (7)   20 (40)    20 (2)   20 (40)   0.875 1.000 1.000 1.000
  ...
  all_photos               14 (14)   20 (40)    21 (5)   20 (40)   0.081 1.000 0.875 1.000
  all_photos_checklist     15 (17)   20 (40)   20 (14)   20 (40)   0.154 1.000 1.000 1.000
  [ok] all 40 cells equal to the paper
```

Every other line has the form

```
  [ok] power to detect a true accuracy of 0.65 with 40 cases: paper 0.44, recomputed 0.44
```

where `paper` is the value printed in the paper and `recomputed` is the value obtained here from the counts. The last
line is `ALL VALUES MATCH THE PAPER`. If a value differed, its line would start with `[MISMATCH]` and the script would
exit with status 1.

Where each block is in the paper:

| Block of the output | Place in the paper |
|---|---|
| Table 2 | Table 2 |
| Chance level | Study Design, paragraph "Metrics"; caption of Table 2 |
| Tendencies of the models; Exact McNemar tests; Variation between three runs | Results, first paragraph |
| Retrieval | Results, paragraph on retrieval; abstract and conclusion |
| Requirement level | Results, paragraph "Requirement level" |
| Draft opinions | Draft Opinions and the Analysts' Opinions |
| First round | Results, first paragraph |

**Check one value by hand.** The smallest McNemar p-value of the paper is 0.092. In `results/counts.json`, under
`mcnemar_gemma_vs_model` → `gemini` → `all_photos`, the discordant pair is `[3, 10]`: with all the photos, Gemma was
right and Gemini wrong in 3 cases, and the opposite in 10. The test uses only these two numbers:

```
python3 -c "from stats import mcnemar_exact; print(round(mcnemar_exact(3, 10), 3))"
0.092
```

The functions are in `stats.py` (43 lines), so they can be compared with any statistics package.

**See a check fail.** Change one count in `results/counts.json`, for instance the `tp` of `decisions` → `gemma` →
`text` from 4 to 5, and run the script again. It reports the cells of Table 2 and the accuracy of Gemma as
`[MISMATCH]` and ends with `2 VALUE(S) DO NOT MATCH`. Restore the value afterwards.

## 3. Run the experiment on fictitious dossiers

```
python3 simulator.py
```

It takes a few seconds and prints three blocks. With the default seed the output is always the same:

```
Synthetic cases: 40 (20 approved, 20 rejected) written to out/cases; with a missing category: 8 approved, 4 rejected

Retrieval over the 49 passages of the regulation, embeddings: lexical TF-IDF (offline stand-in for bge-m3)
  passages per case: median 11.0, 8 to 13
  strategy                                      articles found   rate  distinct sets
  queries from the case (top 2 per query)           192 of 344  0.558             18
  fixed query, as many passages as the case         118 of 344  0.343              5
  fixed query, top 8                                118 of 344  0.343              1
  random draw of as many passages (expected)                    0.373

Decisions, model: completeness rule (offline stand-in for the LLM)
  condition               correct  rejections  no decision   accuracy [95% Wilson]   p against chance   citations (in the prompt)
  text                         16          12            0   0.400 [0.263, 0.554]          0.268              -
  text_rag_fixed               16          12            0   0.400 [0.263, 0.554]          0.268          0 (0)
  ...
```

How to read it:

- **Synthetic cases.** 40 fictitious dossiers were written to `out/cases/`, and their labels to `out/labels.csv`.
- **Retrieval.** `articles found` counts, over all document categories present in the dossiers, how often the
  retrieved passages include the article that establishes the requirement of the category. This is the measure
  behind "235 of 332" in the paper. `distinct sets` shows the difference between the two strategies: the queries
  taken from the case return different passages for different cases, while the fixed query returns the same eight
  passages for every case.
- **Decisions.** One line per condition, with the columns of Table 2 (`correct`, `rejections`) and the tests of the
  paper. `citations (in the prompt)` counts the `[Source: file, Art. N]` markers of the answers and, in parentheses,
  those that point to a passage that was in the prompt.

In this offline run two parts are stand-ins, and the output says so: TF-IDF vectors replace the embedding model, and
the completeness rule of the paper replaces the LLM. The rule ignores the regulatory context, so all conditions give
the same decisions here; they differ in step 5, with a real model. These numbers describe the fictitious dossiers,
not the cases of the paper.

## 4. Look inside one case

The run of step 3 left everything it used in `out/`:

| Path | Content |
|---|---|
| `out/cases/S002.txt` | A fictitious dossier: a header and one `### CATEGORY \| file` section per document |
| `out/labels.csv` | Label of each case, its missing categories and its defective documents |
| `out/example_prompts/<condition>.txt` | The complete prompt of the first case in each condition |
| `out/runs/<condition>.jsonl` | For each case: label, decision, passages retrieved and the answer |

Open `out/cases/S002.txt`. According to `out/labels.csv`, this case is rejected because its water supplier
declaration is defective: the document is an invoice for diesel fuel.

The queries that retrieval takes from this dossier, one for the header and one per section (first 75 characters):

```
python3 -c "import simulator as s; [print(repr(q[:75])) for q in s.section_queries(open('out/cases/S002.txt', encoding='utf-8').read())]"
```

The passages retrieved for it with these queries:

```
python3 -c "import json; r = [json.loads(l) for l in open('out/runs/text_rag_case.jsonl', encoding='utf-8')][1]; print('\n'.join(r['retrieved']))"
```

The prompts sent to the model: compare `out/example_prompts/text.txt` (no regulatory context) with
`out/example_prompts/text_rag_case.txt` (passages retrieved from the case, placed before the dossier, and the
citation request next to the final instruction). `text_full_regulation.txt` carries all 49 passages. The templates of
the photo conditions and of the draft opinions are in `prompts.py`.

The regulatory corpus, one line per passage:

```
python3 -c "import json; [print(p['file'], '|', p['label'], '|', len(p['text']), 'characters') for p in map(json.loads, open('regulation/passages.jsonl', encoding='utf-8'))]"
```

## 5. Optional: real models

The simulator accepts any endpoint that implements the OpenAI routes `/embeddings` and `/chat/completions`. We ran
it with [Ollama](https://ollama.com), which served the open models of the study.

```
OLLAMA_CONTEXT_LENGTH=65536 ollama serve       # in one terminal; the study used a 65,536-token context
ollama pull bge-m3                             # in another terminal: the embedding model of the study
ollama pull gemma4:12b                         # or another model; the study used gemma4:26b on a 24 GB workstation
```

**Embeddings only** (under a minute). Retrieval now uses the embedding model of the study; the decision still comes
from the rule:

```
python3 simulator.py --embed-url http://localhost:11434/v1 --embed-model bge-m3 --conditions text
```

```
Retrieval over the 49 passages of the regulation, embeddings: bge-m3 at http://localhost:11434/v1
  passages per case: median 9.0, 7 to 12
  strategy                                      articles found   rate  distinct sets
  queries from the case (top 2 per query)           188 of 344  0.547             28
  fixed query, as many passages as the case         156 of 344  0.453              6
  fixed query, top 8                                156 of 344  0.453              1
  random draw of as many passages (expected)                    0.305
  fixed query: the first 49 of the 49 positions of the ranking equal the ranking obtained in the study
```

The last line is the check that ties the simulator to the platform: for the fixed query, the simulator ranks the 49
passages in the same order as the platform did in the study.

**Embeddings and model.** Each answer took about 40 seconds with a 12B model on our workstation, so start with a few
cases and two conditions:

```
python3 simulator.py --n 6 --conditions text,text_rag_case \
    --embed-url http://localhost:11434/v1 --embed-model bge-m3 \
    --llm-url http://localhost:11434/v1 --llm-model gemma4:12b --reasoning-effort none
```

The decisions now come from the model, the conditions can differ, and the last column counts the citations of the
regulation. The answers are in `out/runs/<condition>.jsonl`. `--reasoning-effort none` turns the reasoning of the
model off, as in the study.

**Hosted models.** Pass the base URL of the service in `--llm-url` (and `--embed-url`), the model name in
`--llm-model`, and put the key in the environment variable `LLM_API_KEY`. We tested the script with Ollama only; a
service works if it accepts `temperature` and `max_tokens` in `/chat/completions`.

## 6. Optional: vary the run

```
python3 simulator.py --n 100 --seed 7                              # other fictitious cases
python3 simulator.py --conditions text,text_checklist --out out2   # chosen conditions, another output folder
python3 simulator.py --help                                        # all options
```

The conditions available in the simulator are the five without photographs: `text`, `text_rag_fixed`,
`text_rag_case`, `text_full_regulation` and `text_checklist`.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `ModuleNotFoundError: No module named 'stats'` | Run the commands from the folder of the repository, without the `-I` option of Python |
| `warning: N answer(s) cut by the token limit` | The context window of the model server is too small for the prompt. With Ollama, start the server with `OLLAMA_CONTEXT_LENGTH=65536` |
| The column `no decision` is not zero | The answer did not end with the recommendation line. As in the paper, it counts as an error; read the answer in `out/runs/` |
| HTTP error 400 with `--reasoning-effort` | The endpoint does not accept the parameter; remove the option |
| HTTP error 404 | The base URL must end in `/v1` for Ollama |
| Step 3 prints other numbers | The numbers above are for the default `--n 40 --seed 2027` in offline mode; we obtained them with Python 3.9 and 3.14 |
