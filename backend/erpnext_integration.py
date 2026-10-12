"""Delivery tracking bridge. ERP credentials and network calls stay off the phone.

ERPNext owns delivery assignments. RouteOS owns GPS and delivery confirmations.
Only a separate ERP tracking document is written; stock/accounting are untouched.
"""
from __future__ import annotations

import asyncio
from contextlib import closing
from datetime import datetime, timezone, timedelta
import json
import os
import re
import secrets
import sqlite3
import threading
from decimal import Decimal
from http.client import HTTPException as HttpProtocolError
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field, model_validator


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward the integration user's API secret to a redirected host.
        return None


def utc_now() -> str:
    """Local UTC stamp. `app` imports this module, so it cannot be imported back."""
    return datetime.now(timezone.utc).isoformat()


def configuration():
    url = os.getenv("ROUTEOS_ERPNEXT_URL", "").rstrip("/")
    key = os.getenv("ROUTEOS_ERPNEXT_API_KEY", "")
    secret = os.getenv("ROUTEOS_ERPNEXT_API_SECRET", "")
    if not url or not key or not secret:
        raise HTTPException(503, "ERPNext is not configured on the RouteOS backend")
    parsed = urlsplit(url)
    local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if (not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment
            or (parsed.scheme != "https" and not (parsed.scheme == "http" and local))):
        raise HTTPException(503, "ERPNext requires HTTPS, or HTTP on localhost for a local demo")
    return url, key, secret


def erp_request(method, path, body=None, query=None):
    url, key, secret = configuration()
    target = url + quote(path, safe="/%") + ("?" + urlencode(query) if query else "")
    request = Request(target, method=method, headers={
        "Authorization": f"token {key}:{secret}", "Content-Type": "application/json",
        "Accept": "application/json",
    }, data=json.dumps(body).encode() if body is not None else None)
    try:
        with build_opener(NoRedirect()).open(request, timeout=10) as response:
            payload = response.read(2_000_001)
            if len(payload) > 2_000_000:
                raise HTTPException(502, "ERPNext response is too large")
            return json.loads(payload)["data"]
    except HTTPError as error:
        messages = {401: "ERPNext rejected the integration credentials", 403: "ERPNext integration permissions are missing",
                    404: "ERPNext document or tracking schema was not found", 409: "ERPNext document changed; retry sync"}
        raise HTTPException(502, messages.get(error.code, f"ERPNext returned HTTP {error.code}")) from error
    except (URLError, TimeoutError, OSError, ValueError, KeyError, HttpProtocolError) as error:
        raise HTTPException(502, "ERPNext is unavailable or returned an invalid response; retry later") from error


def initialize(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS erp_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS erp_driver_links (
            site TEXT NOT NULL, driver_id INTEGER NOT NULL REFERENCES users(id), erp_driver TEXT NOT NULL,
            PRIMARY KEY(site, driver_id), UNIQUE(site, erp_driver));
        CREATE TABLE IF NOT EXISTS supermarkets (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, address TEXT NOT NULL DEFAULT '',
            latitude REAL NOT NULL, longitude REAL NOT NULL, active INTEGER NOT NULL DEFAULT 1,
            notes TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_supermarkets_name ON supermarkets(name COLLATE NOCASE);
        CREATE TABLE IF NOT EXISTS standing_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, supermarket_id INTEGER NOT NULL REFERENCES supermarkets(id),
            product_name TEXT NOT NULL, uom TEXT NOT NULL, quantity TEXT NOT NULL,
            updated_at TEXT NOT NULL, UNIQUE(supermarket_id, product_name, uom));
        CREATE TABLE IF NOT EXISTS delivery_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT NOT NULL DEFAULT 'native', site TEXT,
            trip TEXT NOT NULL, driver_id INTEGER NOT NULL REFERENCES users(id), erp_driver TEXT,
            ride_id INTEGER UNIQUE REFERENCES rides(id), vehicle TEXT, departure_time TEXT,
            stops TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1, synced_revision INTEGER NOT NULL DEFAULT 0,
            last_sync TEXT, last_error TEXT, attempts INTEGER NOT NULL DEFAULT 0, next_attempt TEXT,
            created_at TEXT NOT NULL, updated_at TEXT);
        CREATE INDEX IF NOT EXISTS idx_deliveries_driver ON delivery_assignments(driver_id, id DESC);
        CREATE TABLE IF NOT EXISTS delivery_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, assignment_id INTEGER NOT NULL REFERENCES delivery_assignments(id),
            actor_id INTEGER NOT NULL REFERENCES users(id), stop_id TEXT NOT NULL,
            status TEXT NOT NULL, reason TEXT NOT NULL, location TEXT, created_at TEXT NOT NULL);
        -- Extra batter a shop asked for. The driver never hands it over on the same
        -- trip; it raises that shop's allocation on the next one, or is reassigned
        -- to another shop so perishable stock is never left over.
        CREATE TABLE IF NOT EXISTS extra_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT, site TEXT, customer TEXT NOT NULL,
            supermarket_id INTEGER REFERENCES supermarkets(id),
            product_name TEXT NOT NULL, uom TEXT NOT NULL, quantity TEXT NOT NULL,
            trip TEXT NOT NULL, stop_id TEXT NOT NULL, actor_id INTEGER NOT NULL REFERENCES users(id),
            status TEXT NOT NULL DEFAULT 'pending', applied_trip TEXT, resolution TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_extra_requests_status ON extra_requests(status, id DESC);
    """)
    db.execute("INSERT OR IGNORE INTO erp_settings VALUES ('instance_id', ?)", (secrets.token_hex(12),))
    if 'items' not in {row['name'] for row in db.execute('PRAGMA table_info(delivery_events)')}:
        db.execute("ALTER TABLE delivery_events ADD COLUMN items TEXT NOT NULL DEFAULT '[]'")
    _migrate(db)


def _columns(db, table):
    return {row['name'] for row in db.execute(f'PRAGMA table_info({table})')}


def _migrate(db):
    """Bring an older database up to the current delivery schema without losing data.

    Earlier revisions stored natively built trips under a `'native'` site with a
    blank ERP driver, and identified supermarkets only by name. Both are replaced
    by real columns, so the table is rebuilt rather than patched.
    """
    columns = _columns(db, 'delivery_assignments')
    legacy = 'source' not in columns
    if legacy:
        db.executescript("""
            ALTER TABLE delivery_assignments RENAME TO delivery_assignments_legacy;
            CREATE TABLE delivery_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT NOT NULL DEFAULT 'native', site TEXT,
                trip TEXT NOT NULL, driver_id INTEGER NOT NULL REFERENCES users(id), erp_driver TEXT,
                ride_id INTEGER UNIQUE REFERENCES rides(id), vehicle TEXT, departure_time TEXT,
                stops TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1, synced_revision INTEGER NOT NULL DEFAULT 0,
                last_sync TEXT, last_error TEXT, attempts INTEGER NOT NULL DEFAULT 0, next_attempt TEXT,
                created_at TEXT NOT NULL, updated_at TEXT);
        """)
        db.execute("""INSERT INTO delivery_assignments
            (id,source,site,trip,driver_id,erp_driver,ride_id,vehicle,departure_time,stops,revision,
             synced_revision,last_sync,last_error,attempts,next_attempt,created_at,updated_at)
            SELECT id, CASE WHEN site='native' THEN 'native' ELSE 'erpnext' END, NULLIF(site,'native'),
                   trip, driver_id, NULLIF(erp_driver,''), ride_id, vehicle, departure_time, stops, revision,
                   synced_revision, last_sync, last_error, attempts, next_attempt, created_at,
                   COALESCE(last_sync, created_at)
            FROM delivery_assignments_legacy""")
        db.execute("DROP TABLE delivery_assignments_legacy")

    # Native trips have no ERP site, so uniqueness is enforced per source instead.
    # SQLite treats NULLs in a UNIQUE column as distinct, hence the partial indexes.
    db.executescript("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_deliveries_trip_native
            ON delivery_assignments(trip) WHERE site IS NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_deliveries_trip_erp
            ON delivery_assignments(site, trip) WHERE site IS NOT NULL;
    """)
    if 'supermarket_id' not in _columns(db, 'extra_requests'):
        db.execute("ALTER TABLE extra_requests ADD COLUMN supermarket_id INTEGER REFERENCES supermarkets(id)")
    # Client polling needs a change timestamp that every delivery edit refreshes.
    # `last_sync` only moves for ERPNext rows, so it cannot drive that cursor.
    db.execute("UPDATE delivery_assignments SET updated_at=COALESCE(last_sync, created_at) WHERE updated_at IS NULL")

    # Any shop mentioned so far becomes a directory entry, so history keeps its link.
    names = {row['customer'] for row in db.execute('SELECT customer FROM extra_requests')}
    for row in db.execute('SELECT stops FROM delivery_assignments'):
        names.update(stop.get('customer') for stop in json.loads(row['stops']) if stop.get('customer'))
    now = utc_now()
    for name in sorted(n for n in names if n):
        db.execute("""INSERT OR IGNORE INTO supermarkets(name,latitude,longitude,active,created_at,updated_at)
            VALUES (?,0,0,1,?,?)""", (name, now, now))
    _link_supermarkets(db)


