"""ML classification operations registry."""

from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

from agentic_patterns.toolkits.data_analysis.ml_helpers import train_and_fit_classifier
from agentic_patterns.toolkits.data_analysis.models import OperationConfig

CLASSIFICATION_OPERATIONS = {
    "logistic_regression": OperationConfig(
        name="logistic_regression",
        category="ml_classification",
        func=lambda df, target, features=None, test_size=0.2, random_state=42, **kwargs: train_and_fit_classifier(
            df, target, features, test_size, LogisticRegression(random_state=random_state, **kwargs), random_state=random_state,
        ),
        parameters={"target": str, "features": None, "test_size": 0.2, "random_state": 42},
        returns_df=False,
        view_only=False,
        description="Train a logistic regression classifier",
    ),
    "random_forest_classification": OperationConfig(
        name="random_forest_classification",
        category="ml_classification",
        func=lambda df, target, features=None, test_size=0.2, n_estimators=100, random_state=42, **kwargs: train_and_fit_classifier(
            df, target, features, test_size, RandomForestClassifier(n_estimators=n_estimators, random_state=random_state, **kwargs), random_state=random_state,
        ),
        parameters={"target": str, "features": None, "test_size": 0.2, "n_estimators": 100, "random_state": 42},
        returns_df=False,
        view_only=False,
        description="Train a random forest classifier",
    ),
    "decision_tree_classification": OperationConfig(
        name="decision_tree_classification",
        category="ml_classification",
        func=lambda df, target, features=None, test_size=0.2, max_depth=None, random_state=42, **kwargs: train_and_fit_classifier(
            df, target, features, test_size, DecisionTreeClassifier(max_depth=max_depth, random_state=random_state, **kwargs), random_state=random_state,
        ),
        parameters={"target": str, "features": None, "test_size": 0.2, "max_depth": None, "random_state": 42},
        returns_df=False,
        view_only=False,
        description="Train a decision tree classifier",
    ),
    "gradient_boosting_classification": OperationConfig(
        name="gradient_boosting_classification",
        category="ml_classification",
        func=lambda df, target, features=None, test_size=0.2, n_estimators=100, random_state=42, **kwargs: train_and_fit_classifier(
            df, target, features, test_size, GradientBoostingClassifier(n_estimators=n_estimators, random_state=random_state, **kwargs), random_state=random_state,
        ),
        parameters={"target": str, "features": None, "test_size": 0.2, "n_estimators": 100, "random_state": 42},
        returns_df=False,
        view_only=False,
        description="Train a gradient boosting classifier",
    ),
    "knn_classification": OperationConfig(
        name="knn_classification",
        category="ml_classification",
        func=lambda df, target, features=None, test_size=0.2, n_neighbors=5, **kwargs: train_and_fit_classifier(
            df, target, features, test_size, KNeighborsClassifier(n_neighbors=n_neighbors, **kwargs),
        ),
        parameters={"target": str, "features": None, "test_size": 0.2, "n_neighbors": 5},
        returns_df=False,
        view_only=False,
        description="Train a k-nearest neighbors classifier",
    ),
    "svm_classification": OperationConfig(
        name="svm_classification",
        category="ml_classification",
        func=lambda df, target, features=None, test_size=0.2, kernel="rbf", random_state=42, **kwargs: train_and_fit_classifier(
            df, target, features, test_size, SVC(kernel=kernel, random_state=random_state, **kwargs), random_state=random_state,
        ),
        parameters={"target": str, "features": None, "test_size": 0.2, "kernel": "rbf", "random_state": 42},
        returns_df=False,
        view_only=False,
        description="Train a support vector machine classifier",
    ),
}
