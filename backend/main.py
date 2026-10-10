from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import json, os
import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv
from pathlib import Path
from threading import RLock

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(Path(__file__).resolve().parent / ".env")
DB_HOST = os.getenv("DB_HOST", "")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_SSL_CA = os.getenv("DB_SSL_CA", "")
SEED_PATH = Path(os.getenv("SURPLUSLINK_SEED", str(ROOT / "seed.json")))
LOCK = RLock()
app = FastAPI(title="SurplusLink API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False, allow_methods=["*"], allow_headers=["*"]
)

def dt(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M")

def stamp(d: datetime) -> str:
    return d.strftime("%Y-%m-%dT%H:%M")

class Row(dict):
    """Dict-like database row that also supports SQLite-style numeric indexing."""
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)

class CursorAdapter:
    def __init__(self, cursor): self.cursor = cursor
    def execute(self, sql, params=()):
        sql = sql.replace("?", "%s")
        self.cursor.execute(sql, params)
        return self
    def fetchone(self):
        row = self.cursor.fetchone()
        return Row(row) if row is not None else None
    def fetchall(self):
        return [Row(row) for row in self.cursor.fetchall()]
    def __iter__(self):
        return iter(self.fetchall())
    @property
    def rowcount(self): return self.cursor.rowcount

class ConnectionAdapter:
    def __init__(self, connection): self.connection = connection
    def execute(self, sql, params=()):
        cur = CursorAdapter(self.connection.cursor())
        return cur.execute(sql, params)
    def commit(self): self.connection.commit()
    def rollback(self): self.connection.rollback()
    def begin(self): self.connection.begin()
    def close(self): self.connection.close()
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb):
        if exc_type is None: self.commit()
        else: self.rollback()
        self.close()

def conn():
    missing = [name for name, value in (("DB_HOST", DB_HOST), ("DB_NAME", DB_NAME), ("DB_USER", DB_USER), ("DB_PASSWORD", DB_PASSWORD)) if not value]
    if missing:
        raise RuntimeError("Missing MySQL environment variables: " + ", ".join(missing))
    ssl = {"ca": DB_SSL_CA} if DB_SSL_CA else {"check_hostname": True}
    raw = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, charset="utf8mb4", cursorclass=DictCursor,
        autocommit=False, connect_timeout=10, ssl=ssl)
    return ConnectionAdapter(raw)

def rows(c, sql, params=()):
    return [dict(r) for r in c.execute(sql, params).fetchall()]

