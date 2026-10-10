# SurplusLink — Food Rescue Network

SurplusLink is a web application that helps restaurants reduce food waste by connecting them with volunteers who can collect surplus food within a specified pickup window.

Restaurants can post donations, volunteers can reserve and collect food, and a dashboard tracks collected, missed, wasted, and available food quantities.

## Features

- **Donations:** Post surplus food with a description, quantity, and pickup window.
- **Volunteer claims:** Reserve food according to capacity, zone, quantity, and timing rules.
- **Claim validation:** Report all applicable rule violations for validly formatted claim requests.
- **Collection and cancellation:** Collect eligible claims or cancel claims when permitted.
- **Simulated clock:** Advance application time to test pickup deadlines and missed claims.
- **Dashboard:** Track food quantities and verify that the accounting totals balance.
- **Activity history:** Review recorded application actions.
- **Persistent storage:** Use MySQL to preserve application data across backend restarts.
- **Seed data:** Initialize application data from `seed.json` when the database has no saved state.

## Technology Stack

- **Frontend:** React and Vite
- **Backend:** Python and FastAPI
- **Database:** MySQL
- **Database hosting:** Aiven MySQL (for the configured cloud setup)
- **Database driver:** PyMySQL
- **API documentation:** FastAPI Swagger UI

## Project Structure

```text
SurplusLink_starter/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── .gitignore
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── style.css
│   ├── package.json
│   └── package-lock.json
├── seed.json
├── README.md
├── AI_USAGE.md
└── .gitignore
```

## Prerequisites

Install the following before running the application:

- Python 3.10 or later
- Node.js and npm
- An accessible MySQL database
- Git (optional)

## Configuration

The backend reads its MySQL connection settings from environment variables. Create a `backend/.env` file for local development and configure the variables expected by `backend/main.py`.

Example configuration:

```dotenv
DB_HOST=your-mysql-host
DB_PORT=3306
DB_NAME=your-database-name
DB_USER=your-database-user
DB_PASSWORD=your-database-password
DB_SSL_CA=path-to-your-ca-certificate
```

Replace the example values with your actual database settings. The port shown is an example; use the port provided by your database service.

For Aiven MySQL, download the CA certificate and configure the correct local path. Use certificate verification for encrypted database connections.

**Security:** Never commit `.env` files, database passwords, private keys, or other credentials to GitHub. Keep credentials in the deployment platform's environment settings for hosted environments.

## Run Locally

### 1. Start the Backend

Open PowerShell in the project root:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

The backend should be available at:

- API: http://127.0.0.1:8000
- Interactive API documentation: http://127.0.0.1:8000/docs

Keep the backend terminal running.

### 2. Start the Frontend

Open a second terminal from the project root:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL displayed by Vite, normally:

http://localhost:5173

Keep both terminals running while using the application.

## Business Rules

### Donations

- Donation quantities must be whole kilograms and at least 1 kg.
- The pickup start time must be earlier than the pickup end time.
- The pickup end time cannot be before the simulated current time.
- Remaining quantity equals the original quantity minus claims that are not cancelled.
- Donation status follows this priority: `CANCELLED`, `EXPIRED`, `FULLY_CLAIMED`, `OPEN`.
- A donor can cancel a donation only when it is open and has no active or collected claims.

### Claims

A claim must satisfy all applicable rules:

1. The donation is not cancelled or expired.
2. The requested quantity does not exceed the volunteer's capacity.
3. The requested quantity does not exceed the donation's remaining quantity.
4. The donation's zone is included in the volunteer's permitted zones.
5. The planned pickup time falls within the pickup window, including its boundaries.
6. The planned pickup time is not before the simulated current time.
7. The planned pickup is at least 60 minutes apart from every other active or collected claim belonging to the same volunteer.

The application should report all applicable rule violations for validly formatted requests. Invalid input, such as a non-whole kilogram quantity, is rejected separately.

### Collection and Cancellation

- An active claim can be collected only when the simulated current time is within the donation's pickup window, including its boundaries.
- An active claim can be cancelled only when the simulated current time is strictly before the planned pickup time.
- Cancelled claims release their reserved quantity.
- Active claims become missed when the simulated clock moves past the donation's pickup deadline.

### Simulated Clock

- The clock starts at the value provided in `seed.json`.
- Users can advance the clock through the application.
- The clock cannot move backwards; setting it to the same time is allowed.
- Business rules use the simulated clock, not the computer's actual system time.
- Timestamps use the local format `YYYY-MM-DDTHH:MM`, without timezone conversion.

### Dashboard Accounting

The dashboard reports the following quantities in kilograms:

- **Listed:** Total quantity posted across non-cancelled donations.
- **Collected:** Quantity in collected claims.
- **Missed:** Quantity in missed claims.
- **Wasted:** Remaining quantity on expired donations.
- **In Progress:** Quantity in active claims.
- **Still Open:** Remaining quantity on donations that have not expired.

The required accounting equation is:

**Listed = Collected + Missed + Wasted + In Progress + Still Open**

The dashboard must also show collected kilograms per donor and collected kilograms and missed-claim counts per volunteer.

## Data Persistence

The backend uses MySQL to store application records. Initial data should be loaded from `seed.json` only when the database has no saved state. Normal backend restarts must preserve existing records and the simulated clock.

## Testing Checklist

Use this checklist to record actual test results before submission:

- [ ] Initial seed data loads correctly.
- [ ] Existing data survives a backend restart.
- [ ] Donations can be posted with valid details.
- [ ] Donation cancellation rules are enforced.
- [ ] All claim-validation rules are enforced.
- [ ] All applicable claim refusal reasons are reported.
- [ ] Cancelled claims release reserved quantities.
- [ ] Collection and missed-claim transitions work correctly.
- [ ] The simulated clock cannot move backwards.
- [ ] Dashboard totals satisfy the accounting equation.
- [ ] Concurrent claims cannot overbook a donation.
- [ ] MySQL SSL and credential configuration work correctly.

## Assumptions and Scope

- The application follows the supplied hackathon requirement that there is no login.
- The user selects the donor or volunteer they are acting as.
- Zones are plain labels; the application does not calculate maps or distances.
- Quantities are represented in whole kilograms.
- The simulated clock controls pickup eligibility and expiry.
- A no-login demonstration is not an authentication system and should not be treated as production-ready for real users' private data.

## AI Usage

AI assistance used during development is documented in `AI_USAGE.md`. It records the types of assistance received, the implementation decisions that require human review, and the testing still needed.

## Project Goal

SurplusLink aims to reduce avoidable food waste by helping restaurants and volunteers coordinate food collection within the required capacity, zone, and timing constraints.

**Rescue more. Waste less.**
