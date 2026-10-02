from __future__ import annotations

import os
import json
import secrets
import sqlite3
import math
import hashlib
import hmac
from contextlib import asynccontextmanager, closing
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator, model_validator


ROOT = Path(__file__).resolve().parent
DATABASE_PATH = Path(os.getenv("ROUTEOS_DATABASE", ROOT / "routeos.db"))


def development_auth() -> bool:
    return os.getenv("ROUTEOS_DEVELOPMENT_AUTH", "0") == "1"


def password_hash(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 600_000).hex()
    return f"{salt}:{digest}"


def issue_session(db, user_id: int) -> str:
    token = new_token()
    db.execute("INSERT INTO sessions(token_hash,user_id,expires_at) VALUES (?,?,?)",
               (hashlib.sha256(token.encode()).hexdigest(), user_id,
                (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()))
    return token


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_timestamp(value: object) -> datetime | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        magnitude = abs(value)
        if magnitude >= 1e14:
            seconds = float(value) / 1e6
        elif magnitude >= 1e11:
            seconds = float(value) / 1000.0
        else:
            seconds = float(value)
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text[-1] in "Zz":
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    return None


def normalize_timestamp(value: object) -> str | None:
    parsed = parse_timestamp(value)
    if parsed is None:
        return None
    return parsed.astimezone(timezone.utc).isoformat()


def new_token() -> str:
    return secrets.token_urlsafe(32)


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 6371000 * 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1 - a)))


ARRIVAL_RADIUS_M = 150.0