def initialize():
    schema = [
        "CREATE TABLE IF NOT EXISTS app_state (id TINYINT PRIMARY KEY, clock VARCHAR(16) NOT NULL) ENGINE=InnoDB",
        "CREATE TABLE IF NOT EXISTS donors (id VARCHAR(32) PRIMARY KEY, name VARCHAR(120) NOT NULL, zone VARCHAR(40) NOT NULL) ENGINE=InnoDB",
        "CREATE TABLE IF NOT EXISTS volunteers (id VARCHAR(32) PRIMARY KEY, name VARCHAR(120) NOT NULL, capacity_kg INT NOT NULL, zones JSON NOT NULL) ENGINE=InnoDB",
        "CREATE TABLE IF NOT EXISTS donations (id VARCHAR(32) PRIMARY KEY, donor_id VARCHAR(32) NOT NULL, description VARCHAR(160) NOT NULL, quantity_kg INT NOT NULL, pickup_from VARCHAR(16) NOT NULL, pickup_until VARCHAR(16) NOT NULL, cancelled TINYINT NOT NULL DEFAULT 0, CONSTRAINT fk_donation_donor FOREIGN KEY (donor_id) REFERENCES donors(id)) ENGINE=InnoDB",
        "CREATE TABLE IF NOT EXISTS claims (id VARCHAR(32) PRIMARY KEY, donation_id VARCHAR(32) NOT NULL, volunteer_id VARCHAR(32) NOT NULL, kg INT NOT NULL, planned_time VARCHAR(16) NOT NULL, status VARCHAR(16) NOT NULL, created_at VARCHAR(16) NOT NULL, INDEX idx_claim_donation_status (donation_id,status), INDEX idx_claim_volunteer_status (volunteer_id,status), CONSTRAINT fk_claim_donation FOREIGN KEY (donation_id) REFERENCES donations(id), CONSTRAINT fk_claim_volunteer FOREIGN KEY (volunteer_id) REFERENCES volunteers(id)) ENGINE=InnoDB",
        "CREATE TABLE IF NOT EXISTS history (id BIGINT AUTO_INCREMENT PRIMARY KEY, at VARCHAR(16) NOT NULL, actor_id VARCHAR(32) NOT NULL, actor_name VARCHAR(120) NOT NULL, action VARCHAR(40) NOT NULL, donation_id VARCHAR(32), claim_id VARCHAR(32), outcome VARCHAR(24) NOT NULL, details TEXT NOT NULL, INDEX idx_history_id (id)) ENGINE=InnoDB"
    ]
    with conn() as c:
        for statement in schema: c.execute(statement)
        count = c.execute("SELECT COUNT(*) AS n FROM donors").fetchone()["n"]
        if count == 0:
            if not SEED_PATH.exists(): raise RuntimeError(f"Seed file not found: {SEED_PATH}")
            seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
            c.execute("INSERT INTO app_state(id,clock) VALUES(1, %s) ON DUPLICATE KEY UPDATE clock=VALUES(clock)", (seed["clock"],))
            for x in seed["donors"]: c.execute("INSERT INTO donors(id,name,zone) VALUES(%s,%s,%s)", (x["id"],x["name"],x["zone"]))
            for x in seed["volunteers"]: c.execute("INSERT INTO volunteers(id,name,capacity_kg,zones) VALUES(%s,%s,%s,%s)", (x["id"],x["name"],x["capacity_kg"],json.dumps(x["zones"])))
            for x in seed["donations"]: c.execute("INSERT INTO donations(id,donor_id,description,quantity_kg,pickup_from,pickup_until) VALUES(%s,%s,%s,%s,%s,%s)", (x["id"],x["donor_id"],x["description"],x["quantity_kg"],x["pickup_from"],x["pickup_until"]))
        else:
            # Ensure clock exists without resetting existing saved state.
            c.execute("INSERT IGNORE INTO app_state(id,clock) VALUES(1,%s)", ("2026-03-10T12:00",))

initialize()

class DonationCreate(BaseModel):
    donor_id: str
    description: str = Field(min_length=1, max_length=160)
    quantity_kg: int = Field(ge=1)
    pickup_from: str
    pickup_until: str

class ClaimCreate(BaseModel):
    volunteer_id: str
    kg: int = Field(ge=1)
    planned_time: str

class ClockUpdate(BaseModel):
    clock: str

class Actor(BaseModel):
    actor_id: str

def state(c):
    return c.execute("SELECT clock FROM app_state WHERE id=1").fetchone()["clock"]

def get_donation(c, did):
    r = c.execute("SELECT * FROM donations WHERE id=?", (did,)).fetchone()
    if not r: raise HTTPException(404, "Donation not found")
    return dict(r)

def get_claim(c, cid):
    r = c.execute("SELECT * FROM claims WHERE id=?", (cid,)).fetchone()
    if not r: raise HTTPException(404, "Claim not found")
    return dict(r)

def claim_rows(c, did=None):
    if did:
        return rows(c, "SELECT * FROM claims WHERE donation_id=? ORDER BY created_at", (did,))
    return rows(c, "SELECT * FROM claims ORDER BY created_at DESC")

def remaining(c, donation):
    used = c.execute("SELECT COALESCE(SUM(kg),0) FROM claims WHERE donation_id=? AND status!='CANCELLED'",
                     (donation["id"],)).fetchone()[0]
    return max(0, donation["quantity_kg"] - used)

def donation_status(c, donation, now=None):
    now = dt(now or state(c))
    if donation["cancelled"]: return "CANCELLED"
    if now > dt(donation["pickup_until"]): return "EXPIRED"
    if remaining(c, donation) == 0: return "FULLY_CLAIMED"
    return "OPEN"

def log(c, actor_id, action, donation_id, claim_id, outcome, details):
    name = c.execute("SELECT name FROM donors WHERE id=?", (actor_id,)).fetchone()
    if not name: name = c.execute("SELECT name FROM volunteers WHERE id=?", (actor_id,)).fetchone()
    if not name: name = {"name": actor_id}
    c.execute("""INSERT INTO history(at,actor_id,actor_name,action,donation_id,claim_id,outcome,details)
                 VALUES(?,?,?,?,?,?,?,?)""",
              (state(c), actor_id, name["name"], action, donation_id, claim_id, outcome, details))

