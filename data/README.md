# Data

## Primary dataset
RetailRocket E-commerce Dataset

## Source
https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset

## Files used
- `events.csv`: visitor interactions (`view`, `addtocart`, `transaction`)
- `category_tree.csv`: category hierarchy
- `item_properties_part1.csv` and `item_properties_part2.csv`: time-varying item properties

## Storage policy
Raw data is downloaded manually to `data/raw/retailrocket/` and is excluded from GitHub via `.gitignore`.

## Important limitations
RetailRocket is observational clickstream data. It does not contain a randomized treatment/control assignment, and most item properties are hashed. It cannot prove that a recommendation causes a business outcome.

## Session and ordering conventions
- A new session starts only when the inactivity gap is **greater than** 30 minutes. An exact 30-minute gap remains in the same session.
- There are 2,143 visitor-timestamp tie groups in this dataset (4,769 events), including 12 groups with more than one event type. The pipeline uses deterministic secondary sorting for reproducibility, but strict funnel steps and recommender evaluation labels require a strictly later timestamp. Tied events are not interpreted as observed behavioral ordering.
