# Phase 5 Synthetic A/B Analysis

## Synthetic-data statement
**Every count in this report is deliberately fabricated for an analysis demonstration.** The RetailRocket dataset contains observational behavior only and did not provide experiment assignments, module exposures, or treatment outcomes.

## Scenario
The fixed scenario assigns 75,000 eligible visitors to each variant. It mirrors the Phase 4 design: control receives a global-popularity ranking and treatment receives a co-visitation ranking. The results are not sampled from customer data and do not estimate business impact.

## Data-quality check
The 50/50 assignment check has p = 1.000000. With the pre-specified threshold of 0.01, the synthetic assignment passes the sample-ratio check.

## Intent-to-treat primary analysis
Control conversion is 0.640%; treatment conversion is 0.789%. The synthetic treatment-control difference is 0.149% (23.3% relative lift), with a Newcombe 95% score interval of [0.064%, 0.235%] and a pooled two-proportion z-test p-value of 0.000597.

## Guardrail
The treatment-control render-success difference is -0.049%. Its 95% confidence interval lower bound is -0.107%, compared with the pre-specified non-inferiority limit of -0.2%.

## Decision exercise
Would not meet the pre-specified decision rule in a real experiment. The 20% practical lift is a decision threshold in this synthetic exercise; it is distinct from the minimum detectable effect used for power planning. This statement describes only how the rule would be applied to the fabricated scenario. It is not a deployment recommendation and must not be represented as a live A/B-test outcome.