def donation_view(c, d):
    d = dict(d)
    d["status"] = donation_status(c, d)
    d["remaining_kg"] = remaining(c, d)
    d["cancelled"] = bool(d["cancelled"])
    donor = c.execute("SELECT name,zone FROM donors WHERE id=?", (d["donor_id"],)).fetchone()
    d["donor_name"] = donor["name"]
    d["zone"] = donor["zone"]
    d["claims"] = claim_rows(c, d["id"])
    return d

def claim_reasons(c, donation, volunteer_id, kg, planned_time):
    reasons = []
    vol = c.execute("SELECT * FROM volunteers WHERE id=?", (volunteer_id,)).fetchone()
    if not vol:
        return ["Choose a valid volunteer."]
    now = dt(state(c))
    status = donation_status(c, donation)
    if status in ("CANCELLED", "EXPIRED"):
        reasons.append(f"Rule 1: donation is {status.lower()}.")
    if kg > vol["capacity_kg"]:
        reasons.append(f"Rule 2: requested {kg} kg exceeds {vol['capacity_kg']} kg volunteer capacity.")
    rem = remaining(c, donation)
    if kg > rem:
        reasons.append(f"Rule 3: requested {kg} kg exceeds {rem} kg remaining.")
    donor = c.execute("SELECT zone FROM donors WHERE id=?", (donation["donor_id"],)).fetchone()
    zones = json.loads(vol["zones"])
    if donor["zone"] not in zones:
        reasons.append(f"Rule 4: {donor['zone']} zone is not in this volunteer's permitted zones.")
    try:
        planned = dt(planned_time)
    except Exception:
        reasons.append("Invalid planned pickup time. Use YYYY-MM-DDTHH:MM.")
        return reasons
    start, end = dt(donation["pickup_from"]), dt(donation["pickup_until"])
    if not start <= planned <= end:
        reasons.append("Rule 5: planned pickup must be inside the donation pickup window.")
    if planned < now:
        reasons.append("Rule 6: planned pickup cannot be before the simulated current time.")
    other = c.execute("""SELECT * FROM claims WHERE volunteer_id=? AND status IN ('ACTIVE','COLLECTED')""",
                      (volunteer_id,)).fetchall()
    for claim in other:
        if abs((planned - dt(claim["planned_time"])).total_seconds()) < 3600:
            reasons.append(f"Rule 7: pickup is less than 60 minutes from claim {claim['id']} ({claim['planned_time']}).")
    return reasons

def update_expired_claims(c):
    now = dt(state(c))
    donations = rows(c, "SELECT * FROM donations")
    for d in donations:
        if not d["cancelled"] and now > dt(d["pickup_until"]):
            c.execute("""UPDATE claims SET status='MISSED'
                         WHERE donation_id=? AND status='ACTIVE'""", (d["id"],))

@app.get("/")
def root():
    return {"app":"SurplusLink","status":"ok"}

@app.get("/api/health")
def health():
    with conn() as c:
        return {"status":"ok","database":"connected","clock":state(c)}

@app.get("/api/bootstrap")
def bootstrap():
    with conn() as c:
        update_expired_claims(c)
        c.commit()
        return {
            "clock": state(c),
            "donors": rows(c, "SELECT * FROM donors ORDER BY name"),
            "volunteers": [{**v,"zones":json.loads(v["zones"])} for v in rows(c,"SELECT * FROM volunteers ORDER BY name")],
            "donations": [donation_view(c,d) for d in rows(c,"SELECT * FROM donations ORDER BY pickup_from")],
            "history": rows(c,"SELECT * FROM history ORDER BY id DESC LIMIT 100")
        }

@app.get("/api/donations")
def donations():
    with conn() as c:
        update_expired_claims(c); c.commit()
        return [donation_view(c,d) for d in rows(c,"SELECT * FROM donations ORDER BY pickup_from")]

