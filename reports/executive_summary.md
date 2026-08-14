# Executive Summary

## Decision context

This case study examines whether the observed e-commerce purchase funnel and a simple co-visitation recommender justify a controlled ranking experiment. The source is RetailRocket's observational clickstream data; it does not contain recommendation exposures or randomized variants.

## Evidence from the analysis

- **Funnel opportunity:** 1,755,781 sessions included a product view, but only 36,675 continued to an add-to-cart after viewing (2.089%). The strict view-to-transaction rate was 0.611%.
- **Model signal:** on a chronological 28-day holdout, purchased-item HitRate@10 was 14.334% for co-visitation and 1.069% for an anchor-excluded global-popularity baseline. Visitor-bootstrap 95% intervals were 11.824%–17.555% and 0.709%–1.537%, respectively.
- **Broader retrieval check:** next-item HitRate@10 was 27.959% for co-visitation and 0.416% for popularity. The two evaluation tasks answer different questions and should not be treated as a conversion metric.
- **Candidate availability:** purchased-item coverage@10 was 80.564%. The 50-item co-visitation cap truncated 275 of 1,433,867 training sessions (0.019%).
- **Experiment readiness:** an illustrative 20% relative-lift sizing scenario requires 70,222 eligible assigned visitors per variant at 80% power and two-sided alpha of 0.05. Historical volume suggests about 12 days to sample size, with a 14-day minimum to cover weekly behavior; this is not a production traffic forecast.

## Recommendation

Do not infer conversion impact from the offline result. Use the co-visitation model as the treatment in a controlled test against a popularity-ranking control, with identical placement and presentation. Randomize eligible visitors persistently, analyze the first qualified assignment using intent to treat, and monitor render-success and latency guardrails.

## What would change the decision

- **Advance:** the treatment's primary-conversion confidence interval is fully positive, the observed lift meets the pre-specified threshold, and guardrails pass.
- **Hold or revise:** the interval crosses zero, the candidate-coverage rate is too low in production, or rendering/performance guardrails regress.

## Limits

The recommender was not deployed. The Phase 5 A/B report uses fabricated counts solely to demonstrate the analysis workflow and must not be presented as an observed experiment result.
