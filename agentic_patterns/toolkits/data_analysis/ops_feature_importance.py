"""Feature importance operations registry and helper functions."""

import logging

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.calibration import LabelEncoder
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression

from agentic_patterns.toolkits.data_analysis.ml_helpers import detect_model_type
from agentic_patterns.toolkits.data_analysis.models import OperationConfig

logger = logging.getLogger(__name__)


class UnencodableColumnError(Exception):
    """Raised when a column cannot be encoded to numeric format."""

    def __init__(self, msg: str, column: str):
        self.column = column
        super().__init__(msg)


def encode_non_numeric_features(x: pd.DataFrame) -> pd.DataFrame:
    """Encode non-numeric features (datetime -> timestamp, string -> label encoding)."""
    x_encoded = x.copy()
    non_numeric_cols = [col for col in x.columns if not pd.api.types.is_numeric_dtype(x[col])]

    for col in non_numeric_cols:
        try:
            if pd.api.types.is_datetime64_any_dtype(x[col]):
                x_encoded[col] = x[col].astype("int64") / 10**9
            else:
                sample_value = x[col].dropna().iloc[0] if not x[col].dropna().empty else None
                if sample_value is not None and isinstance(sample_value, list | dict | tuple | set):
                    raise UnencodableColumnError(
                        f"Column '{col}' contains complex types ({type(sample_value).__name__}) that cannot be encoded.",
                        col,
                    )
                encoder = LabelEncoder()
                x_encoded[col] = encoder.fit_transform(x[col].astype(str))
        except UnencodableColumnError:
            raise
        except Exception as e:
            raise UnencodableColumnError(f"Failed to encode column '{col}': {e}", col) from e

    return x_encoded


def gradient_boosting_feature_importance(
    df: pd.DataFrame, target: str, features: list[str] | None = None, model_type: str | None = None, n_estimators: int = 100, random_state: int = 42,
) -> pd.DataFrame:
    """Calculate feature importance using Gradient Boosting."""
    if features is None:
        features = [col for col in df.columns if col != target]
    x = df[features]
    y = df[target]

    try:
        x = encode_non_numeric_features(x)
    except UnencodableColumnError as e:
        raise ValueError(f"Features can't be numerically encoded: {e.column}") from e

    if model_type is None:
        model_type = detect_model_type(y)
    model = GradientBoostingClassifier(n_estimators=n_estimators, random_state=random_state) if model_type == "classification" else GradientBoostingRegressor(n_estimators=n_estimators, random_state=random_state)

    try:
        model.fit(x, y)
    except Exception as e:
        raise ValueError(f"Failed to fit gradient boosting model (model_type={model_type!r}): {e}") from e

    importance_df = pd.DataFrame({"feature": features, "importance": model.feature_importances_})
    return importance_df.sort_values("importance", ascending=False)


def linear_feature_importance(df: pd.DataFrame, target: str, features: list[str] | None = None) -> pd.DataFrame:
    """Calculate feature importance using linear model coefficients and p-values."""
    if features is None:
        features = [col for col in df.columns if col != target]
    x = df[features]
    y = df[target]

    if not pd.api.types.is_numeric_dtype(y):
        try:
            label_encoder = LabelEncoder()
            y = pd.Series(label_encoder.fit_transform(y), index=y.index)
        except Exception as e:
            raise ValueError(f"Target column '{target}' contains non-numeric data that cannot be converted: {e}") from e

    non_numeric = [col for col in features if not pd.api.types.is_numeric_dtype(x[col])]
    if non_numeric:
        raise ValueError(f"Feature columns {non_numeric} contain non-numeric data. Preprocess before using linear feature importance.")

    model = LinearRegression()
    model.fit(x, y)

    x_with_const = sm.add_constant(x)
    sm_model = sm.OLS(y, x_with_const).fit()
    summary = sm_model.summary2().tables[1]

    importance_df = pd.DataFrame({
        "feature": x.columns,
        "coefficient": model.coef_,
        "std_error": summary["Std.Err."].values[1:],
        "p_value": summary["P>|t|"].values[1:],
        "importance": np.abs(model.coef_),
    })
    return importance_df.sort_values("importance", ascending=False)


