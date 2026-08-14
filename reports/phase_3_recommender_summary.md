# Phase 3 Recommender Evaluation Summary

## Model
This is a non-personalized item-to-item co-visitation recommender. For a viewed item, it ranks items that appeared in the same earlier session most often. It uses product interactions only and removes duplicate items within a session before counting co-visits.

## Evaluation design
The model trains on events before 2015-08-21 08:29:47.788+05:30. The final 28 days form a chronological holdout. Purchased-item retrieval uses the last uniquely timestamped different product view before a transaction as the anchor. Next-item retrieval is a broader secondary evaluation that uses a product view and the next uniquely timestamped different item interaction in the same held-out session. Equal-timestamp event order is not interpreted as behavioral order.

Each example has one target item, so HitRate@K is numerically equivalent to Recall@K. The report uses HitRate@K because it states the retrieval question directly. Both the co-visitation model and popularity baseline remove the current anchor item before selecting K candidates. The committed interval report uses 300 visitor-level bootstrap resamples for HitRate@10 uncertainty.

## Result
For purchased-item retrieval, co-visitation reaches HitRate@10 of 14.334%, compared with 1.069% for the anchor-excluded popularity baseline. Co-visitation coverage@10 is 80.564% for this selected evaluation population. In the broader next-item retrieval task, co-visitation reaches HitRate@10 of 27.959% compared with 0.416% for popularity.

The 50-item session cap limits pairwise computation. It truncates 275 of 1,433,867 training sessions; the committed session-length distribution reports the full context.

## Interpretation limits
These offline tasks measure historical item retrieval, not conversion lift, revenue lift, or relevance across all product-page impressions. Purchased-item retrieval is deliberately conditioned on a later transaction, while next-item retrieval broadens the population but still excludes one-item and tied-timestamp paths. A controlled experiment would be required before any causal product claim.
