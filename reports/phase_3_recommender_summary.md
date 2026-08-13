# Phase 3 Recommender Evaluation Summary

## Model
This is a non-personalized item-to-item co-visitation recommender. For a viewed item, it ranks items that appeared in the same earlier session most often. It uses product interactions only and removes duplicate items within a session before counting co-visits.

## Evaluation design
The model trains on events before 2015-08-21 08:29:47.788+05:30. The final 28 days form a chronological holdout. Each holdout example uses the last different product viewed before a transaction as the anchor and asks whether the purchased item is in the recommendations. This avoids training on future events.

## Result
The co-visitation recommender reaches Recall@10 of 14.334% across eligible holdout purchase examples, compared with 1.069% for a global popularity baseline. It can produce at least one recommendation for 90.671% of those examples.

## Interpretation limits
Recall here measures whether a later purchased item is retrieved after a prior view in historical logs. It does not estimate conversion lift, revenue lift, relevance to every shopper, or the effect of showing recommendations in a product interface. A controlled experiment would be needed for those claims.