def permutation_feature_importance_fn(
    df: pd.DataFrame, target: str, features: list[str] | None = None, model_type: str = "regression", n_estimators: int = 50, n_repeats: int = 10, random_state: int = 42,
) -> pd.DataFrame:
    """Calculate permutation feature importance."""
    if features is None:
        features = [col for col in df.columns if col != target]
    x = df[features]
    y = df[target]

    try:
        x = encode_non_numeric_features(x)
    except UnencodableColumnError as e:
        raise ValueError(f"Features can't be numerically encoded: {e.column}") from e

    model = RandomForestClassifier(n_estimators=n_estimators, random_state=random_state) if model_type == "classification" else RandomForestRegressor(n_estimators=n_estimators, random_state=random_state)

    try:
        model.fit(x, y)
    except Exception as e:
        raise ValueError(f"Failed to fit model for model_type={model_type!r}: {e}") from e

    perm = permutation_importance(model, x, y, n_repeats=n_repeats, random_state=random_state)
    importance_df = pd.DataFrame({"feature": features, "importance": perm.importances_mean, "std": perm.importances_std})
    return importance_df.sort_values("importance", ascending=False)


def random_forest_feature_importance(
    df: pd.DataFrame, target: str, features: list[str] | None = None, model_type: str | None = None, n_estimators: int = 100, random_state: int = 42,
) -> pd.DataFrame:
    """Calculate feature importance using Random Forest."""
    if features is None:
        features = [col for col in df.columns if col != target]
    x = df[features]
    y = df[target]

    try:
        x = encode_non_numeric_features(x)
    except UnencodableColumnError as e:
        raise ValueError(f"Features can't be numerically encoded: {e.column}") from e

    if model_type is None:
        model_type = detect_model_type(y)
    model = RandomForestClassifier(n_estimators=n_estimators, random_state=random_state) if model_type == "classification" else RandomForestRegressor(n_estimators=n_estimators, random_state=random_state)

    try:
        model.fit(x, y)
    except Exception as e:
        raise ValueError(f"Failed to fit random forest model (model_type={model_type!r}): {e}") from e

    importance_df = pd.DataFrame({"feature": features, "importance": model.feature_importances_})
    return importance_df.sort_values("importance", ascending=False)


FEATURE_IMPORTANCE_OPERATIONS = {
    "linear_feature_importance": OperationConfig(
        name="linear_feature_importance",
        category="feature_importance",
        func=linear_feature_importance,
        parameters={"target": str, "features": None},
        returns_df=True,
        view_only=False,
        description="Calculate feature importance using linear models (coefficients)",
    ),
    "random_forest_feature_importance": OperationConfig(
        name="random_forest_feature_importance",
        category="feature_importance",
        func=random_forest_feature_importance,
        parameters={"target": str, "features": None, "model_type": None, "n_estimators": 100, "random_state": 42},
        returns_df=True,
        view_only=False,
        description="Calculate feature importance using Random Forest models",
    ),
    "gradient_boosting_feature_importance": OperationConfig(
        name="gradient_boosting_feature_importance",
        category="feature_importance",
        func=gradient_boosting_feature_importance,
        parameters={"target": str, "features": None, "model_type": None, "n_estimators": 100, "random_state": 42},
        returns_df=True,
        view_only=False,
        description="Calculate feature importance using Gradient Boosting models",
    ),
    "permutation_feature_importance": OperationConfig(
        name="permutation_feature_importance",
        category="feature_importance",
        func=permutation_feature_importance_fn,
        parameters={"target": str, "features": None, "model_type": "regression", "n_estimators": 50, "n_repeats": 10, "random_state": 42},
        returns_df=True,
        view_only=False,
        description="Calculate permutation feature importance",
    ),
}
