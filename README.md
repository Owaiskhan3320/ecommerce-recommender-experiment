# E-commerce Product Analytics and Recommendation Experiment Case Study

An end-to-end data science case study using the RetailRocket clickstream dataset. The project moves from raw-event quality checks to a session funnel, an offline item-to-item recommender evaluation, and a production-oriented experiment design.

## Business question

Where does the purchase journey lose shoppers, and is a simple item-to-item recommender promising enough to justify a controlled product experiment?

## What I built

- A DuckDB SQL pipeline that removes exact duplicates, sessionizes behavior with a 30-minute inactivity rule, and creates session, visitor, and item marts.
- Product-funnel analysis using a strict event sequence: product view → add-to-cart → transaction.
- A co-visitation item-to-item recommender evaluated on a chronological 28-day holdout against a global-popularity baseline.
- A recommender A/B-test design with eligibility, persistent assignment, intent-to-treat analysis, guardrails, and sample-size scenarios.
- A clearly labeled synthetic A/B-analysis exercise that demonstrates sample-ratio checks, confidence intervals, and a pre-specified decision rule.

## Key findings

| Area | Result | Interpretation |
| --- | ---: | --- |
| Funnel | 1,755,781 sessions viewed a product; 2.089% then added to cart | The largest observed drop is between product view and cart. |
| Funnel | 0.611% completed the strict view → cart → transaction sequence | This is descriptive behavior, not causal evidence. |
| Recommender | Purchased-item HitRate@10: 14.334% co-visitation vs 1.069% popularity | Both rankings exclude the current anchor item. |
| Recommender coverage | Purchased-item coverage@10: 80.564% | The model needs a fallback for rare or new items. |
| Broader retrieval | Next-item HitRate@10: 27.959% co-visitation vs 0.416% popularity | This uses the first held-out view in sessions with a later distinct item. |
| Experiment planning | Illustrative 20% lift scenario: 70,222 assigned visitors per arm | Recalculate with qualified production traffic before launch. |

Read the concise decision summary in [reports/executive_summary.md](reports/executive_summary.md).

## Methods and boundaries

### Real-data analysis

- **Dataset:** RetailRocket e-commerce clickstream data; raw files are excluded from the repository. See [data/README.md](data/README.md) for setup and source information.
- **Sessionization:** events are grouped into sessions after an inactivity gap greater than 30 minutes; an exact 30-minute gap remains in the same session.
- **Timestamp ties:** strict funnel steps and recommender labels require strictly later timestamps, rather than treating deterministic secondary sorting as observed behavior.
- **Offline evaluation:** the model trains on events before the final 28 days. It reports a selected purchased-item task and a broader next-item task separately.
- **Baseline:** a global-popularity ranking uses the same historical training period.

### What this project does not claim

- The recommender was deployed or improved conversion in production.
- Offline HitRate@K proves business impact.
- Observational clickstream patterns prove causality.
- The synthetic A/B scenario is a real customer experiment.

Only a randomized experiment with production exposure logging can estimate causal impact. The design for that experiment is in [reports/phase_4_experiment_design.md](reports/phase_4_experiment_design.md).

## Repository structure

```text
data/       Dataset instructions; raw and processed data stay local
docs/       Scope and analytical boundaries
notebooks/  Executed exploratory data-understanding notebook
reports/    Reproducible figures, metrics, summaries, and experiment plan
sql/        Staging, sessionization, and analytical marts
src/        Pipeline and analysis scripts
tests/      SQL, recommender, experiment-planning, and A/B-analysis tests
```

## Reproduce the project

### 1. Create the environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On macOS or Linux:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

To open the exploratory notebook, install the optional notebook tools:

```powershell
python -m pip install -r requirements-notebook.txt
```

### 2. Add the raw data

Download the RetailRocket files described in [data/README.md](data/README.md) and place them here:

```text
data/raw/retailrocket/events.csv
data/raw/retailrocket/category_tree.csv
data/raw/retailrocket/item_properties_part1.csv
data/raw/retailrocket/item_properties_part2.csv
```

Only `events.csv` is required to run the current analytical pipeline. The raw files and generated DuckDB database are ignored by Git.

### 3. Run the full pipeline

```powershell
python src/run_all.py
```

This rebuilds the DuckDB analytical database and refreshes the Phase 1–5 reports. The recommender evaluation is the slowest step because it processes the full training history.

### 4. Run the checks

```powershell
python -m unittest discover -s tests -v
```

## Project flow

1. **Data understanding:** inspect schema, event mix, duplicates, sessionization sensitivity, and activity distributions.
2. **Product analytics:** quantify strict funnel loss and describe first-versus-later session behavior.
3. **Recommender evaluation:** build a co-visitation baseline and compare it with popularity on a time-based holdout.
4. **Experiment design:** specify the control, treatment, assignment, metrics, guardrails, and sample-size scenarios for a live test.
5. **Synthetic A/B analysis:** demonstrate how the pre-specified analysis would be applied without presenting fabricated results as real.

## Main outputs

- [Phase 2 funnel summary](reports/phase_2_product_analysis_summary.md)
- [Phase 3 recommender summary](reports/phase_3_recommender_summary.md)
- [Phase 4 experiment design](reports/phase_4_experiment_design.md)
- [Phase 5 synthetic A/B analysis](reports/phase_5_synthetic_ab_summary.md)