@app.post("/api/donations")
def create_donation(data: DonationCreate):
    try:
        start, end = dt(data.pickup_from), dt(data.pickup_until)
    except Exception:
        raise HTTPException(400, "Times must use YYYY-MM-DDTHH:MM.")
    with LOCK, conn() as c:
        now = dt(state(c))
        if not c.execute("SELECT 1 FROM donors WHERE id=?", (data.donor_id,)).fetchone():
            raise HTTPException(400, "Choose a valid donor.")
        if start >= end: raise HTTPException(400, "pickup_from must be before pickup_until.")
        if end < now: raise HTTPException(400, "pickup_until cannot be before the simulated clock.")
        did = "DN" + str(c.execute("SELECT COUNT(*) FROM donations").fetchone()[0] + 1).zfill(3)
        c.execute("""INSERT INTO donations(id,donor_id,description,quantity_kg,pickup_from,pickup_until)
                     VALUES(?,?,?,?,?,?)""",
                  (did,data.donor_id,data.description.strip(),data.quantity_kg,data.pickup_from,data.pickup_until))
        log(c,data.donor_id,"POST_DONATION",did,None,"SUCCESS",f"Posted {data.quantity_kg} kg: {data.description}")
        c.commit()
        return donation_view(c,get_donation(c,did))

@app.post("/api/donations/{donation_id}/cancel")
def cancel_donation(donation_id: str, data: Actor):
    with LOCK, conn() as c:
        d = get_donation(c, donation_id)
        if d["donor_id"] != data.actor_id: raise HTTPException(403, "Only the donor can cancel this donation.")
        if donation_status(c,d) != "OPEN": raise HTTPException(400, "A donation can be cancelled only while OPEN.")
        active = c.execute("SELECT COUNT(*) FROM claims WHERE donation_id=? AND status IN ('ACTIVE','COLLECTED')",(donation_id,)).fetchone()[0]
        if active: raise HTTPException(400, "Cannot cancel a donation with ACTIVE or COLLECTED claims.")
        c.execute("UPDATE donations SET cancelled=1 WHERE id=?", (donation_id,))
        log(c,data.actor_id,"CANCEL_DONATION",donation_id,None,"SUCCESS","Donation cancelled")
        c.commit()
        return donation_view(c,get_donation(c,donation_id))

@app.post("/api/donations/{donation_id}/claims/validate")
def validate_claim(donation_id: str, data: ClaimCreate):
    with conn() as c:
        d = get_donation(c,donation_id)
        return {"valid":len(claim_reasons(c,d,data.volunteer_id,data.kg,data.planned_time)) == 0,
                "reasons":claim_reasons(c,d,data.volunteer_id,data.kg,data.planned_time)}

@app.post("/api/donations/{donation_id}/claims")
def create_claim(donation_id: str, data: ClaimCreate):
    with LOCK, conn() as c:
        c.begin()
        d = c.execute("SELECT * FROM donations WHERE id=? FOR UPDATE", (donation_id,)).fetchone()
        if not d: raise HTTPException(404, "Donation not found")
        d = dict(d)
        reasons = claim_reasons(c,d,data.volunteer_id,data.kg,data.planned_time)
        if reasons:
            c.rollback()
            raise HTTPException(400, detail={"message":"Claim refused","reasons":reasons})
        cid = "CL" + str(c.execute("SELECT COUNT(*) FROM claims").fetchone()[0] + 1).zfill(3)
        c.execute("""INSERT INTO claims(id,donation_id,volunteer_id,kg,planned_time,status,created_at)
                     VALUES(?,?,?,?,?,'ACTIVE',?)""",
                  (cid,donation_id,data.volunteer_id,data.kg,data.planned_time,state(c)))
        log(c,data.volunteer_id,"CLAIM_DONATION",donation_id,cid,"SUCCESS",f"Reserved {data.kg} kg at {data.planned_time}")
        c.commit()
        return get_claim(c,cid)

@app.post("/api/claims/{claim_id}/collect")
def collect_claim(claim_id: str, data: Actor):
    with LOCK, conn() as c:
        claim = get_claim(c,claim_id)
        if claim["volunteer_id"] != data.actor_id: raise HTTPException(403,"Only the claiming volunteer can collect this claim.")
        if claim["status"] != "ACTIVE": raise HTTPException(400,"Only ACTIVE claims can be collected.")
        now = dt(state(c))
        donation = get_donation(c,claim["donation_id"])
        if not dt(donation["pickup_from"]) <= now <= dt(donation["pickup_until"]):
            raise HTTPException(400,"Collection is allowed only during the pickup window.")
        c.execute("UPDATE claims SET status='COLLECTED' WHERE id=?", (claim_id,))
        log(c,data.actor_id,"COLLECT_CLAIM",claim["donation_id"],claim_id,"SUCCESS",f"Collected {claim['kg']} kg")
        c.commit()
        return get_claim(c,claim_id)

