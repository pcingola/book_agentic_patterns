# Database table description

We have a database with the following description:

{db_description}

Given the table schema, provide a concise summary of the table.

- Explain what is the main purpose of the table and what it can be used for.
- Highlight any important columns, e.g. controlled vocabularies or relationships to other tables.
- Be concise and to the point, remove fluff and filler words.
- This is supposed to be a comment in a `schema.sql` file, so it should be one line, or a short paragraph.
- Output the description text only. No code blocks, markdown, titles, or any other formatting than plain text with the description.
- You can ONLY use new lines if needed.
- Aim for 300 characters if possible, but go longer if there is important information to convey.

## Table Schema

{table_schema}
