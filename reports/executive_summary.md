# Executive Summary

## Decision context

This case study examines whether session-level e-commerce behavior and a simple co-visitation recommender justify a controlled ranking experiment. RetailRocket provides observational clickstream data only; it contains neither recommendation exposures nor randomized variants.

## Evidence from the analysis

- **Funnel opportunity:** session-level analysis shows the largest observed loss occurs before add-to-cart. These logs do not identify its cause; product relevance is one hypothesis alongside price, availability, traffic quality, and shopper intent.
- **Model signal:** on a chronological 28-day holdout, purchased-item HitRate@10 is 14.334% for co-visitation and 1.069% for an anchor-excluded popularity baseline. Visitor-bootstrap 95% intervals are 11.821%–17.321% and 0.659%–1.557%, respectively.
- **Broader retrieval check:** next-item HitRate@10 is 27.959% for co-visitation and 0.416% for popularity. The tasks answer different retrieval questions and are not conversion metrics.
- **Candidate availability:** purchased-item coverage@10 is 80.564%. The detailed evaluation setup and uncertainty outputs are in the Phase 3 reports.
- **Experiment readiness:** the Phase 4 report provides illustrative sample-size planning. Production eligibility and qualified-assignment traffic must be measured before estimating experiment duration.

## Recommendation

Do not infer conversion impact from the offline result. Use the co-visitation model as the treatment in a controlled test against a popularity-ranking control, with identical placement and presentation. Randomize eligible visitors persistently, analyze the first qualified assignment using intent to treat, and monitor render-success and latency guardrails.

## What would change the decision

- **Advance:** the treatment's primary-conversion confidence-interval lower bound clears the pre-specified minimum practical effect, and guardrails pass.
- **Hold or revise:** the primary interval does not clear the practical threshold, candidate coverage is too low in production, or rendering/performance guardrails regress.

## Limits

The recommender was not deployed. The Phase 5 A/B report uses fabricated counts solely to demonstrate the analysis workflow and must not be presented as an observed experiment result.
