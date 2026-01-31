# Database enum identification

We have a database with the following description:

{db_description}

Given the table schema, and the column information, identifies whether the column is an enum type.

## Table Schema:

{table_schema}

## Column Information:
- Name: {column_name}
- Data Type: {column_data_type}
- Description: {column_description}
- The table has {row_count} rows.
- The column has {distinct_count} unique values.
- The distinct values and their counts are as follows:
{distinct_by_count}

## Task

Return your analysis as a structured response with:
- is_enum: True if the column is an enum type, otherwise False
- reasoning: Brief explanation of your decision (be concise, plain text, no formatting, less than 200 characters)
