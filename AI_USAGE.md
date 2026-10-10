# AI Usage Disclosure — SurplusLink

## 1. AI Tools Used

**Tool:** ChatGPT

AI assistance was used during development to help understand the problem statement, plan the application structure, prepare implementation code, troubleshoot errors, and improve project documentation.

## 2. How AI Was Used

### Requirements and Planning

AI assistance was used to interpret the SurplusLink problem statement and organize its requirements into application features, including:

- Donor and volunteer workflows.
- Donation creation and cancellation.
- Claim validation and refusal reasons.
- Simulated clock and expiry handling.
- Dashboard accounting and activity history.
- Persistent database storage.

### Implementation Assistance

AI assistance was used to help prepare and revise code for the React frontend and FastAPI backend.

The project initially used SQLite for local persistence. During subsequent development, the database configuration was changed toward MySQL using PyMySQL and environment-based connection settings.

AI assistance also helped prepare database configuration examples, project setup instructions, `.gitignore` rules, and documentation.

### Debugging Assistance

AI assistance was used to interpret local startup errors involving missing environment variables and SSL certificate paths. The troubleshooting guidance focused on configuring the local environment and connecting the backend to the intended MySQL service.

A successful startup or database connection should only be reported after it has been verified in the running application.

### Documentation

AI assistance was used to draft and revise `README.md` and `AI_USAGE.md`, including local setup steps, business rules, project structure, assumptions, and a testing checklist.

## 3. Human Review and Changes

The developer reviewed the proposed implementation and setup instructions while running the application locally.

The project configuration was adjusted to use MySQL instead of the original SQLite setup. Database credentials were intended to be supplied through environment variables rather than hardcoded in source code.

Suggested configuration and code must be reviewed against the actual project files. Any remaining defects, incomplete requirements, or differences between the documentation and implementation should be corrected before submission.

## 4. Testing and Verification

The following items require verification against the final committed version:

- Backend starts successfully with the configured MySQL database.
- Frontend communicates correctly with the backend.
- Seed data is loaded only when no saved state exists.
- Data persists after restarting the backend.
- Donation and claim validation rules behave as specified.
- The simulated clock and missed-claim transitions work correctly.
- Dashboard quantities satisfy the required accounting equation.
- Concurrent claim requests cannot overbook a donation.
- Database connections use verified SSL where required.
- Credentials, certificates, and local database files are excluded from public source control.

This disclosure does not claim that every test has passed. Results should be updated to reflect the tests actually completed.

## 5. Limitations and Security Considerations

The hackathon problem statement explicitly requires no login. The application therefore uses a person-selection workflow rather than a full identity-verification system.

That design follows the supplied hackathon requirements, but it is not sufficient by itself to protect real users' accounts or private data in a production application.

MySQL, SSL, and environment variables help protect database connections and credentials, but they do not replace authorization, input validation, access restrictions, or careful handling of personal data.

## 6. Developer Responsibility

AI assistance was used as a development aid. The developer remains responsible for understanding, reviewing, testing, and maintaining the submitted code and for ensuring that the final implementation follows the problem statement.