def connection() -> sqlite3.Connection:
    db = sqlite3.connect(DATABASE_PATH, timeout=10.0)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA journal_mode = WAL")
    db.execute("PRAGMA busy_timeout = 10000")
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
              route_type TEXT NOT NULL DEFAULT 'recorded',
              created_at TEXT NOT NULL,
              FOREIGN KEY (recorder_id) REFERENCES users(id),
              FOREIGN KEY (track_id) REFERENCES recorded_tracks(id)
            );
            CREATE TABLE IF NOT EXISTS route_favorites (
              user_id INTEGER NOT NULL,
              route_id INTEGER NOT NULL,
              created_at TEXT NOT NULL,
              PRIMARY KEY (user_id, route_id),
              FOREIGN KEY (user_id) REFERENCES users(id),
              FOREIGN KEY (route_id) REFERENCES routes(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS route_recents (
              user_id INTEGER NOT NULL,
              route_id INTEGER NOT NULL,
              last_used_at TEXT NOT NULL,
              PRIMARY KEY (user_id, route_id),
              FOREIGN KEY (user_id) REFERENCES users(id),
              FOREIGN KEY (route_id) REFERENCES routes(id) ON DELETE CASCADE
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
        if "auth_token" not in user_columns:
            db.execute("ALTER TABLE users ADD COLUMN auth_token TEXT")
        if "password_hash" not in user_columns:
            db.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
        db.execute("""CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
            expires_at TEXT NOT NULL)""")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_users_auth_token ON users(auth_token)")
        db.execute(
            """
            UPDATE rides SET status = 'ended', ended_at = started_at
             WHERE status = 'active' AND id NOT IN (
                 SELECT MAX(id) FROM rides WHERE status = 'active' GROUP BY driver_id
             )
            """
        )
        db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_rides_active_driver ON rides(driver_id) WHERE status = 'active'"
        )
        route_columns = {row["name"] for row in db.execute("PRAGMA table_info(routes)").fetchall()}
        for column, kind in (("waypoints", "TEXT"), ("distance_meters", "REAL"), ("duration_seconds", "INTEGER"), ("point_count", "INTEGER")):
            if column not in route_columns:
                db.execute(f"ALTER TABLE routes ADD COLUMN {column} {kind}")
        if "hub_latitude" not in route_columns:
            db.execute("ALTER TABLE routes ADD COLUMN hub_latitude REAL")
        if "hub_longitude" not in route_columns:
            db.execute("ALTER TABLE routes ADD COLUMN hub_longitude REAL")
        if "route_type" not in route_columns:
            db.execute("ALTER TABLE routes ADD COLUMN route_type TEXT NOT NULL DEFAULT 'recorded'")
        db.execute(
            """
            UPDATE routes
               SET route_type = created_at, created_at = route_type
             WHERE created_at IN ('recorded', 'drawn')
               AND route_type LIKE '____-__-__%'
            """
        )
        db.execute(
            "DELETE FROM live_locations WHERE ride_id NOT IN (SELECT id FROM rides)"
            " OR driver_id NOT IN (SELECT id FROM users)"
        )
        db.execute(
            "DELETE FROM rides WHERE driver_id NOT IN (SELECT id FROM users)"
            " OR route_id NOT IN (SELECT id FROM routes)"
        )
        db.execute(
            "DELETE FROM route_favorites WHERE route_id NOT IN (SELECT id FROM routes)"
            " OR user_id NOT IN (SELECT id FROM users)"
        )
        db.execute(
            "DELETE FROM route_recents WHERE route_id NOT IN (SELECT id FROM routes)"
            " OR user_id NOT IN (SELECT id FROM users)"
        )
        for row in db.execute("SELECT id FROM users WHERE auth_token IS NULL").fetchall():
            db.execute("UPDATE users SET auth_token = ? WHERE id = ?", (new_token(), row["id"]))
        for name, role in (
            ("Disha Patani", "driver"),
            ("Sukumara Kurup", "driver"),
            ("Thomachan Valiparambil", "admin"),
        ):
            existing = db.execute("SELECT id FROM users WHERE lower(name) = lower(?)", (name,)).fetchone()
            if existing is None:
                db.execute(
                    "INSERT INTO users(name, role, auth_token, created_at) VALUES (?, ?, ?, ?)",
                    (name, role, new_token(), utc_now()),
                )
        for row in db.execute("""SELECT r.id,t.points FROM routes r JOIN recorded_tracks t ON t.id=r.track_id
            WHERE r.point_count IS NULL OR r.distance_meters IS NULL""").fetchall():
            try:
                points = json.loads(row["points"])
                distance, duration = route_stats(points)
            except (ValueError, TypeError, KeyError):
                points, distance, duration = [], 0, 0
            db.execute("""UPDATE routes SET point_count=?,distance_meters=COALESCE(distance_meters,?),
                duration_seconds=COALESCE(duration_seconds,?) WHERE id=?""", (len(points),distance,duration,row["id"]))
        db.commit()


class EventIn(BaseModel):
    kind: str = Field(min_length=1, max_length=80)
    payload: dict = Field(default_factory=dict)


class UserIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    password: str | None = Field(default=None, min_length=12, max_length=256)


class LoginIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    password: str | None = Field(default=None, max_length=256)


class TrackPoint(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timestamp: str | int | None = None
    altitude_meters: float | None = None

    @field_validator("timestamp", mode="before")
    @classmethod
    def canonical_timestamp(cls, value: object) -> str | None:
        return normalize_timestamp(value)


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
    route_type: str = Field(default="recorded", pattern="^(recorded|drawn)$")
    hub_latitude: float | None = Field(default=None, ge=-90, le=90)
    hub_longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def hub_coordinates_pair(self) -> RouteIn:
        if (self.hub_latitude is None) != (self.hub_longitude is None):
            raise ValueError("hub_latitude and hub_longitude must be set together")
        return self


class RideIn(BaseModel):
    driver_id: int
    route_id: int
    vehicle_type: str = Field(min_length=1, max_length=40)
    vehicle_number: str = Field(min_length=1, max_length=40)


class PlannedPoint(TrackPoint):
    sequence: int = Field(ge=0)
    type: str = Field(pattern="^(start|via|destination)$")
    label: str | None = Field(default=None, max_length=200)
    address: str | None = Field(default=None, max_length=500)


class PlannedRouteIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    points: list[PlannedPoint] = Field(min_length=2, max_length=102)
    distance_meters: float = Field(gt=0)
    duration_seconds: int = Field(gt=0)

    @model_validator(mode="after")
    def ordered_points(self):
        if not self.name.strip():
            raise ValueError("route name must not be blank")
        for i, point in enumerate(self.points):
            expected = "start" if i == 0 else "destination" if i == len(self.points)-1 else "via"
            if point.sequence != i or point.type != expected:
                raise ValueError("points must be ordered start, via, destination")
        return self


class LiveLocationIn(BaseModel):
    driver_id: int
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    speed_mps: float | None = Field(default=None, ge=0)
    bearing: float | None = Field(default=None, ge=0, le=360)


class RouteActorIn(BaseModel):
    driver_id: int


class RouteRenameIn(RouteActorIn):
    name: str = Field(min_length=1, max_length=160)


class RouteShareIn(RouteActorIn):
    recipient_id: int | None = None


class EndRideIn(BaseModel):
    driver_id: int


class ArriveIn(BaseModel):
    driver_id: int


def current_user(x_routeos_token: str | None = Header(default=None), authorization: str | None = Header(default=None)) -> dict:
    bearer = authorization[7:] if authorization and authorization.startswith("Bearer ") else None
    if not bearer and not (development_auth() and x_routeos_token):
        raise HTTPException(status_code=401, detail="missing API token")
    with closing(connection()) as db:
        user = db.execute("""SELECT u.id,u.name,u.role FROM sessions s JOIN users u ON u.id=s.user_id
            WHERE s.token_hash=? AND s.expires_at>?""",
            (hashlib.sha256((bearer or "").encode()).hexdigest(), utc_now())).fetchone()
        if user is None and development_auth():
            user = db.execute("SELECT id,name,role FROM users WHERE auth_token=?", (bearer or x_routeos_token,)).fetchone()
    if user is None:
        raise HTTPException(status_code=401, detail="invalid API token")
    return dict(user)


def caller_owns(me: dict, driver_id: int) -> None:
    if driver_id != me["id"]:
        raise HTTPException(status_code=403, detail="driver mismatch")


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="RouteOS Backend", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[v.strip() for v in os.getenv("ROUTEOS_CORS_ORIGINS", "").split(",") if v.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "routeos-backend", "organic_maps": True}


@app.post("/api/v1/users", status_code=201)
def create_user(user: UserIn) -> dict:
    name = user.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="name must not be blank")
    if not user.password and not development_auth():
        raise HTTPException(status_code=422, detail="password of at least 12 characters required")
    created_at = utc_now()
    token = new_token()
    with closing(connection()) as db:
        if db.execute("SELECT 1 FROM users WHERE lower(name) = lower(?)", (name,)).fetchone() is not None:
            raise HTTPException(status_code=409, detail="account name already taken")
        cursor = db.execute(
            "INSERT INTO users(name, role, auth_token, password_hash, created_at) VALUES (?, 'driver', ?, ?, ?)",
            (name, token, password_hash(user.password) if user.password else None, created_at),
        )
        if user.password:
            token = issue_session(db, cursor.lastrowid)
        db.commit()
    return {"id": cursor.lastrowid, "name": name, "role": "driver", "auth_token": token, "created_at": created_at}


@app.post("/api/v1/auth/login")
def login(login: LoginIn) -> dict:
    normalized_name = login.name.strip()
    with closing(connection()) as db:
        existing = db.execute(
            "SELECT id, name, role, auth_token, password_hash, created_at FROM users WHERE lower(name) = lower(?) ORDER BY id LIMIT 1",
            (normalized_name,),
        ).fetchone()
        if existing is not None:
            user = dict(existing)
            encoded = user.pop("password_hash")
            if encoded:
                if not login.password or not hmac.compare_digest(encoded, password_hash(login.password, encoded.split(":")[0])):
                    raise HTTPException(status_code=401, detail="invalid credentials")
                user["auth_token"] = issue_session(db, user["id"])
                db.commit()
                return user
            if not development_auth():
                raise HTTPException(status_code=401, detail="invalid credentials")
            if user["auth_token"] is None:
                user["auth_token"] = new_token()
                db.execute("UPDATE users SET auth_token = ? WHERE id = ?", (user["auth_token"], user["id"]))
                db.commit()
            return user
    raise HTTPException(status_code=401, detail="unknown RouteOS quick-login account")


@app.post("/api/v1/auth/logout")
def logout(me: dict = Depends(current_user), authorization: str | None = Header(default=None)) -> dict:
    if authorization and authorization.startswith("Bearer "):
        with closing(connection()) as db:
            db.execute("DELETE FROM sessions WHERE token_hash=?", (hashlib.sha256(authorization[7:].encode()).hexdigest(),))
            db.commit()
    return {"logged_out": True}


@app.post("/api/v1/tracks", status_code=201)
def create_track(track: TrackIn, me: dict = Depends(current_user)) -> dict:
    caller_owns(me, track.recorder_id)
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
def create_route(route: RouteIn, me: dict = Depends(current_user)) -> dict:
    caller_owns(me, route.recorder_id)
    created_at = utc_now()
    with closing(connection()) as db:
        if db.execute("SELECT 1 FROM users WHERE id = ?", (route.recorder_id,)).fetchone() is None:
            raise HTTPException(status_code=404, detail="recorder not found")
        track = db.execute(
            "SELECT recorder_id, points FROM recorded_tracks WHERE id = ?", (route.track_id,)
        ).fetchone()
        if track is None:
            raise HTTPException(status_code=404, detail="recorded track not found")
        if track["recorder_id"] != route.recorder_id:
            raise HTTPException(status_code=409, detail="track belongs to another driver")
        cursor = db.execute(
            "INSERT INTO routes(name, recorder_id, track_id, origin, destination, route_type, created_at, hub_latitude, hub_longitude) "
            "VALUES(:name, :recorder_id, :track_id, :origin, :destination, :route_type, :created_at, :hub_latitude, :hub_longitude)",
            {
                "name": route.name,
                "recorder_id": route.recorder_id,
                "track_id": route.track_id,
                "origin": route.origin,
                "destination": route.destination,
                "route_type": route.route_type,
                "created_at": created_at,
                "hub_latitude": route.hub_latitude,
                "hub_longitude": route.hub_longitude,
            },
        )
        points = json.loads(track["points"])
        distance, duration = route_stats(points)
        db.execute("UPDATE routes SET point_count=?,distance_meters=?,duration_seconds=? WHERE id=?",
                   (len(points),distance,duration,cursor.lastrowid))
        db.commit()
    return {"id": cursor.lastrowid, **route.model_dump(), "created_at": created_at}


def route_stats(points: list[dict]) -> tuple[float, int]:
    distance = 0.0
    for first, second in zip(points, points[1:]):
        lat1, lon1 = math.radians(first["latitude"]), math.radians(first["longitude"])
        lat2, lon2 = math.radians(second["latitude"]), math.radians(second["longitude"])
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        distance += 6371000 * 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1 - a)))
    timestamps = [
        stamp for stamp in (parse_timestamp(point.get("timestamp")) for point in points) if stamp is not None
    ]
    duration = 0
    if len(timestamps) >= 2:
        duration = max(0, int((max(timestamps) - min(timestamps)).total_seconds()))
    if duration == 0 and distance > 0:
        duration = max(60, int(distance / 8.3))
    return distance, duration


