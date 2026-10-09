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
        CREATE TABLE IF NOT EXISTS delivery_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, site TEXT NOT NULL, trip TEXT NOT NULL,
            driver_id INTEGER NOT NULL REFERENCES users(id), erp_driver TEXT NOT NULL,
            ride_id INTEGER UNIQUE REFERENCES rides(id), vehicle TEXT, departure_time TEXT,
            stops TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1, synced_revision INTEGER NOT NULL DEFAULT 0,
            last_sync TEXT, last_error TEXT, attempts INTEGER NOT NULL DEFAULT 0, next_attempt TEXT,
            created_at TEXT NOT NULL, UNIQUE(site, trip));
        CREATE INDEX IF NOT EXISTS idx_deliveries_driver ON delivery_assignments(driver_id, id DESC);
        CREATE TABLE IF NOT EXISTS delivery_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, assignment_id INTEGER NOT NULL REFERENCES delivery_assignments(id),
            actor_id INTEGER NOT NULL REFERENCES users(id), stop_id TEXT NOT NULL,
            status TEXT NOT NULL, reason TEXT NOT NULL, location TEXT, created_at TEXT NOT NULL);
    """)
    db.execute("INSERT OR IGNORE INTO erp_settings VALUES ('instance_id', ?)", (secrets.token_hex(12),))
    if 'items' not in {row['name'] for row in db.execute('PRAGMA table_info(delivery_events)')}:
        db.execute("ALTER TABLE delivery_events ADD COLUMN items TEXT NOT NULL DEFAULT '[]'")


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


class ProductDelivered(BaseModel):
    id: str = Field(min_length=1, max_length=140)
    delivered_quantity: Decimal = Field(ge=0, max_digits=12, decimal_places=3)


class StopUpdate(BaseModel):
    status: str = Field(pattern="^(arrived|delivered|partial|failed)$")
    reason: str = Field(default="", max_length=500)
    items: list[ProductDelivered] = Field(default_factory=list, max_length=100)

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

    def register(self, app, current_user):
        @app.get("/api/v1/deliveries")
        def deliveries(me=Depends(current_user)):
            with closing(self.connection()) as db:
                rows = db.execute("SELECT * FROM delivery_assignments WHERE (? OR driver_id=?) ORDER BY id DESC LIMIT 100",
                                  (int(me["role"] == "admin"), me["id"])).fetchall()
                return {"assignments": [self.snapshot(db, row) for row in rows]}

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
                db.execute('UPDATE delivery_assignments SET stops=?,revision=revision+1,next_attempt=NULL WHERE id=?',
                           (json.dumps(stops), assignment_id))
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
                    db.execute("UPDATE delivery_assignments SET ride_id=?,revision=revision+1 WHERE id=?", (body.ride_id, assignment_id))
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
                if stop["status"] == body.status and stop["reason"] == body.reason and same_items:
                    return self.snapshot(db, row)
                if stop["status"] in ("delivered", "partial", "failed"):
                    raise HTTPException(409, "Confirmed delivery outcomes cannot be overwritten")
                now = self.now()
                location = self.snapshot(db, row)["location"]
                stop.update(status=body.status, reason=body.reason, confirmed_at=now)
                for item in products:
                    item['delivered_quantity'] = submitted.get(item['id'], '0')
                db.execute("UPDATE delivery_assignments SET stops=?,revision=revision+1,next_attempt=NULL WHERE id=?",
                           (json.dumps(stops), assignment_id))
                db.execute("""INSERT INTO delivery_events(assignment_id,actor_id,stop_id,status,reason,location,created_at,items)
                    VALUES (?,?,?,?,?,?,?,?)""", (assignment_id, me["id"], stop_id, body.status, body.reason,
                                              json.dumps(location), now, json.dumps(products)))
                db.commit()
                return self.snapshot(db, db.execute("SELECT * FROM delivery_assignments WHERE id=?", (assignment_id,)).fetchone())

        @app.post("/api/v1/erpnext/sync")
        def sync(me=Depends(current_user)):
            self.admin(me)
            site, _, _ = configuration()
            # A phone request must not wait for a slow ERP server or a whole batch.
            with closing(self.connection()) as db:
                db.execute("UPDATE delivery_assignments SET next_attempt=NULL WHERE site=?", (site,))
                db.commit()
            return {"queued": True}
