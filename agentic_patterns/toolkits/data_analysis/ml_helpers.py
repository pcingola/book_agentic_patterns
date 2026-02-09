"""ML helper functions for classification and regression operations."""

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


def detect_model_type(target_series: pd.Series) -> str:
    """Auto-detect classification vs regression based on target column."""
    if not pd.api.types.is_numeric_dtype(target_series):
        return "classification"
    unique_ratio = target_series.nunique() / len(target_series)
    if unique_ratio < 0.05:
        return "classification"
    return "regression"


def train_and_fit_classifier(df: pd.DataFrame, target: str, features: list[str] | None, test_size: float, model, **kwargs) -> dict:
    """Train a classifier and return metrics."""
    if features is None:
        features = [col for col in df.columns if col != target]
    x = df[features]
    y = df[target]

    non_numeric = [col for col in x.columns if not pd.api.types.is_numeric_dtype(x[col])]
    if non_numeric:
        raise ValueError(
            f"Feature columns {non_numeric} contain non-numeric data. "
            f"Please preprocess these columns (e.g., use one-hot encoding) before training."
        )

    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=test_size, random_state=kwargs.get("random_state"))
    model.fit(x_train, y_train)
    y_pred = model.predict(x_test)
    return {
        "model": model,
        "accuracy": accuracy_score(y_test, y_pred),
        "classification_report": classification_report(y_test, y_pred),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "features": features,
        "target": target,
        "test_size": test_size,
    }


def train_and_fit_regressor(df: pd.DataFrame, target: str, features: list[str] | None, test_size: float, model, **kwargs) -> dict:
    """Train a regressor and return metrics."""
    if features is None:
        features = [col for col in df.columns if col != target]
    x = df[features]
    y = df[target]

    non_numeric = [col for col in x.columns if not pd.api.types.is_numeric_dtype(x[col])]
    if non_numeric:
        raise ValueError(
            f"Feature columns {non_numeric} contain non-numeric data. "
            f"Please preprocess these columns (e.g., use one-hot encoding) before training."
        )

    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=test_size, random_state=kwargs.get("random_state"))
    model.fit(x_train, y_train)
    y_pred = model.predict(x_test)
    mse = mean_squared_error(y_test, y_pred)
    return {
        "model": model,
        "mse": mse,
        "rmse": np.sqrt(mse),
        "mae": mean_absolute_error(y_test, y_pred),
        "r2": r2_score(y_test, y_pred),
        "features": features,
        "target": target,
        "test_size": test_size,
    }
