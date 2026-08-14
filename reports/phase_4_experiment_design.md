# Phase 4 Recommender Experiment Design

## Status
**Planning only. No A/B test was run for this project.** The historical clickstream is used to set directional sample-size scenarios; it is not treated as causal evidence.

## Decision question
Does a co-visitation recommendation module improve purchase conversion compared with a global-popularity module when both occupy the same product-page location?

## Variants
- **Control:** the top 10 globally popular, currently valid items in the recommendation slot.
- **Treatment:** the top 10 valid co-visitation candidates for the item currently viewed.
- Keep placement, number of tiles, visual treatment, lazy-loading behavior, and tracking identical. This isolates ranking logic rather than the effect of adding a new page component.

## Eligibility and assignment
- Qualify a visitor on their first product-detail-page view where the treatment can return 10 valid candidate items.
- Exclude bots and internal traffic using rules frozen before analysis. Keep failed renders in the assigned population and report them as a guardrail.
- Assign eligible visitors 50/50 by a stable hash of an anonymous visitor or device identifier. Persist the assignment across visits.
- Analyze only the first qualified assignment per visitor, by assigned variant (intent to treat), even if the module fails to render or the visitor does not click a recommendation.

## Metrics
- **Primary:** purchase conversion in the assignment session, defined as a transaction after the first qualified assignment divided by eligible assigned visitors.
- **Secondary:** recommendation click-through rate, add-to-cart rate after exposure, and revenue per exposed visitor if order value is available.
- **Guardrails:** module-render success, recommendation latency, product-page exit rate, and any support or error-rate signals available in production.

## Hypotheses and decision rule
- **Null hypothesis:** treatment and control have equal primary conversion rates.
- **Alternative:** the conversion rates differ. Use a two-sided 5% test and report the absolute conversion difference with a 95% confidence interval.
- Use the 20% relative minimum detectable effect only for sample-size planning. Before launch, separately set a minimum practical effect for the business decision and require the primary confidence interval to clear that threshold while guardrails remain within pre-set limits. Do not stop early for a favorable interim result.

## Sample-size scenarios
The planning proxy is the historical strict view-to-transaction rate: 10,721 purchase sessions from 1,755,781 product-view sessions (0.611%) over 139 calendar days. This is not the final experimental baseline because production eligibility and first-exposure measurement will differ.

For an illustrative 20% relative-lift scenario, the two-sided calculation requires 70,222 eligible assigned visitors per variant (140,444 total). Historical product-view volume implies roughly 12 days to reach that count; the plan enforces at least 14 days to cover weekly behavior. This is a sizing illustration, not a real traffic forecast; recalculate from actual qualified-assignment traffic before launch.

## Required production logging
Record `experiment_id`, `variant`, `visitor_id`, `session_id`, `exposure_time`, `anchor_itemid`, ranked candidate item IDs, render status, candidate clicks, add-to-cart events, and transactions. Log the assignment before rendering so the intent-to-treat population is recoverable.

## Interpretation boundary
An offline HitRate@10 advantage justifies testing the ranking. Only this randomized experiment can estimate the module's causal impact on the defined conversion metric.
