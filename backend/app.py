from __future__ import annotations

import os
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parent
DATABASE_PATH = Path(os.getenv("ROUTEOS_DATABASE", ROOT / "routeos.db"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connection() -> sqlite3.Connection:
    db = sqlite3.connect(DATABASE_PATH)
    db.row_factory = sqlite3.Row
    return db


def initialize_database() -> None:
    with closing(connection()) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              kind TEXT NOT NULL,
              payload TEXT NOT NULL,
              created_at TEXT NOT NULL
            )
            """
        )
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              role TEXT NOT NULL DEFAULT 'driver',
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS recorded_tracks (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              recorder_id INTEGER NOT NULL,
              organic_maps_track_id TEXT,
              points TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY (recorder_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS routes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              recorder_id INTEGER NOT NULL,
              track_id INTEGER NOT NULL,
              origin TEXT,
              destination TEXT,
              created_at TEXT NOT NULL,
              FOREIGN KEY (recorder_id) REFERENCES users(id),
              FOREIGN KEY (track_id) REFERENCES recorded_tracks(id)
            );
            CREATE TABLE IF NOT EXISTS rides (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              driver_id INTEGER NOT NULL,
              route_id INTEGER NOT NULL,
              vehicle_type TEXT NOT NULL,
              vehicle_number TEXT NOT NULL,
              status TEXT NOT NULL,
              started_at TEXT NOT NULL,
              ended_at TEXT,
              FOREIGN KEY (driver_id) REFERENCES users(id),
              FOREIGN KEY (route_id) REFERENCES routes(id)
            );
            CREATE TABLE IF NOT EXISTS live_locations (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              ride_id INTEGER NOT NULL,
              driver_id INTEGER NOT NULL,
              latitude REAL NOT NULL,
              longitude REAL NOT NULL,
              speed_mps REAL,
              bearing REAL,
              recorded_at TEXT NOT NULL,
              FOREIGN KEY (ride_id) REFERENCES rides(id),
              FOREIGN KEY (driver_id) REFERENCES users(id)
            );
            """
        )
        user_columns = {row["name"] for row in db.execute("PRAGMA table_info(users)").fetchall()}
        if "role" not in user_columns:
            db.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'driver'")
        route_columns = {row["name"] for row in db.execute("PRAGMA table_info(routes)").fetchall()}
        if "hub_latitude" not in route_columns:
            db.execute("ALTER TABLE routes ADD COLUMN hub_latitude REAL")
        if "hub_longitude" not in route_columns:
            db.execute("ALTER TABLE routes ADD COLUMN hub_longitude REAL")
        for name, role in (
            ("Disha Patani", "driver"),
            ("Sukumara Kurup", "driver"),
            ("Thomachan Valiparambil", "admin"),
        ):
            existing = db.execute("SELECT id FROM users WHERE lower(name) = lower(?)", (name,)).fetchone()
            if existing is None:
                db.execute(
                    "INSERT INTO users(name, role, created_at) VALUES (?, ?, ?)",
                    (name, role, utc_now()),
                )
            else:
                db.execute("UPDATE users SET name = ?, role = ? WHERE id = ?", (name, role, existing["id"]))
        db.commit()


class EventIn(BaseModel):
    kind: str = Field(min_length=1, max_length=80)
    payload: dict = Field(default_factory=dict)


class UserIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class LoginIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class TrackPoint(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timestamp: str | None = None
    altitude_meters: float | None = None


class TrackIn(BaseModel):
    recorder_id: int
    organic_maps_track_id: str | None = None
    points: list[TrackPoint] = Field(min_length=2, max_length=100_000)


class RouteIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    recorder_id: int
    track_id: int
    origin: str | None = Field(default=None, max_length=120)
    destination: str | None = Field(default=None, max_length=120)
    hub_latitude: float | None = Field(default=None, ge=-90, le=90)
    hub_longitude: float | None = Field(default=None, ge=-180, le=180)


class RideIn(BaseModel):
    driver_id: int
    route_id: int
    vehicle_type: str = Field(min_length=1, max_length=40)
    vehicle_number: str = Field(min_length=1, max_length=40)


class LiveLocationIn(BaseModel):
    driver_id: int
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    speed_mps: float | None = Field(default=None, ge=0)
    bearing: float | None = Field(default=None, ge=0, le=360)


app = FastAPI(title="RouteOS Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    initialize_database()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "routeos-backend", "organic_maps": True}


@app.post("/api/v1/users", status_code=201)
def create_user(user: UserIn) -> dict:
    created_at = utc_now()
    with closing(connection()) as db:
        cursor = db.execute("INSERT INTO users(name, role, created_at) VALUES (?, 'driver', ?)", (user.name, created_at))
        db.commit()
    return {"id": cursor.lastrowid, "name": user.name, "role": "driver", "created_at": created_at}


@app.post("/api/v1/auth/login")
def login(login: LoginIn) -> dict:
    normalized_name = login.name.strip()
    with closing(connection()) as db:
        existing = db.execute(
            "SELECT id, name, role, created_at FROM users WHERE lower(name) = lower(?) ORDER BY id LIMIT 1",
            (normalized_name,),
        ).fetchone()
        if existing is not None:
            return dict(existing)
    raise HTTPException(status_code=401, detail="unknown RouteOS quick-login account")


@app.post("/api/v1/tracks", status_code=201)
def create_track(track: TrackIn) -> dict:
    created_at = utc_now()
    points = [point.model_dump() for point in track.points]
    with closing(connection()) as db:
        if db.execute("SELECT 1 FROM users WHERE id = ?", (track.recorder_id,)).fetchone() is None:
            raise HTTPException(status_code=404, detail="recorder not found")
        cursor = db.execute(
            "INSERT INTO recorded_tracks(recorder_id, organic_maps_track_id, points, created_at) VALUES (?, ?, ?, ?)",
            (track.recorder_id, track.organic_maps_track_id, json.dumps(points), created_at),
        )
        db.commit()
    return {
        "id": cursor.lastrowid,
        "recorder_id": track.recorder_id,
        "organic_maps_track_id": track.organic_maps_track_id,
        "point_count": len(points),
        "created_at": created_at,
    }


@app.post("/api/v1/routes", status_code=201)
def create_route(route: RouteIn) -> dict:
    created_at = utc_now()
    with closing(connection()) as db:
        if db.execute("SELECT 1 FROM users WHERE id = ?", (route.recorder_id,)).fetchone() is None:
            raise HTTPException(status_code=404, detail="recorder not found")
        track = db.execute(
            "SELECT recorder_id FROM recorded_tracks WHERE id = ?", (route.track_id,)
        ).fetchone()
        if track is None:
            raise HTTPException(status_code=404, detail="recorded track not found")
        if track["recorder_id"] != route.recorder_id:
            raise HTTPException(status_code=409, detail="track belongs to another driver")
        cursor = db.execute(
            "INSERT INTO routes(name, recorder_id, track_id, origin, destination, created_at, hub_latitude, hub_longitude) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (route.name, route.recorder_id, route.track_id, route.origin, route.destination, created_at,
             route.hub_latitude, route.hub_longitude),
        )
        db.commit()
    return {"id": cursor.lastrowid, **route.model_dump(), "created_at": created_at}


@app.get("/api/v1/routes")
def list_routes() -> list[dict]:
    with closing(connection()) as db:
        rows = db.execute(
            """
            SELECT r.id, r.name, r.recorder_id, r.track_id, r.origin, r.destination, r.created_at,
                   r.hub_latitude, r.hub_longitude, u.name AS recorder_name
            FROM routes r JOIN users u ON u.id = r.recorder_id
            ORDER BY r.id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


@app.get("/api/v1/routes/{route_id}")
def get_route(route_id: int) -> dict:
    with closing(connection()) as db:
        row = db.execute(
            """
            SELECT r.id, r.name, r.recorder_id, r.track_id, r.origin, r.destination, r.created_at,
                   r.hub_latitude, r.hub_longitude, u.name AS recorder_name,
                   t.organic_maps_track_id, t.points
            FROM routes r JOIN recorded_tracks t ON t.id = r.track_id
            JOIN users u ON u.id = r.recorder_id
            WHERE r.id = ?
            """,
            (route_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="route not found")
    route = dict(row)
    route["points"] = json.loads(route.pop("points"))
    return route


@app.post("/api/v1/rides", status_code=201)
def start_ride(ride: RideIn) -> dict:
    started_at = utc_now()
    with closing(connection()) as db:
        driver = db.execute("SELECT role FROM users WHERE id = ?", (ride.driver_id,)).fetchone()
        if driver is None or driver["role"] != "driver":
            raise HTTPException(status_code=403, detail="a driver account is required")
        if db.execute("SELECT 1 FROM routes WHERE id = ?", (ride.route_id,)).fetchone() is None:
            raise HTTPException(status_code=404, detail="route not found")
        active = db.execute(
            "SELECT id FROM rides WHERE driver_id = ? AND status = 'active'", (ride.driver_id,)
        ).fetchone()
        if active is not None:
            raise HTTPException(status_code=409, detail="driver already has an active ride")
        cursor = db.execute(
            """
            INSERT INTO rides(driver_id, route_id, vehicle_type, vehicle_number, status, started_at)
            VALUES (?, ?, ?, ?, 'active', ?)
            """,
            (ride.driver_id, ride.route_id, ride.vehicle_type, ride.vehicle_number, started_at),
        )
        db.commit()
    return {"id": cursor.lastrowid, **ride.model_dump(), "status": "active", "started_at": started_at}


@app.post("/api/v1/rides/{ride_id}/locations", status_code=201)
def update_live_location(ride_id: int, location: LiveLocationIn) -> dict:
    recorded_at = utc_now()
    with closing(connection()) as db:
        ride = db.execute("SELECT driver_id, status FROM rides WHERE id = ?", (ride_id,)).fetchone()
        if ride is None:
            raise HTTPException(status_code=404, detail="ride not found")
        if ride["status"] != "active":
            raise HTTPException(status_code=409, detail="ride has ended")
        if ride["driver_id"] != location.driver_id:
            raise HTTPException(status_code=403, detail="location belongs to another driver")
        cursor = db.execute(
            """
            INSERT INTO live_locations(ride_id, driver_id, latitude, longitude, speed_mps, bearing, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (ride_id, location.driver_id, location.latitude, location.longitude,
             location.speed_mps, location.bearing, recorded_at),
        )
        db.commit()
    return {"id": cursor.lastrowid, "ride_id": ride_id, **location.model_dump(), "recorded_at": recorded_at}


@app.post("/api/v1/rides/{ride_id}/end")
def end_ride(ride_id: int) -> dict:
    ended_at = utc_now()
    with closing(connection()) as db:
        ride = db.execute("SELECT status FROM rides WHERE id = ?", (ride_id,)).fetchone()
        if ride is None:
            raise HTTPException(status_code=404, detail="ride not found")
        db.execute("UPDATE rides SET status = 'ended', ended_at = ? WHERE id = ?", (ended_at, ride_id))
        db.commit()
    return {"id": ride_id, "status": "ended", "ended_at": ended_at}


@app.get("/api/v1/rides/active")
def active_rides() -> list[dict]:
    with closing(connection()) as db:
        rows = db.execute(
            """
            SELECT rides.id, rides.driver_id, rides.route_id, rides.vehicle_type, rides.vehicle_number,
                   rides.status, rides.started_at, users.name AS driver_name, routes.name AS route_name,
                   locations.latitude, locations.longitude, locations.speed_mps, locations.bearing,
                   locations.recorded_at AS location_recorded_at
            FROM rides
            JOIN users ON users.id = rides.driver_id
            JOIN routes ON routes.id = rides.route_id
            LEFT JOIN live_locations locations ON locations.id = (
              SELECT id FROM live_locations WHERE ride_id = rides.id ORDER BY id DESC LIMIT 1
            )
            WHERE rides.status = 'active'
            ORDER BY rides.id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


@app.get("/api/v1/drivers/{driver_id}/active-ride")
def driver_active_ride(driver_id: int) -> dict:
    with closing(connection()) as db:
        row = db.execute(
            """
            SELECT rides.id, rides.driver_id, rides.route_id, rides.vehicle_type, rides.vehicle_number,
                   rides.status, rides.started_at, routes.name AS route_name, tracks.points
            FROM rides
            JOIN routes ON routes.id = rides.route_id
            JOIN recorded_tracks tracks ON tracks.id = routes.track_id
            WHERE rides.driver_id = ? AND rides.status = 'active'
            ORDER BY rides.id DESC LIMIT 1
            """,
            (driver_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="no active ride")
    ride = dict(row)
    points = json.loads(ride.pop("points"))
    if points:
        ride["destination_latitude"] = points[-1]["latitude"]
        ride["destination_longitude"] = points[-1]["longitude"]
    return ride


@app.get("/api/v1/manifest")
def manifest() -> dict:
    return {
        "product": "RouteOS",
        "map_engine": "Organic Maps",
        "offline_first": True,
        "features": [
            "quick-login",
            "shared-routes",
            "route-recording",
            "route-drawing",
            "vehicle-selection",
            "organic-maps-navigation",
            "live-tracking",
            "admin-console",
        ],
        "endpoints": {
            "health": "/health",
            "login": "/api/v1/auth/login",
            "routes": "/api/v1/routes",
            "rides": "/api/v1/rides",
            "active_rides": "/api/v1/rides/active",
            "events": "/api/v1/events",
        },
    }


@app.post("/api/v1/events", status_code=201)
def create_event(event: EventIn) -> dict:
    created_at = utc_now()
    with closing(connection()) as db:
        cursor = db.execute(
            "INSERT INTO events(kind, payload, created_at) VALUES (?, ?, ?)",
            (event.kind, json.dumps(event.payload), created_at),
        )
        db.commit()
        return {"id": cursor.lastrowid, "kind": event.kind, "payload": event.payload, "created_at": created_at}


@app.get("/api/v1/events")
def list_events(limit: int = 50) -> list[dict]:
    if not 1 <= limit <= 200:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 200")
    with closing(connection()) as db:
        rows = db.execute(
            "SELECT id, kind, payload, created_at FROM events ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [
        {**dict(row), "payload": json.loads(row["payload"])}
        for row in rows
    ]
