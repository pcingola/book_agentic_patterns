# Code Review Reference

## Security Checklist

- Input validation on all user-provided data
- Parameterized queries for database operations
- Authentication and authorization checks
- Sensitive data exposure (logs, errors, responses)
- Dependency vulnerabilities

## Common Bug Patterns

- Off-by-one errors in loops
- Null/undefined handling
- Race conditions in async code
- Resource leaks (connections, file handles)