def _link_supermarkets(db):
    """Attach stops and extra requests to their directory entry by name."""
    by_name = {row['name']: row['id'] for row in db.execute('SELECT id,name FROM supermarkets')}
    for row in db.execute('SELECT id,stops FROM delivery_assignments').fetchall():
        stops = json.loads(row['stops'])
        changed = False
        for stop in stops:
            supermarket_id = by_name.get(stop.get('customer'))
            if supermarket_id and stop.get('supermarket_id') != supermarket_id:
                stop['supermarket_id'] = supermarket_id
                changed = True
        if changed:
            db.execute('UPDATE delivery_assignments SET stops=? WHERE id=?', (json.dumps(stops), row['id']))
    db.execute("""UPDATE extra_requests SET supermarket_id=(
        SELECT id FROM supermarkets WHERE supermarkets.name=extra_requests.customer)
        WHERE supermarket_id IS NULL""")


class ImportTrip(BaseModel):
    trip: str = Field(min_length=1, max_length=140)
    driver_id: int = Field(gt=0)


class AttachRide(BaseModel):
    ride_id: int = Field(gt=0)


class ProductPlan(BaseModel):
    item_code: str = Field(default="", max_length=140)
    product_name: str = Field(min_length=1, max_length=140)
    uom: str = Field(min_length=1, max_length=40)
    planned_quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)

    @model_validator(mode="after")
    def nonblank(self):
        self.product_name, self.uom = self.product_name.strip(), self.uom.strip()
        if not self.product_name or not self.uom:
            raise ValueError("Product name and unit are required")
        return self


class ProductList(BaseModel):
    items: list[ProductPlan] = Field(min_length=1, max_length=100)


class StopIn(BaseModel):
    """One supermarket on a natively built trip."""
    stop_ref: str = Field(default="", max_length=140)
    customer: str = Field(min_length=1, max_length=140)
    supermarket_id: int | None = Field(default=None, gt=0)
    address: str = Field(default="", max_length=500)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    items: list[ProductPlan] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def trimmed(self):
        self.customer = self.customer.strip()
        if not self.customer:
            raise ValueError("Supermarket name is required")
        return self


class SupermarketIn(BaseModel):
    """Directory entry for a shop RouteOS delivers to."""
    name: str = Field(min_length=1, max_length=140)
    address: str = Field(default="", max_length=500)
    latitude: float = Field(default=0, ge=-90, le=90)
    longitude: float = Field(default=0, ge=-180, le=180)
    notes: str = Field(default="", max_length=500)
    standing_order: list[ProductPlan] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def trimmed(self):
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("Supermarket name is required")
        return self


class StandingOrderIn(BaseModel):
    """The usual allocation for a shop, used when a trip is built."""
    items: list[ProductPlan] = Field(min_length=1, max_length=100)


class TransferIn(BaseModel):
    """Move planned batter from one stop to another, so nothing is left over."""
    from_stop_id: str = Field(min_length=1, max_length=140)
    to_stop_id: str = Field(min_length=1, max_length=140)
    product_name: str = Field(min_length=1, max_length=140)
    uom: str = Field(min_length=1, max_length=40)
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)

    @model_validator(mode="after")
    def distinct_stops(self):
        self.product_name, self.uom = self.product_name.strip(), self.uom.strip()
        if self.from_stop_id == self.to_stop_id:
            raise ValueError("Choose two different supermarkets")
        if not self.product_name or not self.uom:
            raise ValueError("Product name and unit are required")
        return self


