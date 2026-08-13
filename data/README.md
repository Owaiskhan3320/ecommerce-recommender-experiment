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
