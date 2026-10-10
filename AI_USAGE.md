# AI Usage Disclosure — SurplusLink

AI assistance was used to help review the project structure, explain database migration concepts, draft documentation, and identify implementation and security checks. Suggested changes must be reviewed and tested by the project author.

## Database migration

The starter backend was adapted from SQLite to MySQL using PyMySQL. The schema is created by the backend, and seed data is loaded only when no donor records exist. Connection settings are read from environment variables, and a CA certificate path can be configured for TLS verification.

## Human review and testing

Before submission, the author should verify the Aiven connection settings, confirm certificate verification works, test seed initialization and persistence, and exercise all donation/claim rules including concurrent claim attempts. Document any further changes, rejected suggestions, and test results accurately. Do not claim a test passed unless it was actually run.
