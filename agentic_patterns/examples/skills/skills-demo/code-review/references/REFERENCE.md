# Code Review Reference

## Common Security Vulnerabilities

### Code Injection
- `eval()` - Executes arbitrary code from string input
- `exec()` - Executes arbitrary Python statements
- Template injection - Unescaped user input in templates

### SQL Injection
- String concatenation in SQL queries
- Missing parameterized queries

### Cross-Site Scripting (XSS)
- Unescaped HTML output
- innerHTML with user data