@app.post("/api/claims/{claim_id}/cancel")
def cancel_claim(claim_id: str, data: Actor):
    with LOCK, conn() as c:
        claim = get_claim(c,claim_id)
        if claim["volunteer_id"] != data.actor_id: raise HTTPException(403,"Only the claiming volunteer can cancel this claim.")
        if claim["status"] != "ACTIVE": raise HTTPException(400,"Only ACTIVE claims can be cancelled.")
        if not dt(state(c)) < dt(claim["planned_time"]):
            raise HTTPException(400,"A claim can be cancelled only strictly before its planned pickup time.")
        c.execute("UPDATE claims SET status='CANCELLED' WHERE id=?", (claim_id,))
        log(c,data.actor_id,"CANCEL_CLAIM",claim["donation_id"],claim_id,"SUCCESS",f"Cancelled {claim['kg']} kg; quantity returned")
        c.commit()
        return get_claim(c,claim_id)

@app.post("/api/clock")
def update_clock(data: ClockUpdate):
    try: new = dt(data.clock)
    except Exception: raise HTTPException(400,"Clock must use YYYY-MM-DDTHH:MM.")
    with LOCK, conn() as c:
        old = dt(state(c))
        if new < old: raise HTTPException(400,"The simulated clock cannot move backwards.")
        c.execute("UPDATE app_state SET clock=? WHERE id=1", (data.clock,))
        update_expired_claims(c)
        log(c,"SYSTEM","ADVANCE_CLOCK",None,None,"SUCCESS",f"Clock advanced from {stamp(old)} to {stamp(new)}")
        c.commit()
        return {"clock":state(c)}

@app.get("/api/dashboard")
def dashboard():
    with conn() as c:
        update_expired_claims(c); c.commit()
        donations = [dict(d) for d in rows(c,"SELECT * FROM donations WHERE cancelled=0")]
        listed = sum(d["quantity_kg"] for d in donations)
        collected = c.execute("SELECT COALESCE(SUM(kg),0) FROM claims WHERE status='COLLECTED' AND donation_id IN (SELECT id FROM donations WHERE cancelled=0)").fetchone()[0]
        missed = c.execute("SELECT COALESCE(SUM(kg),0) FROM claims WHERE status='MISSED' AND donation_id IN (SELECT id FROM donations WHERE cancelled=0)").fetchone()[0]
        active = c.execute("SELECT COALESCE(SUM(kg),0) FROM claims WHERE status='ACTIVE' AND donation_id IN (SELECT id FROM donations WHERE cancelled=0)").fetchone()[0]
        wasted = sum(remaining(c,d) for d in donations if donation_status(c,d)=="EXPIRED")
        still_open = sum(remaining(c,d) for d in donations if donation_status(c,d)!="EXPIRED")
        donor_stats = []
        for d in rows(c,"SELECT * FROM donors"):
            kg = c.execute("""SELECT COALESCE(SUM(c.kg),0) FROM claims c JOIN donations dn ON dn.id=c.donation_id
                              WHERE dn.donor_id=? AND dn.cancelled=0 AND c.status='COLLECTED'""",(d["id"],)).fetchone()[0]
            donor_stats.append({"id":d["id"],"name":d["name"],"collected_kg":kg})
        volunteer_stats = []
        for v in rows(c,"SELECT * FROM volunteers"):
            vals = c.execute("""SELECT COALESCE(SUM(CASE WHEN status='COLLECTED' THEN kg ELSE 0 END),0),
                                SUM(CASE WHEN status='MISSED' THEN 1 ELSE 0 END)
                                FROM claims WHERE volunteer_id=?""",(v["id"],)).fetchone()
            volunteer_stats.append({"id":v["id"],"name":v["name"],"collected_kg":vals[0] or 0,"missed_claims":vals[1] or 0})
        return {"listed_kg":listed,"collected_kg":collected,"missed_kg":missed,"wasted_kg":wasted,
                "in_progress_kg":active,"still_open_kg":still_open,
                "balanced":listed == collected + missed + wasted + active + still_open,
                "donor_stats":donor_stats,"volunteer_stats":volunteer_stats}

@app.get("/api/history")
def history():
    with conn() as c:
        return rows(c,"SELECT * FROM history ORDER BY id DESC LIMIT 100")
