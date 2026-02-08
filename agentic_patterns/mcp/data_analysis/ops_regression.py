"""ML regression operations registry."""

from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Lasso, LinearRegression, Ridge
from sklearn.neighbors import KNeighborsRegressor
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor

from agentic_patterns.mcp.data_analysis.ml_helpers import train_and_fit_regressor
from agentic_patterns.mcp.data_analysis.models import OperationConfig

REGRESSION_OPERATIONS = {
    "linear_regression": OperationConfig(
        name="linear_regression",
        category="ml_regression",
        func=lambda df, target, features=None, test_size=0.2, **kwargs: train_and_fit_regressor(
            df, target, features, test_size, LinearRegression(),
        ),
        parameters={"target": str, "features": None, "test_size": 0.2},
        returns_df=False,
        view_only=False,
        description="Train a linear regression model",
    ),
    "ridge_regression": OperationConfig(
        name="ridge_regression",
        category="ml_regression",
        func=lambda df, target, features=None, test_size=0.2, alpha=1.0, random_state=42, **kwargs: train_and_fit_regressor(
            df, target, features, test_size, Ridge(alpha=alpha, random_state=random_state, **kwargs), random_state=random_state,
        ),
        parameters={"target": str, "features": None, "test_size": 0.2, "alpha": 1.0, "random_state": 42},
        returns_df=False,
        view_only=False,
        description="Train a ridge regression model with L2 regularization",
    ),
    "lasso_regression": OperationConfig(
        name="lasso_regression",
        category="ml_regression",
        func=lambda df, target, features=None, test_size=0.2, alpha=1.0, random_state=42, **kwargs: train_and_fit_regressor(
            df, target, features, test_size, Lasso(alpha=alpha, random_state=random_state, **kwargs), random_state=random_state,
        ),
        parameters={"target": str, "features": None, "test_size": 0.2, "alpha": 1.0, "random_state": 42},
        returns_df=False,
        view_only=False,
        description="Train a lasso regression model with L1 regularization",
    ),
    "random_forest_regression": OperationConfig(
        name="random_forest_regression",
        category="ml_regression",
        func=lambda df, target, features=None, test_size=0.2, n_estimators=100, random_state=42, **kwargs: train_and_fit_regressor(
            df, target, features, test_size, RandomForestRegressor(n_estimators=n_estimators, random_state=random_state, **kwargs), random_state=random_state,
        ),
        parameters={"target": str, "features": None, "test_size": 0.2, "n_estimators": 100, "random_state": 42},
        returns_df=False,
        view_only=False,
        description="Train a random forest regression model",
    ),
    "decision_tree_regression": OperationConfig(
        name="decision_tree_regression",
        category="ml_regression",
        func=lambda df, target, features=None, test_size=0.2, max_depth=None, random_state=42, **kwargs: train_and_fit_regressor(
            df, target, features, test_size, DecisionTreeRegressor(max_depth=max_depth, random_state=random_state, **kwargs), random_state=random_state,
        ),
        parameters={"target": str, "features": None, "test_size": 0.2, "max_depth": None, "random_state": 42},
        returns_df=False,
        view_only=False,
        description="Train a decision tree regression model",
    ),
    "gradient_boosting_regression": OperationConfig(
        name="gradient_boosting_regression",
        category="ml_regression",
        func=lambda df, target, features=None, test_size=0.2, n_estimators=100, random_state=42, **kwargs: train_and_fit_regressor(
            df, target, features, test_size, GradientBoostingRegressor(n_estimators=n_estimators, random_state=random_state, **kwargs), random_state=random_state,
        ),
        parameters={"target": str, "features": None, "test_size": 0.2, "n_estimators": 100, "random_state": 42},
        returns_df=False,
        view_only=False,
        description="Train a gradient boosting regression model",
    ),
    "knn_regression": OperationConfig(
        name="knn_regression",
        category="ml_regression",
        func=lambda df, target, features=None, test_size=0.2, n_neighbors=5, **kwargs: train_and_fit_regressor(
            df, target, features, test_size, KNeighborsRegressor(n_neighbors=n_neighbors, **kwargs),
        ),
        parameters={"target": str, "features": None, "test_size": 0.2, "n_neighbors": 5},
        returns_df=False,
        view_only=False,
        description="Train a k-nearest neighbors regression model",
    ),
    "svr_regression": OperationConfig(
        name="svr_regression",
        category="ml_regression",
        func=lambda df, target, features=None, test_size=0.2, kernel="rbf", **kwargs: train_and_fit_regressor(
            df, target, features, test_size, SVR(kernel=kernel, **kwargs),
        ),
        parameters={"target": str, "features": None, "test_size": 0.2, "kernel": "rbf"},
        returns_df=False,
        view_only=False,
        description="Train a support vector regression model",
    ),
}