@app.get("/api/v1/routes")
def list_routes(driver_id: int | None = None, me: dict = Depends(current_user)) -> list[dict]:
    if driver_id is not None:
        caller_owns(me, driver_id)
    viewer_id = me["id"]
    with closing(connection()) as db:
        rows = db.execute(
            """
            SELECT r.id, r.name, r.recorder_id, r.track_id, r.origin, r.destination, r.route_type, r.created_at,
                   r.hub_latitude, r.hub_longitude, r.distance_meters, r.duration_seconds, r.point_count,
                   u.name AS recorder_name, f.route_id IS NOT NULL AS is_favorite, rec.last_used_at
             FROM routes r JOIN users u ON u.id = r.recorder_id
             LEFT JOIN route_favorites f ON f.route_id=r.id AND f.user_id=?
             LEFT JOIN route_recents rec ON rec.route_id=r.id AND rec.user_id=?
             ORDER BY COALESCE(rec.last_used_at,r.created_at) DESC, r.id DESC
             """
            , (viewer_id, viewer_id)
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["is_favorite"] = bool(item["is_favorite"])
            result.append(item)
    return result


@app.post("/api/v1/planned-routes", status_code=201)
def save_planned_route(route: PlannedRouteIn, me: dict = Depends(current_user)) -> dict:
    stamp = utc_now()
    points = [p.model_dump() for p in route.points]
    with closing(connection()) as db:
        with db:
            track = db.execute("INSERT INTO recorded_tracks(recorder_id, points, created_at) VALUES (?, ?, ?)",
                               (me["id"], json.dumps(points), stamp))
            saved = db.execute(
                "INSERT INTO routes(name, recorder_id, track_id, origin, destination, route_type, created_at, waypoints, distance_meters, duration_seconds) VALUES (?, ?, ?, ?, ?, 'drawn', ?, ?, ?, ?)",
                (route.name.strip(), me["id"], track.lastrowid, points[0].get("label") or "Start", points[-1].get("label") or "Destination", stamp, json.dumps(points), route.distance_meters, route.duration_seconds))
            db.execute("UPDATE routes SET point_count=? WHERE id=?", (len(points), saved.lastrowid))
    return {"id": saved.lastrowid, "name": route.name.strip(), "route_type": "drawn", "created_at": stamp}


@app.get("/api/v1/routes/{route_id}")
def get_route(route_id: int, me: dict = Depends(current_user)) -> dict:
    with closing(connection()) as db:
        row = db.execute(
            """
            SELECT r.id, r.name, r.recorder_id, r.track_id, r.origin, r.destination, r.route_type, r.created_at,
                   r.hub_latitude, r.hub_longitude, u.name AS recorder_name,
                   t.organic_maps_track_id, t.points, r.waypoints, r.distance_meters AS saved_distance, r.duration_seconds AS saved_duration
            FROM routes r LEFT JOIN recorded_tracks t ON t.id = r.track_id
            JOIN users u ON u.id = r.recorder_id
            WHERE r.id = ?
            """,
            (route_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="route not found")
    route = dict(row)
    raw_points = route.pop("points")
    route["points"] = json.loads(raw_points) if raw_points else []
    route["point_count"] = len(route["points"])
    route["distance_meters"], route["duration_seconds"] = route_stats(route["points"])
    definition = route.pop("waypoints")
    if definition:
        route["points"] = json.loads(definition)
        route["distance_meters"] = route.pop("saved_distance")
        route["duration_seconds"] = route.pop("saved_duration")
    return route


def route_actor(db: sqlite3.Connection, route_id: int, driver_id: int) -> tuple[sqlite3.Row, sqlite3.Row]:
    route = db.execute("SELECT * FROM routes WHERE id = ?", (route_id,)).fetchone()
    if route is None:
        raise HTTPException(status_code=404, detail="route not found")
    actor = db.execute("SELECT id, role FROM users WHERE id = ?", (driver_id,)).fetchone()
    if actor is None:
        raise HTTPException(status_code=404, detail="driver not found")
    return route, actor


@app.patch("/api/v1/routes/{route_id}")
def rename_route(route_id: int, rename: RouteRenameIn, me: dict = Depends(current_user)) -> dict:
    caller_owns(me, rename.driver_id)
    with closing(connection()) as db:
        route, actor = route_actor(db, route_id, rename.driver_id)
        if actor["role"] != "admin" and route["recorder_id"] != rename.driver_id:
            raise HTTPException(status_code=403, detail="only the route owner or admin can rename this route")
        db.execute("UPDATE routes SET name = ? WHERE id = ?", (rename.name.strip(), route_id))
        db.commit()
    return {"id": route_id, "name": rename.name.strip()}


@app.delete("/api/v1/routes/{route_id}")
def delete_route(route_id: int, driver_id: int, me: dict = Depends(current_user)) -> dict:
    caller_owns(me, driver_id)
    with closing(connection()) as db:
        route, actor = route_actor(db, route_id, driver_id)
        if actor["role"] != "admin" and route["recorder_id"] != driver_id:
            raise HTTPException(status_code=403, detail="only the route owner or admin can delete this route")
        used = db.execute("SELECT id, status FROM rides WHERE route_id = ? LIMIT 1", (route_id,)).fetchone()
        if used is not None:
            detail = "route is being used by an active ride" if used["status"] == "active" else "route has ride history and cannot be deleted"
            raise HTTPException(status_code=409, detail=detail)
        try:
            db.execute("DELETE FROM routes WHERE id = ?", (route_id,))
            db.execute("DELETE FROM recorded_tracks WHERE id = ? AND NOT EXISTS (SELECT 1 FROM routes WHERE track_id = ?)", (route["track_id"], route["track_id"]))
            db.commit()
        except sqlite3.IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="route has ride history and cannot be deleted")
    return {"id": route_id, "deleted": True}


@app.post("/api/v1/routes/{route_id}/favorite")
def favorite_route(route_id: int, actor: RouteActorIn, me: dict = Depends(current_user)) -> dict:
    caller_owns(me, actor.driver_id)
    with closing(connection()) as db:
        route_actor(db, route_id, actor.driver_id)
        db.execute("INSERT OR IGNORE INTO route_favorites(user_id, route_id, created_at) VALUES (?, ?, ?)",
                   (actor.driver_id, route_id, utc_now()))
        db.commit()
    return {"id": route_id, "is_favorite": True}


@app.delete("/api/v1/routes/{route_id}/favorite")
def unfavorite_route(route_id: int, driver_id: int, me: dict = Depends(current_user)) -> dict:
    caller_owns(me, driver_id)
    with closing(connection()) as db:
        route_actor(db, route_id, driver_id)
        db.execute("DELETE FROM route_favorites WHERE user_id = ? AND route_id = ?", (driver_id, route_id))
        db.commit()
    return {"id": route_id, "is_favorite": False}


@app.post("/api/v1/routes/{route_id}/recent")
def mark_route_recent(route_id: int, actor: RouteActorIn, me: dict = Depends(current_user)) -> dict:
    caller_owns(me, actor.driver_id)
    with closing(connection()) as db:
        route_actor(db, route_id, actor.driver_id)
        db.execute(
            "INSERT INTO route_recents(user_id, route_id, last_used_at) VALUES (?, ?, ?) ON CONFLICT(user_id, route_id) DO UPDATE SET last_used_at = excluded.last_used_at",
            (actor.driver_id, route_id, utc_now()),
        )
        db.commit()
    return {"id": route_id, "marked_recent": True}


@app.delete("/api/v1/routes/{route_id}/recent")
def clear_route_recent(route_id: int, driver_id: int, me: dict = Depends(current_user)) -> dict:
    caller_owns(me, driver_id)
    with closing(connection()) as db:
        route_actor(db, route_id, driver_id)
        db.execute("DELETE FROM route_recents WHERE user_id = ? AND route_id = ?", (driver_id, route_id))
        db.commit()
    return {"id": route_id, "cleared": True}


@app.post("/api/v1/routes/{route_id}/share")
def share_route(route_id: int, share: RouteShareIn, me: dict = Depends(current_user)) -> dict:
    caller_owns(me, share.driver_id)
    with closing(connection()) as db:
        route, actor = route_actor(db, route_id, share.driver_id)
        if me["role"] != "admin" and route["recorder_id"] != me["id"]:
            raise HTTPException(status_code=403, detail="only the route owner or admin can share this route")
        if share.recipient_id is not None and db.execute("SELECT id FROM users WHERE id = ?", (share.recipient_id,)).fetchone() is None:
            raise HTTPException(status_code=404, detail="recipient not found")
        payload = {"route_id": route_id, "shared_by": share.driver_id, "recipient_id": share.recipient_id}
        db.execute("INSERT INTO events(kind, payload, created_at) VALUES (?, ?, ?)", ("route_shared", json.dumps(payload), utc_now()))
        db.commit()
    return {"id": route_id, "shared": True, "recipient_id": share.recipient_id}


@app.post("/api/v1/rides", status_code=201)
def start_ride(ride: RideIn, me: dict = Depends(current_user)) -> dict:
    caller_owns(me, ride.driver_id)
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
        try:
            cursor = db.execute(
                """
                INSERT INTO rides(driver_id, route_id, vehicle_type, vehicle_number, status, started_at)
                VALUES (?, ?, ?, ?, 'active', ?)
                """,
                (ride.driver_id, ride.route_id, ride.vehicle_type, ride.vehicle_number, started_at),
            )
            db.execute(
                "INSERT INTO route_recents(user_id,route_id,last_used_at) VALUES (?,?,?) "
                "ON CONFLICT(user_id,route_id) DO UPDATE SET last_used_at=excluded.last_used_at",
                (ride.driver_id, ride.route_id, started_at),
            )
            db.commit()
        except sqlite3.IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="driver already has an active ride")
    return {"id": cursor.lastrowid, **ride.model_dump(), "status": "active", "started_at": started_at}


