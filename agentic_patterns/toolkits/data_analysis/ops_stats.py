"""Statistical test operations registry."""

import pandas as pd
from scipy import stats

from agentic_patterns.toolkits.data_analysis.models import OperationConfig

STATS_OPERATIONS = {
    "t_test_one_sample": OperationConfig(
        name="t_test_one_sample",
        category="stats",
        func=lambda df, column, population_mean=0: {
            "statistic": stats.ttest_1samp(df[column].dropna(), population_mean).statistic,
            "p_value": stats.ttest_1samp(df[column].dropna(), population_mean).pvalue,
            "degrees_of_freedom": len(df[column].dropna()) - 1,
            "column": column,
            "population_mean": population_mean,
            "sample_mean": df[column].mean(),
            "sample_size": len(df[column].dropna()),
        },
        parameters={"column": str, "population_mean": 0},
        returns_df=False,
        view_only=True,
        description="Perform one-sample t-test against population mean",
    ),
    "t_test_two_sample": OperationConfig(
        name="t_test_two_sample",
        category="stats",
        func=lambda df, column1, column2, equal_var=True: {
            "statistic": stats.ttest_ind(df[column1].dropna(), df[column2].dropna(), equal_var=equal_var).statistic,
            "p_value": stats.ttest_ind(df[column1].dropna(), df[column2].dropna(), equal_var=equal_var).pvalue,
            "column1": column1,
            "column2": column2,
            "mean1": df[column1].mean(),
            "mean2": df[column2].mean(),
            "equal_var": equal_var,
        },
        parameters={"column1": str, "column2": str, "equal_var": True},
        returns_df=False,
        view_only=True,
        description="Perform two-sample t-test between two columns",
    ),
    "chi_square_test": OperationConfig(
        name="chi_square_test",
        category="stats",
        func=lambda df, column1, column2: {
            "statistic": stats.chi2_contingency(pd.crosstab(df[column1], df[column2])).statistic,
            "p_value": stats.chi2_contingency(pd.crosstab(df[column1], df[column2])).pvalue,
            "degrees_of_freedom": stats.chi2_contingency(pd.crosstab(df[column1], df[column2])).dof,
            "expected_frequencies": stats.chi2_contingency(pd.crosstab(df[column1], df[column2])).expected_freq.tolist(),
            "column1": column1,
            "column2": column2,
        },
        parameters={"column1": str, "column2": str},
        returns_df=False,
        view_only=True,
        description="Perform chi-square test of independence between two categorical variables",
    ),
    "normality_test": OperationConfig(
        name="normality_test",
        category="stats",
        func=lambda df, column: {
            "statistic": stats.shapiro(df[column].dropna()).statistic,
            "p_value": stats.shapiro(df[column].dropna()).pvalue,
            "test_name": "Shapiro-Wilk",
            "column": column,
            "sample_size": len(df[column].dropna()),
            "is_normal_005": stats.shapiro(df[column].dropna()).pvalue > 0.05,
        },
        parameters={"column": str},
        returns_df=False,
        view_only=True,
        description="Test for normality using Shapiro-Wilk test",
    ),
    "correlation_test": OperationConfig(
        name="correlation_test",
        category="stats",
        func=lambda df, column1, column2, method="pearson": {
            "correlation": (stats.pearsonr(df[column1].dropna(), df[column2].dropna()).statistic if method == "pearson" else stats.spearmanr(df[column1].dropna(), df[column2].dropna()).statistic),
            "p_value": (stats.pearsonr(df[column1].dropna(), df[column2].dropna()).pvalue if method == "pearson" else stats.spearmanr(df[column1].dropna(), df[column2].dropna()).pvalue),
            "method": method,
            "column1": column1,
            "column2": column2,
        },
        parameters={"column1": str, "column2": str, "method": "pearson"},
        returns_df=False,
        view_only=True,
        description="Test correlation between two numeric variables (Pearson or Spearman)",
    ),
    "anova_one_way": OperationConfig(
        name="anova_one_way",
        category="stats",
        func=lambda df, value_column, group_column: {
            "f_statistic": stats.f_oneway(*[group[value_column].dropna() for name, group in df.groupby(group_column)]).statistic,
            "p_value": stats.f_oneway(*[group[value_column].dropna() for name, group in df.groupby(group_column)]).pvalue,
            "degrees_of_freedom_between": len(df[group_column].unique()) - 1,
            "degrees_of_freedom_within": len(df[value_column].dropna()) - len(df[group_column].unique()),
            "value_column": value_column,
            "group_column": group_column,
            "groups": list(df[group_column].unique()),
            "group_means": df.groupby(group_column)[value_column].mean().to_dict(),
        },
        parameters={"value_column": str, "group_column": str},
        returns_df=False,
        view_only=True,
        description="Perform one-way ANOVA to test differences between group means",
    ),
    "mann_whitney_u_test": OperationConfig(
        name="mann_whitney_u_test",
        category="stats",
        func=lambda df, value_column, group_column: {
            "statistic": stats.mannwhitneyu(
                df[df[group_column] == df[group_column].unique()[0]][value_column].dropna(),
                df[df[group_column] == df[group_column].unique()[1]][value_column].dropna(),
            ).statistic,
            "p_value": stats.mannwhitneyu(
                df[df[group_column] == df[group_column].unique()[0]][value_column].dropna(),
                df[df[group_column] == df[group_column].unique()[1]][value_column].dropna(),
            ).pvalue,
            "value_column": value_column,
            "group_column": group_column,
            "groups": list(df[group_column].unique()[:2]),
        },
        parameters={"value_column": str, "group_column": str},
        returns_df=False,
        view_only=True,
        description="Perform Mann-Whitney U test (non-parametric) between two groups",
    ),
}
