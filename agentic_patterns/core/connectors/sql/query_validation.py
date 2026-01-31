"""SQL query validation."""


class QueryValidationError(Exception):
    """Raised when a SQL query fails validation."""


def validate_query(query: str) -> None:
    """Validate that a query is a single SELECT statement.

    Raises:
        QueryValidationError: If the query is invalid
    """
    if not query.strip():
        raise QueryValidationError("SQL query cannot be empty")

    query_stripped = query.strip()
    if query_stripped.rstrip(";").count(";") > 0:
        raise QueryValidationError("Multiple SQL statements are not allowed")

    query_upper = query_stripped.upper()
    if not query_upper.startswith("SELECT"):
        raise QueryValidationError("Only SELECT queries are allowed")
