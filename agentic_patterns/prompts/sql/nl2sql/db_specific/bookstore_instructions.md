# Bookstore database-specific instructions

- When querying for books, always join with authors through the book_authors table to get author information
- Customer addresses are normalized in the addresses table - join when location information is needed
- Order status follows this lifecycle: pending -> processing -> shipped -> delivered (or cancelled)
- Payment methods are stored as enum values in orders table
- Book genres and languages are enum fields - use exact matches from the enum values
- When calculating totals, use the price and quantity fields from order_items
- Publisher information is denormalized in the books table for performance
