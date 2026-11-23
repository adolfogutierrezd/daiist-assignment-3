# Assignment 3 Report

- **Name**: Adolfo Gutierrez de Gandarilla Domínguez
- **Student ID**: 19003
- **Group**: BBADBA 5B

## Use case

**Who asks.** Staff of Spanish sports clubs, federations and event
organisers who are not lawyers: club managers, team delegates, federation
administrators, organisers of a race or a match. They ask practical questions
about their legal obligations, for example *"¿Qué sanción tiene un club si sus
aficionados lanzan objetos al campo?"*, *"¿Puede un deportista negarse a un
control de dopaje fuera de competición?"* or *"¿Qué requisitos tiene una
competición para ser oficial?"*. Questions and answers are in Spanish, like
the laws.

**What they do with the answer.** They decide what to do next: prepare a
document, accept or refuse a request, warn an athlete, or call the
federation's lawyer.

**What a wrong answer costs compared with "I don't know".**

| Answer | What happens | Rough cost |
|---|---|---|
| Correct, with citation | They act correctly and can check the article cited | Saves a lawyer's consultation (~€150) |
| **"The laws I have don't answer this, ask a lawyer / the federation"** | One consultation with a lawyer or the federation | **~€150 and a few days** |
| **Wrong but confident** | They act on it: an event without the required measures, a missed deadline, an athlete told something false about doping controls | **Fines from a few thousand to hundreds of thousands of euros, a club sanctioned, an athlete banned for years** |

A confident wrong answer is **far worse** than a refusal, so the assistant
must **only answer from the text of the laws, cite the article for every
claim, and say "I don't know" whenever the laws it has don't cover the
question**. A useful refusal is a success, not a failure. This is why the
evaluation counts wrong answers and unsupported claims separately from
refusals, and why the ship decision looks first at how often it makes things
up.

**What it is not.** It is not legal advice and it doesn't know case law,
regional laws or federation rules, only the three national laws below.

## Corpus

Three Spanish national laws on sport, downloaded as **consolidated
text** (the current version, with all amendments applied) from the open-data
API of the *Boletín Oficial del Estado* (BOE). The API returns the law already
divided into blocks (preamble, headings, articles), each with its title.

| Document | BOE identifier and URL | Published | Consolidated text updated | Licence | Words (current text, without preamble) |
|---|---|---|---|---|---|
| Ley 39/2022, de 30 de diciembre, del Deporte | [BOE-A-2022-24430](https://www.boe.es/buscar/act.php?id=BOE-A-2022-24430) | 31/12/2022 | 19/11/2026 | Not subject to copyright; BOE reuse conditions | ~40,700 |
| Ley Orgánica 11/2021, de 28 de diciembre, de lucha contra el dopaje en el deporte | [BOE-A-2021-21650](https://www.boe.es/buscar/act.php?id=BOE-A-2021-21650) | 29/12/2021 | 20/12/2025 | Not subject to copyright; BOE reuse conditions | ~28,700 |
| Ley 19/2007, de 11 de julio, contra la violencia, el racismo, la xenofobia y la intolerancia en el deporte | [BOE-A-2007-13408](https://www.boe.es/buscar/act.php?id=BOE-A-2007-13408) | 12/07/2007 | 19/12/2025 | Not subject to copyright; BOE reuse conditions | ~14,400 |
| **Total** | | | | | **~83,800** |

**Licence.** Laws and regulations are **excluded from copyright** in Spain
(article 13 of the *Ley de Propiedad Intelectual*: *"No son objeto de
propiedad intelectual las disposiciones legales o reglamentarias…"*), and
the BOE allows its content to be reused provided the source and the date of
the version are cited. The texts contain **no personal data** (only the
names of the King and the ministers who signed them, in the signature block,
which I drop).

**Why these three.** Together they cover the main legal obligations of a
club or federation: how sport is organised (licences, competitions,
federations, sports justice), anti-doping (controls, sanctions, health of
athletes), and violence and racism at events (security measures, sanctions
for clubs and spectators).

**Why I leave out the preambles.** The preamble explains *why* the law was
made but contains no binding rule. It mentions many of the topics without
stating the rule, so it would compete with the actual articles in the search
and could lead to unsupported answers. It also saves embedding quota.
Including the preambles, the three texts have ~100,700 words.

## Ingestion

*How you extract, clean and chunk; one extraction problem you fixed; chunk metadata; number of chunks.*

## Test set

*How you wrote it, counts by kind, two examples.*

## Retrieval

*Hit rate at 1/3/5 per design, words added to the prompt, the design you chose.*

## Tools and subagent

*Your tools' descriptions, one search result, the subagent's instructions, one transcript from your editor.*

## Adding a document

*What happens when a document is already indexed. The unanswerable question, the document you added, the answer before and after.*

## Harness and guardrails

*Your AGENTS.md rules, the approval step, and your extra guardrail with one case where it fired.*

## Evaluation

*Code checks, the judge's rubric, your agreement with the judge, and results: correct, unsupported, correct refusals, wrong refusals.*

## Failures

*Failed questions by cause, with counts, and what to fix first.*

## Decision

*Would you let users rely on it, for what, with which safeguard? Cost and latency per question.*

## AI use

*What you used and how, or "none".*