@app.post("/api/v1/rides/{ride_id}/locations", status_code=201)
def update_live_location(ride_id: int, location: LiveLocationIn, me: dict = Depends(current_user)) -> dict:
    caller_owns(me, location.driver_id)
    recorded_at = utc_now()
    with closing(connection()) as db:
        ride = db.execute("SELECT driver_id, route_id, status FROM rides WHERE id = ?", (ride_id,)).fetchone()
        if ride is None:
            raise HTTPException(status_code=404, detail="ride not found")
        if ride["driver_id"] != location.driver_id:
            raise HTTPException(status_code=403, detail="location belongs to another driver")
        cursor = db.execute(
            """
            INSERT INTO live_locations(ride_id, driver_id, latitude, longitude, speed_mps, bearing, recorded_at)
            SELECT ?, ?, ?, ?, ?, ?, ?
            WHERE EXISTS (SELECT 1 FROM rides WHERE id = ? AND status = 'active')
            """,
            (ride_id, location.driver_id, location.latitude, location.longitude,
             location.speed_mps, location.bearing, recorded_at, ride_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=409, detail="ride has ended")
        hub = db.execute(
            "SELECT hub_latitude, hub_longitude FROM routes WHERE id = ?", (ride["route_id"],)
        ).fetchone()
        db.commit()
    distance_to_hub_m: float | None = None
    arrived = False
    if hub is not None and hub["hub_latitude"] is not None and hub["hub_longitude"] is not None:
        distance_to_hub_m = haversine_m(
            location.latitude, location.longitude, hub["hub_latitude"], hub["hub_longitude"]
        )
        arrived = distance_to_hub_m <= ARRIVAL_RADIUS_M
    return {
        "id": cursor.lastrowid,
        "ride_id": ride_id,
        **location.model_dump(),
        "recorded_at": recorded_at,
        "distance_to_hub_m": distance_to_hub_m,
        "arrived": arrived,
    }


def _finish_ride(db: sqlite3.Connection, ride_id: int, driver_id: int, outcome: str) -> dict:
    ended_at = utc_now()
    updated = db.execute(
        "UPDATE rides SET status = 'ended', ended_at = ? WHERE id = ? AND status = 'active'",
        (ended_at, ride_id),
    )
    if updated.rowcount == 1:
        db.execute(
            "INSERT INTO events(kind, payload, created_at) VALUES (?, ?, ?)",
            (outcome, json.dumps({"ride_id": ride_id, "driver_id": driver_id}), ended_at),
        )
        db.commit()
        return {"id": ride_id, "status": "ended", "ended_at": ended_at}
    db.commit()
    current = db.execute("SELECT status, ended_at FROM rides WHERE id = ?", (ride_id,)).fetchone()
    return {"id": ride_id, "status": current["status"], "ended_at": current["ended_at"]}


@app.post("/api/v1/rides/{ride_id}/end")
def end_ride(ride_id: int, body: EndRideIn, me: dict = Depends(current_user)) -> dict:
    if me["role"] != "admin":
        caller_owns(me, body.driver_id)
    with closing(connection()) as db:
        ride = db.execute("SELECT driver_id, status FROM rides WHERE id = ?", (ride_id,)).fetchone()
        if ride is None:
            raise HTTPException(status_code=404, detail="ride not found")
        if ride["driver_id"] != body.driver_id and me["role"] != "admin":
            raise HTTPException(status_code=403, detail="ride belongs to another driver")
        return _finish_ride(db, ride_id, ride["driver_id"], "ride_ended")


@app.post("/api/v1/rides/{ride_id}/arrive")
def arrive_ride(ride_id: int, body: ArriveIn, me: dict = Depends(current_user)) -> dict:
    if me["role"] != "admin":
        caller_owns(me, body.driver_id)
    with closing(connection()) as db:
        ride = db.execute("SELECT driver_id, route_id, status FROM rides WHERE id = ?", (ride_id,)).fetchone()
        if ride is None:
            raise HTTPException(status_code=404, detail="ride not found")
        if ride["driver_id"] != body.driver_id and me["role"] != "admin":
            raise HTTPException(status_code=403, detail="ride belongs to another driver")
        if ride["status"] != "active":
            current = db.execute("SELECT status, ended_at FROM rides WHERE id = ?", (ride_id,)).fetchone()
            return {"id": ride_id, "status": current["status"], "ended_at": current["ended_at"], "arrived": True}
        hub = db.execute(
            "SELECT hub_latitude, hub_longitude FROM routes WHERE id = ?", (ride["route_id"],)
        ).fetchone()
        distance_to_hub_m: float | None = None
        if hub is not None and hub["hub_latitude"] is not None and hub["hub_longitude"] is not None:
            latest = db.execute(
                "SELECT latitude, longitude FROM live_locations WHERE ride_id = ? ORDER BY id DESC LIMIT 1",
                (ride_id,),
            ).fetchone()
            if latest is None:
                raise HTTPException(status_code=409, detail="no live location recorded yet")
            distance_to_hub_m = haversine_m(
                latest["latitude"], latest["longitude"], hub["hub_latitude"], hub["hub_longitude"]
            )
            if distance_to_hub_m > ARRIVAL_RADIUS_M:
                raise HTTPException(
                    status_code=409,
                    detail=f"driver is {distance_to_hub_m:.0f}m from the hub (within {ARRIVAL_RADIUS_M:.0f}m required)",
                )
        result = _finish_ride(db, ride_id, ride["driver_id"], "ride_arrived")
        result["arrived"] = True
        result["distance_to_hub_m"] = distance_to_hub_m
        return result


@app.get("/api/v1/rides/active")
def active_rides(me: dict = Depends(current_user)) -> list[dict]:
    if me["role"] != "admin":
        raise HTTPException(status_code=403, detail="admin access required")
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
def driver_active_ride(driver_id: int, me: dict = Depends(current_user)) -> dict:
    if driver_id != me["id"] and me["role"] != "admin":
        raise HTTPException(status_code=403, detail="driver mismatch")
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
    points = json.loads(ride.pop("points")) if ride["points"] else []
    ride["destination_latitude"] = points[-1]["latitude"] if points else None
    ride["destination_longitude"] = points[-1]["longitude"] if points else None
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
def create_event(event: EventIn, me: dict = Depends(current_user)) -> dict:
    created_at = utc_now()
    with closing(connection()) as db:
        cursor = db.execute(
            "INSERT INTO events(kind, payload, created_at) VALUES (?, ?, ?)",
            (event.kind, json.dumps(event.payload), created_at),
        )
        db.commit()
        return {"id": cursor.lastrowid, "kind": event.kind, "payload": event.payload, "created_at": created_at}


@app.get("/api/v1/events")
def list_events(limit: int = 50, me: dict = Depends(current_user)) -> list[dict]:
    if me["role"] != "admin":
        raise HTTPException(status_code=403, detail="admin access required")
    if not 1 <= limit <= 200:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 200")
    with closing(connection()) as db:
        rows = db.execute(
            "SELECT id, kind, payload, created_at FROM events ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        try:
            item["payload"] = json.loads(row["payload"])
        except (ValueError, TypeError):
            item["payload"] = {"raw": row["payload"]}
        items.append(item)
    return items
