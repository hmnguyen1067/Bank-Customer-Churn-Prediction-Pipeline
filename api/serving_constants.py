CATEGORICAL_FEATURES: list[str] = [
    "Geography",
    "Gender",
    "NumOfProducts",
    "HasCrCard",
    "IsActiveMember",
    "Satisfaction Score",
    "Card Type",
]

NUMERICAL_FEATURES: list[str] = [
    "CreditScore",
    "Age",
    "Tenure",
    "Balance",
    "EstimatedSalary",
    "Point Earned",
]

PREPROCESSOR_MODEL_NAME: str = "ChurnDataPreprocessor"
XGB_MODEL_NAME: str = "XGBoostChurnModel"
MLFLOW_TRACKING_URI: str = "http://localhost:5000"
