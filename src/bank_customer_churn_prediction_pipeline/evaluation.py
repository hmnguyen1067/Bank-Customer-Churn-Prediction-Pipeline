import mlflow
import pandas as pd
import numpy as np 
import xgboost as xgb
import matplotlib

from .constants import TARGET, PREDICTION_COL
from .training import make_predictions

matplotlib.use('Agg')

def evaluate_shap(model, preprocessor, X_test, y_test):
    def model_predict(input):
        preds = model.predict(xgb.DMatrix(input))
        
        return np.clip(np.rint(preds), 0, 1).astype(int)

    with mlflow.start_run():
        shap_config = {
            "log_explainer": True,  # Save the explainer model
            "explainer_type": "exact",  # Use exact SHAP values (slower but precise)
            "max_error_examples": 100,  # Number of error cases to explain
            "log_model_explanations": True,  # Log individual prediction explanations
        }

        eval_data = preprocessor.transform(X_test)

        result = mlflow.models.evaluate(
            model=model_predict,
            data=eval_data,
            targets=y_test,
            feature_names=preprocessor.get_feature_names_out(),
            model_type="classifier",
            evaluator_config=shap_config,
        )

        print(f"Model accuracy: {result.metrics['accuracy_score']:.3f}")
        print("Generated SHAP artifacts:")
        for name, path in result.artifacts.items():
            if "shap" in name:
                print(f"  {name}: {path}")