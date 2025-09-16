from typing import Tuple
from .constants import DROPPED_COLS, TARGET
import pandas as pd
from sklearn.model_selection import train_test_split


def read_data(data_path: str) -> pd.DataFrame:
    df = pd.read_csv(data_path)
    df = df.drop(columns=DROPPED_COLS)
    return df


def split_data(
    df: pd.DataFrame,
    seed: int,
) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    labels = df[TARGET].values
    X = df.drop(columns=[TARGET])

    X_train, X_vtest, y_train, y_vtest = train_test_split(
        X, labels, test_size=0.2, random_state=seed, stratify=labels
    )

    X_val, X_test, y_val, y_test = train_test_split(
        X_vtest, y_vtest, test_size=0.5, random_state=seed, stratify=y_vtest
    )

    return X_train, y_train, X_val, y_val, X_test, y_test