class TripIn(BaseModel):
    """A delivery trip created directly by an admin, without ERPNext."""
    trip: str = Field(min_length=1, max_length=140)
    driver_id: int = Field(gt=0)
    vehicle: str = Field(default="", max_length=60)
    stops: list[StopIn] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_stops(self):
        self.trip = self.trip.strip()
        if not self.trip:
            raise ValueError("Trip reference is required")
        seen = set()
        for stop in self.stops:
            key = stop.stop_ref.strip()
            if not key:
                raise ValueError("Each stop needs a reference")
            if key in seen:
                raise ValueError(f"Duplicate stop reference: {key}")
            seen.add(key)
        return self


class ProductDelivered(BaseModel):
    id: str = Field(min_length=1, max_length=140)
    delivered_quantity: Decimal = Field(ge=0, max_digits=12, decimal_places=3)


class ExtraRequested(BaseModel):
    """More batter a shop asked for, recorded at the stop for the next trip."""
    product_name: str = Field(min_length=1, max_length=140)
    uom: str = Field(min_length=1, max_length=40)
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)

    @model_validator(mode="after")
    def trimmed(self):
        self.product_name, self.uom = self.product_name.strip(), self.uom.strip()
        if not self.product_name or not self.uom:
            raise ValueError("Product name and unit are required")
        return self


class ExtraRequestIn(BaseModel):
    items: list[ExtraRequested] = Field(default_factory=list, max_length=100)


class ResolveExtras(BaseModel):
    """Close extra requests that are now planned into a trip or moved elsewhere."""

    ids: list[int] = Field(min_length=1, max_length=200)
    note: str = Field(default="", max_length=200)


class StopUpdate(BaseModel):
    status: str = Field(pattern="^(arrived|delivered|partial|failed)$")
    reason: str = Field(default="", max_length=500)
    items: list[ProductDelivered] = Field(default_factory=list, max_length=100)
    extras: list[ExtraRequested] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def failure_reason(self):
        self.reason = self.reason.strip()
        if self.status in ("failed", "partial") and not self.reason:
            raise ValueError("Explain why the delivery failed or was short")
        return self


