# SurplusLink — Food Rescue Network

SurplusLink connects food donors with volunteers who collect surplus food before it goes to waste. It supports donation posting, claims, pickup validation, a simulated clock, activity history, and a dashboard that accounts for saved and wasted food.

## Technology

- Frontend: React + Vite
- Backend: Python + FastAPI
- Database: MySQL (InnoDB)
- Driver: PyMySQL
- Initial demo data: `seed.json` (loaded only when the MySQL database has no donor records)

## Prerequisites

- Python 3.10+
- Node.js and npm
- A MySQL database (Aiven MySQL is supported)

## Configure MySQL

Create a MySQL database/schema in Aiven. Download its CA certificate and keep it outside Git. In `backend`, create a `.env` file using `.env.example` as a template, and set `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, and `DB_SSL_CA`. Never commit `.env` or your CA/private credentials.

The backend reads these values from environment variables. If using PowerShell, you can set them for the current terminal before starting the API, for example:

```powershell
$env:DB_HOST = "your-aiven-host"
$env:DB_PORT = "your-aiven-port"
$env:DB_NAME = "defaultdb"
$env:DB_USER = "avnadmin"
$env:DB_PASSWORD = "your-password"
$env:DB_SSL_CA = "C:\path\to\ca.pem"
```

Use the exact host, port, database, username, password and CA certificate shown in your Aiven service. Do not paste passwords into source code or chat.

## Run locally

### 1. Backend

Open PowerShell in the project root:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

The backend creates the required MySQL tables and loads `seed.json` only if the `donors` table is empty. Existing data and the simulated clock are not reseeded on normal restarts.

API: http://127.0.0.1:8000
Swagger docs: http://127.0.0.1:8000/docs

### 2. Frontend

Open a second terminal in the project root:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal (normally http://localhost:5173). The frontend uses `VITE_API_URL` if configured, otherwise it defaults to the local API URL.

## Core rules

- Donation quantities are whole kilograms and at least 1 kg.
- Claims enforce donation status, volunteer capacity, remaining quantity, zone, pickup window, simulated time, and 60-minute scheduling separation.
- Cancelled claims release reserved quantity. Active claims become missed after the donation deadline.
- Claim creation uses a database transaction and locks the donation row to reduce concurrent overbooking.
- Dashboard totals must balance: Listed = Collected + Missed + Wasted + In Progress + Still Open.
- The simulated clock, not the operating system clock, drives eligibility and expiry.

## Privacy and security notes

The official hackathon statement explicitly requires person selection without login. This project therefore retains the hackathon's no-login interaction model; it must not be described as production-grade identity authentication. Use fictional demo identities and data. The MySQL password is supplied through environment variables and the connection uses TLS settings; keep the Aiven CA certificate private to deployment configuration. Before serving real public users, implement authentication and per-user authorization, restrict CORS to the deployed frontend origin, add rate limiting, and review API responses for personal-data exposure.

## Testing checklist

- [ ] MySQL connection succeeds with certificate verification.
- [ ] First startup creates tables and loads seed data.
- [ ] Restart preserves the simulated clock and saved records.
- [ ] Claim rules report all applicable refusal reasons.
- [ ] Concurrent attempts cannot reserve the same final kilograms.
- [ ] Collection, cancellation, expiry, and missed claims update the dashboard correctly.
- [ ] Dashboard accounting remains balanced.

## AI usage

See `AI_USAGE.md` for the assistance used during development. Update it to reflect the actual changes, testing, and verification performed before submission.
