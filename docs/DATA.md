# About dataset
## Source
[Kaggle](https://www.kaggle.com/datasets/radheshyamkollipara/bank-customer-churn/data)

## Feature Description
- RowNumber: corresponds to the record (row) number and has no effect on the output
- CustomerId: contains random values and has no effect on customer leaving the bank
- Surname: surname has no impact on the decision to leave the bank
- CreditScore: higher scores generally correlate with lower churn
- Geography: customer location can affect churn
- Gender: included for completeness; impact may vary
- Age: older customers are generally less likely to churn
- Tenure: number of years as a customer; longer tenure often correlates with lower churn
- Balance: higher balances often correlate with lower churn
- NumOfProducts: number of products a customer has purchased
- HasCrCard: whether the customer has a credit card
- IsActiveMember: whether the customer is considered active
- EstimatedSalary: similar to balance, higher salary often correlates with lower churn
- Exited: target label indicating whether the customer left the bank (0/1)
- Complain: whether the customer filed a complaint
- Satisfaction Score: satisfaction with complaint resolution
- Card Type: type of card held by the customer
- Point Earned: loyalty points earned by the customer

## Expected File Path
- The pipeline expects the CSV at `data/Customer-Churn-Records.csv`.
- Use `make data-up` to download via Kaggle CLI, or place the file manually under `data/`.