class DeliveryIntegration:
    def __init__(self, connection, now):
        self.connection, self.now = connection, now
        self.sync_lock = threading.Lock()

    @staticmethod
    def admin(me):
        if me["role"] != "admin":
            raise HTTPException(403, "admin access required")

    @staticmethod
    def authorized(db, assignment_id, me):
        row = db.execute("SELECT * FROM delivery_assignments WHERE id=?", (assignment_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "delivery assignment not found")
        if me["role"] != "admin" and row["driver_id"] != me["id"]:
            raise HTTPException(403, "delivery belongs to another driver")
        return row

    @staticmethod
    def extras_signature(extras):
        """Comparable form so a retried confirmation does not duplicate requests."""
        return {(item.product_name, item.uom, str(item.quantity)) for item in extras}

    def snapshot(self, db, row):
        result = dict(row)
        result["stops"] = json.loads(row["stops"])
        for stop in result["stops"]:
            stop.setdefault('items', [])
        user = db.execute("SELECT name FROM users WHERE id=?", (row["driver_id"],)).fetchone()
        result["driver_name"] = user["name"]
        result["ride"] = None
        result["location"] = None
        if row["ride_id"]:
            ride = db.execute("SELECT id,status,started_at,ended_at FROM rides WHERE id=?", (row["ride_id"],)).fetchone()
            result["ride"] = dict(ride) if ride else None
            location = db.execute("""SELECT latitude,longitude,speed_mps,bearing,accuracy_meters,recorded_at
                FROM live_locations WHERE ride_id=? ORDER BY recorded_at DESC,id DESC LIMIT 1""", (row["ride_id"],)).fetchone()
            result["location"] = dict(location) if location else None
        delivered = sum(stop["status"] == "delivered" for stop in result["stops"])
        failed = sum(stop["status"] == "failed" for stop in result["stops"])
        partial = sum(stop["status"] == "partial" for stop in result["stops"])
        result["status"] = ("Delivered" if delivered == len(result["stops"]) else
                            "Closed with failures" if failed and delivered + failed + partial == len(result["stops"]) else
                            "Closed with shortages" if partial and delivered + partial == len(result["stops"]) else
                            "In progress" if row["ride_id"] else "Assigned")
        result["sync_pending"] = row["revision"] != row["synced_revision"]
        result["sync_pending"] |= bool(row["last_error"])
        if result["ride"] and result["ride"]["ended_at"]:
            result["sync_pending"] |= not row["last_sync"] or result["ride"]["ended_at"] > row["last_sync"]
        result["source"] = row["source"] or "native"
        # Batter still on the van: planned but not yet handed over. Anything left
        # when the trip closes is what would spoil.
        surplus = {}
        for stop in result['stops']:
            if stop['status'] in ('delivered', 'partial', 'failed'):
                continue
            for item in stop['items']:
                key = (item['product_name'], item['uom'])
                surplus[key] = surplus.get(key, Decimal(0)) + (
                    Decimal(str(item['planned_quantity'])) - Decimal(str(item['delivered_quantity'])))
        result['surplus'] = [{'product_name': name, 'uom': uom, 'quantity': str(amount)}
                             for (name, uom), amount in surplus.items()]
        result["events"] = [dict(event) for event in db.execute(
            "SELECT actor_id,stop_id,status,reason,location,created_at,items FROM delivery_events WHERE assignment_id=? ORDER BY id",
            (row["id"],))]
        for event in result['events']:
            event['items'] = json.loads(event['items'])
        totals = {}
        for stop in result['stops']:
            for item in stop['items']:
                key = (item['item_code'] or item['product_name'], item['uom'])
                total = totals.setdefault(key, {'product_name':item['product_name'], 'uom':item['uom'],
                                                'planned_quantity':Decimal(0), 'delivered_quantity':Decimal(0)})
                total['planned_quantity'] += Decimal(str(item['planned_quantity']))
                total['delivered_quantity'] += Decimal(str(item['delivered_quantity']))
        result['product_totals'] = [{**item, 'planned_quantity':str(item['planned_quantity']),
                                    'delivered_quantity':str(item['delivered_quantity'])} for item in totals.values()]
        return result

    def sync(self, force=False):
        # Serial writes prevent an older snapshot overwriting a newer one in ERPNext.
        if not self.sync_lock.acquire(blocking=False):
            return {"synced": 0, "failed": 0, "busy": True}
        try:
            site, _, _ = configuration()
            captured_at = self.now()
            with closing(self.connection()) as db:
                rows = db.execute("""SELECT a.* FROM delivery_assignments a LEFT JOIN rides r ON r.id=a.ride_id
                    WHERE a.site=? AND (a.revision!=a.synced_revision OR r.status='active'
                        OR (r.ended_at IS NOT NULL AND (a.last_sync IS NULL OR r.ended_at>a.last_sync)))
                    AND (? OR a.next_attempt IS NULL OR a.next_attempt<=?) ORDER BY a.id LIMIT 100""",
                    (site, int(force), self.now())).fetchall()
                instance = db.execute("SELECT value FROM erp_settings WHERE key='instance_id'").fetchone()[0]
                snapshots = [(row, self.snapshot(db, row)) for row in rows]
            counts = {"synced": 0, "failed": 0, "busy": False}
            for row, snapshot in snapshots:
                name = f"ROUTEOS-{instance}-{row['id']}"
                body = {"delivery_trip": row["trip"], "driver": row["erp_driver"],
                        "tracking_status": snapshot["status"], "tracking_data": json.dumps(snapshot),
                        "last_update_utc": captured_at, "routeos_reference": name}
                try:
                    # Custom DocType autonames from routeos_reference: PUT is idempotent.
                    existing = erp_request("GET", "/api/resource/RouteOS Delivery Tracking", query={
                        "filters": json.dumps([["name", "=", name]]), "fields": '["name"]', "limit_page_length": 1})
                    if existing:
                        erp_request("PUT", "/api/resource/RouteOS Delivery Tracking/" + quote(name, safe=""), body)
                    else:
                        erp_request("POST", "/api/resource/RouteOS Delivery Tracking", body)
                    with closing(self.connection()) as db:
                        db.execute("""UPDATE delivery_assignments SET synced_revision=?,last_sync=?,last_error=NULL,
                            attempts=0,next_attempt=NULL WHERE id=?""", (row["revision"], captured_at, row["id"]))
                        db.commit()
                    counts["synced"] += 1
                except HTTPException as error:
                    retry_at = datetime.now(timezone.utc) + timedelta(seconds=min(300, 30 * 2 ** min(row["attempts"], 4)))
                    with closing(self.connection()) as db:
                        db.execute("""UPDATE delivery_assignments SET last_error=?,attempts=attempts+1,next_attempt=?
                            WHERE id=?""", (str(error.detail), retry_at.isoformat(), row["id"]))
                        db.commit()
                    counts["failed"] += 1
            return counts
        finally:
            self.sync_lock.release()

    def supermarket(self, db, row):
        """Directory entry with the shop's usual allocation attached."""
        result = dict(row)
        result['standing_order'] = [dict(item) for item in db.execute(
            """SELECT product_name,uom,quantity FROM standing_orders WHERE supermarket_id=?
                ORDER BY product_name COLLATE NOCASE""", (row['id'],))]
        return result

    def save_standing_order(self, db, supermarket_id, items):
        db.execute("DELETE FROM standing_orders WHERE supermarket_id=?", (supermarket_id,))
        for item in items:
            db.execute("""INSERT INTO standing_orders(supermarket_id,product_name,uom,quantity,updated_at)
                VALUES (?,?,?,?,?)""", (supermarket_id, item.product_name, item.uom,
                                        str(item.planned_quantity), self.now()))

    def rename_stops(self, db, supermarket_id, name):
        """Keep history readable after a shop is renamed."""
        for row in db.execute('SELECT id,stops FROM delivery_assignments').fetchall():
            stops = json.loads(row['stops'])
            changed = False
            for stop in stops:
                if stop.get('supermarket_id') == supermarket_id and stop.get('customer') != name:
                    stop['customer'] = name
                    changed = True
            if changed:
                db.execute('UPDATE delivery_assignments SET stops=? WHERE id=?', (json.dumps(stops), row['id']))
        db.execute("UPDATE extra_requests SET customer=? WHERE supermarket_id=?", (name, supermarket_id))

    async def run(self):
        while True:
            await asyncio.sleep(30)
            try:
                await asyncio.to_thread(self.sync)
            except HTTPException:
                pass  # Unconfigured integration must never stop the existing app.
            except Exception:
                import logging
                logging.getLogger("uvicorn.error").exception("RouteOS ERPNext sync failed")

    def register(self, app, current_user, external_client=None):
        @app.get("/api/v1/deliveries")
        def deliveries(me=Depends(current_user)):
            with closing(self.connection()) as db:
                rows = db.execute("SELECT * FROM delivery_assignments WHERE (? OR driver_id=?) ORDER BY id DESC LIMIT 100",
                                  (int(me["role"] == "admin"), me["id"])).fetchall()
                return {"assignments": [self.snapshot(db, row) for row in rows]}

        @app.get("/api/v1/supermarkets")
        def supermarkets(me=Depends(current_user)):
            """Supermarket directory with each shop's usual allocation."""
            with closing(self.connection()) as db:
                return {"supermarkets": [self.supermarket(db, row) for row in db.execute(
                    "SELECT * FROM supermarkets ORDER BY active DESC, name COLLATE NOCASE")]}
        @app.post("/api/v1/supermarkets", status_code=201)
        def create_supermarket(body: SupermarketIn, me=Depends(current_user)):
            self.admin(me)
            now = self.now()
            with closing(self.connection()) as db:
                if db.execute("SELECT 1 FROM supermarkets WHERE name=? COLLATE NOCASE",
                              (body.name,)).fetchone():
                    raise HTTPException(409, "That supermarket is already in the directory")
                cursor = db.execute("""INSERT INTO supermarkets(name,address,latitude,longitude,notes,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?)""", (body.name, body.address.strip(), body.latitude, body.longitude,
                                                body.notes.strip(), now, now))
                self.save_standing_order(db, cursor.lastrowid, body.standing_order)
                db.commit()
                return self.supermarket(db, db.execute("SELECT * FROM supermarkets WHERE id=?",
                                                        (cursor.lastrowid,)).fetchone())
        @app.patch("/api/v1/supermarkets/{supermarket_id}")
        def update_supermarket(supermarket_id: int, body: SupermarketIn, me=Depends(current_user)):
            """Edit a shop. Its name is free to change: history keeps pointing at the same row."""
            self.admin(me)
            with closing(self.connection()) as db:
                row = db.execute("SELECT * FROM supermarkets WHERE id=?", (supermarket_id,)).fetchone()
                if row is None:
                    raise HTTPException(404, "supermarket not found")
                clash = db.execute("SELECT id FROM supermarkets WHERE name=? COLLATE NOCASE AND id<>?",
                                   (body.name, supermarket_id)).fetchone()
                if clash:
                    raise HTTPException(409, "Another supermarket already uses that name")
                db.execute("""UPDATE supermarkets SET name=?,address=?,latitude=?,longitude=?,notes=?,updated_at=?
                    WHERE id=?""", (body.name, body.address.strip(), body.latitude, body.longitude,
                                    body.notes.strip(), self.now(), supermarket_id))
                self.save_standing_order(db, supermarket_id, body.standing_order)
                # Stops keep a snapshot of the shop they visited, but follow a rename.
                self.rename_stops(db, supermarket_id, body.name)
                db.commit()
                return self.supermarket(db, db.execute("SELECT * FROM supermarkets WHERE id=?",
                                                        (supermarket_id,)).fetchone())
        @app.post("/api/v1/supermarkets/{supermarket_id}/standing-order")
        def set_standing_order(supermarket_id: int, body: StandingOrderIn, me=Depends(current_user)):
            """Replace the usual allocation, so trips can be built without retyping."""
            self.admin(me)
            with closing(self.connection()) as db:
                if db.execute("SELECT 1 FROM supermarkets WHERE id=?", (supermarket_id,)).fetchone() is None:
                    raise HTTPException(404, "supermarket not found")
                self.save_standing_order(db, supermarket_id, body.items)
                db.commit()
                return self.supermarket(db, db.execute("SELECT * FROM supermarkets WHERE id=?",
                                                        (supermarket_id,)).fetchone())

        @app.post("/api/v1/deliveries/trips", status_code=201)
        def create_trip(body: TripIn, me=Depends(current_user)):
            """Create a delivery trip from the admin panel, without ERPNext."""
            self.admin(me)
            with closing(self.connection()) as db:
                existing = db.execute('SELECT * FROM delivery_assignments WHERE site IS NULL AND trip=?',
                                      (body.trip,)).fetchone()
                if existing:
                    if existing['driver_id'] != body.driver_id:
                        raise HTTPException(409, 'Trip is already assigned to another RouteOS driver')
                    return self.snapshot(db, existing)
                driver = db.execute("SELECT role FROM users WHERE id=?", (body.driver_id,)).fetchone()
                if not driver or driver["role"] != "driver":
                    raise HTTPException(422, "Choose a RouteOS driver account")
                seen_supermarkets = set()
                for stop in body.stops:
                    if stop.supermarket_id is None:
                        continue
                    if stop.supermarket_id in seen_supermarkets:
                        raise HTTPException(409, "A supermarket can only appear once on a trip")
                    seen_supermarkets.add(stop.supermarket_id)
                    shop = db.execute("SELECT * FROM supermarkets WHERE id=?", (stop.supermarket_id,)).fetchone()
                    if shop is None:
                        raise HTTPException(422, f"Unknown supermarket: {stop.customer}")
                    if not shop["active"]:
                        raise HTTPException(409, f"{shop['name']} is no longer active")
                stops = [{"id": stop.stop_ref.strip(), "customer": stop.customer,
                          "supermarket_id": stop.supermarket_id,
                          "address": stop.address, "address_text": stop.address, "delivery_note": None,
                          "latitude": stop.latitude, "longitude": stop.longitude,
                          "status": "pending", "reason": "", "confirmed_at": None,
                          "items": [{'id': secrets.token_hex(12), **item.model_dump(mode='json'),
                                     'delivered_quantity': '0'} for item in stop.items]}
                         for stop in body.stops]
                db.execute("BEGIN IMMEDIATE")
                try:
                    cursor = db.execute("""INSERT INTO delivery_assignments
                        (source,trip,driver_id,vehicle,stops,created_at,updated_at) VALUES ('native',?,?,?,?,?,?)""",
                        (body.trip, body.driver_id, body.vehicle.strip(),
                         json.dumps(stops), self.now(), self.now()))
                    db.commit()
                except sqlite3.IntegrityError as error:
                    raise HTTPException(409, "Trip already exists") from error
                return self.snapshot(db, db.execute("SELECT * FROM delivery_assignments WHERE id=?",
                                                    (cursor.lastrowid,)).fetchone())

        @app.post("/api/v1/deliveries/{assignment_id}/transfer")
        def transfer_planned(assignment_id: int, body: TransferIn, me=Depends(current_user)):
            """Move planned quantity between stops on a trip that has not started.

            Batter is perishable, so batter a shop will not take is given to
            another shop on the same trip instead of being left over.
            """
            self.admin(me)
            with closing(self.connection()) as db:
                db.execute("BEGIN IMMEDIATE")
                row = self.authorized(db, assignment_id, me)
                if row["ride_id"]:
                    raise HTTPException(409, "The trip has already started; outcomes can no longer be changed")
                stops = json.loads(row["stops"])
                source = next((item for item in stops if item["id"] == body.from_stop_id), None)
                target = next((item for item in stops if item["id"] == body.to_stop_id), None)
                if source is None or target is None:
                    raise HTTPException(404, "delivery stop not found")
                moving = Decimal(str(body.quantity))
                found = False
                for item in source['items']:
                    if item['product_name'] == body.product_name and item['uom'] == body.uom:
                        found = True
                        planned = Decimal(str(item['planned_quantity']))
                        if moving >= planned:
                            raise HTTPException(422, 'Move less than the planned quantity, or remove the line')
                        item['planned_quantity'] = str(planned - moving)
                if not found:
                    raise HTTPException(422, f"{body.product_name} is not planned for the first supermarket")
                receiving = next((item for item in target['items']
                                  if item['product_name'] == body.product_name and item['uom'] == body.uom), None)
                if receiving is None:
                    target['items'].append({'id': secrets.token_hex(12), 'item_code': '',
                                            'product_name': body.product_name, 'uom': body.uom,
                                            'planned_quantity': str(moving), 'delivered_quantity': '0'})
                else:
                    receiving['planned_quantity'] = str(Decimal(str(receiving['planned_quantity'])) + moving)
                    if receiving.get('delivered_quantity') not in (None, '0'):
                        raise HTTPException(409, "The second supermarket has already confirmed this product")
                now = self.now()
                db.execute("UPDATE delivery_assignments SET stops=?,revision=revision+1,next_attempt=NULL,updated_at=? WHERE id=?",
                           (json.dumps(stops), now, assignment_id))
                db.commit()
                return self.snapshot(db, db.execute("SELECT * FROM delivery_assignments WHERE id=?",
                                                    (assignment_id,)).fetchone())

        @app.get("/api/v1/erpnext/catalog")
        def catalog(me=Depends(current_user)):
            self.admin(me)
            trips = erp_request("GET", "/api/resource/Delivery Trip", query={
                "filters": '[["docstatus","=",1],["status","in",["Scheduled","In Transit"]]]',
                "fields": '["name","driver","driver_name","vehicle","departure_time","status"]',
                "order_by": "departure_time desc", "limit_page_length": 100})
            with closing(self.connection()) as db:
                drivers = [dict(row) for row in db.execute("SELECT id,name FROM users WHERE role='driver' ORDER BY name")]
            return {"trips": trips, "drivers": drivers}

        @app.post("/api/v1/erpnext/import", status_code=201)
        def import_trip(body: ImportTrip, me=Depends(current_user)):
            self.admin(me)
            site, _, _ = configuration()
            with closing(self.connection()) as db:
                existing = db.execute('SELECT * FROM delivery_assignments WHERE site=? AND trip=?', (site, body.trip)).fetchone()
                if existing:
                    if existing['driver_id'] != body.driver_id:
                        raise HTTPException(409, 'Trip is already assigned to another RouteOS driver')
                    return self.snapshot(db, existing)
            trip = erp_request("GET", "/api/resource/Delivery Trip/" + quote(body.trip, safe=""))
            if trip.get("docstatus") != 1 or trip.get("status") not in ("Scheduled", "In Transit"):
                raise HTTPException(409, "Only submitted, scheduled or in-transit trips can be assigned")
            if not trip.get("driver") or not trip.get("delivery_stops"):
                raise HTTPException(409, "ERPNext trip needs a driver and delivery stops")
            stops = [{"id": stop["name"], "customer": stop.get("customer"), "address": stop.get("address"),
                      "address_text": re.sub(r"<[^>]*>", " ", stop.get("customer_address") or ""),
                      "delivery_note": stop.get("delivery_note"), "latitude": stop.get("lat"),
                      "longitude": stop.get("lng"), "status": "pending", "reason": "", "confirmed_at": None}
                     for stop in trip["delivery_stops"]]
            notes = {}
            for stop in stops:
                stop['items'] = []
                note_name = stop['delivery_note']
                if not note_name:
                    continue
                if note_name in notes:
                    raise HTTPException(409, 'A Delivery Note cannot be counted at multiple stops')
                note = erp_request('GET', '/api/resource/Delivery Note/' + quote(note_name, safe=''))
                if note.get('docstatus') != 1 or note.get('is_return'):
                    raise HTTPException(409, 'Delivery quantities require a submitted, non-return Delivery Note')
                if note.get('customer') != stop['customer']:
                    raise HTTPException(409, 'Delivery Note customer does not match the trip stop')
                for item in note.get('items', []):
                    try:
                        product = ProductPlan(item_code=item['item_code'], product_name=item.get('item_name') or item['item_code'],
                                              uom=item['uom'], planned_quantity=item['qty'])
                    except (ValueError, KeyError) as error:
                        raise HTTPException(409, 'ERPNext product quantity or unit is invalid') from error
                    stop['items'].append({'id':item['name'], **product.model_dump(mode='json'), 'delivered_quantity':'0'})
                if not stop['items'] or len(stop['items']) > 100:
                    raise HTTPException(409, 'Delivery Note must have between 1 and 100 product rows')
                notes[note_name] = note
            with closing(self.connection()) as db:
                db.execute("BEGIN IMMEDIATE")
                existing = db.execute("SELECT * FROM delivery_assignments WHERE site=? AND trip=?", (site, body.trip)).fetchone()
                if existing:
                    if existing["driver_id"] != body.driver_id:
                        raise HTTPException(409, "Trip is already assigned to another RouteOS driver")
                    return self.snapshot(db, existing)  # Never reset delivery confirmations on re-import.
                driver = db.execute("SELECT role FROM users WHERE id=?", (body.driver_id,)).fetchone()
                if not driver or driver["role"] != "driver":
                    raise HTTPException(422, "Choose a RouteOS driver account")
                try:
                    db.execute("INSERT OR IGNORE INTO erp_driver_links VALUES (?,?,?)", (site, body.driver_id, trip["driver"]))
                    link = db.execute("SELECT erp_driver FROM erp_driver_links WHERE site=? AND driver_id=?", (site, body.driver_id)).fetchone()
                    if not link or link[0] != trip["driver"]:
                        raise HTTPException(409, "ERPNext driver is linked to another RouteOS driver")
                    cursor = db.execute("""INSERT INTO delivery_assignments
                        (site,trip,driver_id,erp_driver,vehicle,departure_time,stops,created_at) VALUES (?,?,?,?,?,?,?,?)""",
                        (site, body.trip, body.driver_id, trip["driver"], trip.get("vehicle"), trip.get("departure_time"),
                         json.dumps(stops), self.now()))
                    db.commit()
                except sqlite3.IntegrityError as error:
                    raise HTTPException(409, "Trip or driver is already linked") from error
                return self.snapshot(db, db.execute("SELECT * FROM delivery_assignments WHERE id=?", (cursor.lastrowid,)).fetchone())

        @app.post('/api/v1/deliveries/{assignment_id}/stops/{stop_id}/products')
        def assign_products(assignment_id: int, stop_id: str, body: ProductList, me=Depends(current_user)):
            self.admin(me)
            with closing(self.connection()) as db:
                db.execute('BEGIN IMMEDIATE')
                row = self.authorized(db, assignment_id, me)
                stops = json.loads(row['stops'])
                stop = next((item for item in stops if item['id'] == stop_id), None)
                if not stop:
                    raise HTTPException(404, 'delivery stop not found')
                if row['ride_id'] or stop['status'] != 'pending' or stop['delivery_note']:
                    raise HTTPException(409, 'Products can only be assigned before a ride, on stops without a Delivery Note')
                stop['items'] = [{'id':secrets.token_hex(12), **item.model_dump(mode='json'), 'delivered_quantity':'0'}
                                 for item in body.items]
                db.execute('UPDATE delivery_assignments SET stops=?,revision=revision+1,next_attempt=NULL,updated_at=? WHERE id=?',
                           (json.dumps(stops), self.now(), assignment_id))
                db.commit()
                return self.snapshot(db, db.execute('SELECT * FROM delivery_assignments WHERE id=?', (assignment_id,)).fetchone())

        @app.post("/api/v1/deliveries/{assignment_id}/ride")
        def attach_ride(assignment_id: int, body: AttachRide, me=Depends(current_user)):
            with closing(self.connection()) as db:
                db.execute("BEGIN IMMEDIATE")
                row = self.authorized(db, assignment_id, me)
                if row["ride_id"] == body.ride_id:
                    return self.snapshot(db, row)
                if row["ride_id"]:
                    raise HTTPException(409, "Delivery already has a ride; it cannot be replaced")
                ride = db.execute("SELECT * FROM rides WHERE id=?", (body.ride_id,)).fetchone()
                if not ride or ride["driver_id"] != row["driver_id"] or ride["status"] != "active":
                    raise HTTPException(409, "Link an active ride belonging to the assigned driver")
                if ride["vehicle_number"].strip().casefold() != (row["vehicle"] or "").strip().casefold():
                    raise HTTPException(409, "Ride vehicle number must match the ERPNext delivery vehicle")
                try:
                    db.execute("UPDATE delivery_assignments SET ride_id=?,revision=revision+1,updated_at=? WHERE id=?",
                               (body.ride_id, self.now(), assignment_id))
                    db.commit()
                except sqlite3.IntegrityError as error:
                    raise HTTPException(409, "Ride is already linked to another delivery trip") from error
                return self.snapshot(db, db.execute("SELECT * FROM delivery_assignments WHERE id=?", (assignment_id,)).fetchone())

        @app.post("/api/v1/deliveries/{assignment_id}/stops/{stop_id}")
        def update_stop(assignment_id: int, stop_id: str, body: StopUpdate, me=Depends(current_user)):
            with closing(self.connection()) as db:
                db.execute("BEGIN IMMEDIATE")
                row = self.authorized(db, assignment_id, me)
                stops = json.loads(row["stops"])
                stop = next((item for item in stops if item["id"] == stop_id), None)
                if stop is None:
                    raise HTTPException(404, "delivery stop not found")
                if not row["ride_id"]:
                    raise HTTPException(409, "Start and link the assigned driver's ride first")
                products = stop.setdefault('items', [])
                submitted = {item.id: str(item.delivered_quantity) for item in body.items}
                if len(submitted) != len(body.items):
                    raise HTTPException(422, 'Duplicate product rows')
                if body.status in ('delivered', 'partial'):
                    if not products:
                        raise HTTPException(409, 'Ask the admin to assign products and quantities before confirming delivery')
                    if set(submitted) != {item['id'] for item in products}:
                        raise HTTPException(422, 'Enter delivered quantity for every assigned product')
                    for item in products:
                        if Decimal(submitted[item['id']]) > Decimal(str(item['planned_quantity'])):
                            raise HTTPException(422, 'Delivered quantity cannot exceed the assigned quantity')
                    complete = all(Decimal(submitted[item['id']]) == Decimal(str(item['planned_quantity'])) for item in products)
                    positive = any(Decimal(value) > 0 for value in submitted.values())
                    if body.status == 'delivered' and not complete:
                        raise HTTPException(422, 'Use partial delivery and give a reason for shortages')
                    if body.status == 'partial' and (complete or not positive):
                        raise HTTPException(422, 'Partial delivery requires some goods delivered and some short; use failed for zero')
                elif body.items:
                    raise HTTPException(422, 'Only delivered or partial outcomes accept product quantities')
                same_items = all(Decimal(str(item['delivered_quantity'])) == Decimal(submitted.get(item['id'], '0'))
                                 for item in products)
                recorded = {(item["product_name"], item["uom"], str(item["quantity"])) for item in
                            db.execute("""SELECT product_name,uom,quantity FROM extra_requests
                                WHERE trip=? AND stop_id=? AND status='pending'""",
                                       (row["trip"], stop_id)).fetchall()}
                submitted_extras = self.extras_signature(body.extras)
                same_extras = not (submitted_extras - recorded)
                if (stop["status"] == body.status and stop["reason"] == body.reason
                        and same_items and same_extras):
                    return self.snapshot(db, row)
                if stop["status"] in ("delivered", "partial", "failed"):
                    raise HTTPException(409, "Confirmed delivery outcomes cannot be overwritten")
                now = self.now()
                location = self.snapshot(db, row)["location"]
                stop.update(status=body.status, reason=body.reason, confirmed_at=now)
                for item in products:
                    item['delivered_quantity'] = submitted.get(item['id'], '0')
                db.execute("UPDATE delivery_assignments SET stops=?,revision=revision+1,next_attempt=NULL,updated_at=? WHERE id=?",
                           (json.dumps(stops), now, assignment_id))
                db.execute("""INSERT INTO delivery_events(assignment_id,actor_id,stop_id,status,reason,location,created_at,items)
                    VALUES (?,?,?,?,?,?,?,?)""", (assignment_id, me["id"], stop_id, body.status, body.reason,
                                              json.dumps(location), now, json.dumps(products)))
                # The request is for a later trip, never extra handed over now.
                for signature in sorted(submitted_extras - recorded):
                    product_name, uom, quantity = signature
                    db.execute("""INSERT INTO extra_requests
                        (site,customer,supermarket_id,product_name,uom,quantity,trip,stop_id,actor_id,
                         created_at,updated_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                        (row["site"], stop["customer"], stop.get("supermarket_id"), product_name, uom,
                         quantity, row["trip"], stop_id, me["id"], now, now))
                db.commit()
                return self.snapshot(db, db.execute("SELECT * FROM delivery_assignments WHERE id=?", (assignment_id,)).fetchone())

        @app.get("/api/v1/reports/deliveries")
        def delivery_report(me=Depends(current_user)):
            """Delivery results for the admin, built on the client's own read model.

            Rendering this screen and the customer's polling endpoint from the same
            projection is what makes a check here a real check of their contract.
            """
            self.admin(me)
            with closing(self.connection()) as db:
                rows = db.execute("SELECT * FROM delivery_assignments ORDER BY id DESC LIMIT 200").fetchall()
                trips = [self.client_trip(db, row) for row in rows]
                totals = {}
                for trip in trips:
                    for stop in trip['stops']:
                        for item in stop['items']:
                            key = (item['product_name'], item['uom'])
                            bucket = totals.setdefault(key, {
                                'product_name': item['product_name'], 'uom': item['uom'],
                                'planned_quantity': Decimal(0), 'delivered_quantity': Decimal(0)})
                            bucket['planned_quantity'] += Decimal(str(item['planned_quantity']))
                            bucket['delivered_quantity'] += Decimal(str(item['delivered_quantity']))
                return {
                    'trips': trips,
                    'product_totals': [{**item, 'planned_quantity': str(item['planned_quantity']),
                                        'delivered_quantity': str(item['delivered_quantity'])}
                                       for item in totals.values()],
                    'shortages': [
                        {'trip': trip['trip'], 'customer': stop['customer'], 'reason': stop['reason'],
                         'items': [item for item in stop['items']
                                   if Decimal(str(item['delivered_quantity'])) < Decimal(str(item['planned_quantity']))]}
                        for trip in trips for stop in trip['stops']
                        if stop['status'] in ('partial', 'failed')],
                }

        @app.get("/api/v1/deliveries/extras")
        def extras(me=Depends(current_user)):
            """Extra batter shops asked for, awaiting the next trip or reassignment."""
            with closing(self.connection()) as db:
                rows = db.execute("""SELECT id,customer,supermarket_id,product_name,uom,quantity,trip,status,created_at
                    FROM extra_requests WHERE status='pending' ORDER BY id DESC LIMIT 200""").fetchall()
                grouped = {}
                for row in rows:
                    key = (row["supermarket_id"], row["customer"], row["product_name"], row["uom"])
                    total = grouped.setdefault(key, {'ids': [], 'customer': row["customer"],
                                                     'supermarket_id': row["supermarket_id"],
                                                     'product_name': row["product_name"], 'uom': row["uom"],
                                                     'quantity': Decimal(0), 'requests': 0})
                    total['quantity'] += Decimal(str(row["quantity"]))
                    total['requests'] += 1
                    total['ids'].append(row["id"])
                return {"extras": [{**item, 'quantity': str(item['quantity'])} for item in grouped.values()]}

        @app.post("/api/v1/deliveries/extras/resolve")
        def resolve_extras(body: ResolveExtras, me=Depends(current_user)):
            """Close extra requests once they are folded into a trip or moved to another shop."""
            self.admin(me)
            if not body.ids:
                raise HTTPException(422, "Choose at least one extra request to resolve")
            now = self.now()
            resolved = 0
            with closing(self.connection()) as db:
                db.execute("BEGIN IMMEDIATE")
                for request_id in body.ids:
                    cursor = db.execute("""UPDATE extra_requests SET status='resolved',resolution=?,updated_at=?
                        WHERE id=? AND status='pending'""", (body.note.strip(), now, request_id))
                    resolved += cursor.rowcount
                db.commit()
            if not resolved:
                raise HTTPException(409, "Those extra requests were already resolved")
            return {"resolved": resolved}

        @app.post("/api/v1/erpnext/sync")
        def sync(me=Depends(current_user)):
            self.admin(me)
            site, _, _ = configuration()
            # A phone request must not wait for a slow ERP server or a whole batch.
            with closing(self.connection()) as db:
                db.execute("UPDATE delivery_assignments SET next_attempt=NULL WHERE site=?", (site,))
                db.commit()
            return {"queued": True}

        if external_client is not None:
            self.register_client_reads(app, external_client)

    def client_trip(self, db, row):
        """Client-facing view of one trip.

        Deliberately a projection rather than the driver-facing snapshot: the
        client has no use for ERPNext sync bookkeeping, and the site column can
        hold their ERP URL.
        """
        snapshot = self.snapshot(db, row)
        return {
            'id': snapshot['id'],
            'trip': snapshot['trip'],
            'status': snapshot['status'],
            'driver_id': snapshot['driver_id'],
            'driver_name': snapshot['driver_name'],
            'vehicle': snapshot['vehicle'],
            'created_at': snapshot['created_at'],
            'updated_at': snapshot['updated_at'],
            'ride': snapshot['ride'],
            'location': snapshot['location'],
            'surplus': snapshot['surplus'],
            'stops': [{
                'id': stop['id'],
                'supermarket_id': stop.get('supermarket_id'),
                'customer': stop['customer'],
                'address_text': stop['address_text'],
                'latitude': stop['latitude'],
                'longitude': stop['longitude'],
                'status': stop['status'],
                'reason': stop['reason'],
                'confirmed_at': stop['confirmed_at'],
                'items': [{
                    'product_name': item['product_name'],
                    'uom': item['uom'],
                    'planned_quantity': item['planned_quantity'],
                    'delivered_quantity': item['delivered_quantity'],
                } for item in stop['items']],
            } for stop in snapshot['stops']],
            'product_totals': snapshot['product_totals'],
        }

    def register_client_reads(self, app, external_client):
        """Read-only endpoints for the client's own reporting system."""
        @app.get("/api/v1/client/deliveries")
        def client_deliveries(since: str = "", me=Depends(external_client)):
            """Polling endpoint. `since` is an ISO-8601 timestamp; omit it for a full read.

            The cursor tracks delivery confirmations and assignment edits, not live GPS
            samples, so a trip is reported once its outcomes change.
            """
            query = "SELECT * FROM delivery_assignments WHERE 1=1"
            params = []
            if since:
                try:
                    parsed = datetime.fromisoformat(since.strip().replace('Z', '+00:00'))
                except ValueError as error:
                    raise HTTPException(422, "since must be an ISO-8601 timestamp") from error
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                query += " AND updated_at>?"
                params.append(parsed.astimezone(timezone.utc).isoformat())
            query += " ORDER BY id DESC"
            with closing(self.connection()) as db:
                rows = db.execute(query, params).fetchall()
                return {"trips": [self.client_trip(db, row) for row in rows], "count": len(rows)}

        @app.get("/api/v1/client/deliveries/{assignment_id}")
        def client_delivery(assignment_id: int, me=Depends(external_client)):
            """Full detail for one trip: outcomes, quantities, reasons and GPS evidence."""
            with closing(self.connection()) as db:
                row = db.execute("SELECT * FROM delivery_assignments WHERE id=?", (assignment_id,)).fetchone()
                if row is None:
                    raise HTTPException(404, "delivery assignment not found")
                return self.client_trip(db, row)
