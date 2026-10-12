# RouteOS delivery: supermarkets, standing orders and extra requests

This describes the delivery flow RouteOS runs for Saravana, independent of any
external ERP. ERPNext remains supported but is optional and unused by this
client.

## The business

Saravana manufactures dosa and idli batter and delivers it to supermarkets.

- Every supermarket has a **standing order** — currently 5 packets.
- The driver hands over **exactly** the planned amount. A driver can never give
  extras on their own.
- A shop that wants more has the request **recorded at the stop**, per product.
  Nothing extra leaves the van on that trip.
- The request raises that shop's allocation on a **later trip**, or the admin
  moves that quantity to **another shop** on the same trip.
- Batter is perishable, so anything still planned but not handed over when a
  trip closes is what would spoil. Every trip reports that as `surplus`.

## Entities

| Table | Purpose |
| --- | --- |
| `supermarkets` | Directory of shops, with address, coordinates and an active flag |
| `standing_orders` | The usual allocation for a shop, applied when a trip includes it |
| `delivery_assignments` | A trip: its driver, vehicle and ordered stops |
| `delivery_events` | Immutable record of each confirmed stop outcome |
| `extra_requests` | Extra batter a shop asked for, pending or resolved |

Stops are stored as a JSON snapshot on the trip, but each one references a
`supermarket_id`. Renaming a shop updates its history without breaking the link.

Trips carry a `source` of `native` (built in the app) or `erpnext` (imported).
ERP columns are nullable, so a natively built trip has no ERP site or driver
rather than a placeholder value.

## Quantity rules

A driver confirms `delivered` / `partial` / `failed` per stop:

- Delivered must equal the planned quantity.
- Partial requires some goods short plus a reason.
- Delivered can never exceed planned.
- Final outcomes cannot be overwritten.

These rules are identical for imported and natively built trips.

## API

Admin (session authenticated):

| Endpoint | Purpose |
| --- | --- |
| `GET /api/v1/supermarkets` | Directory with each shop's standing order |
| `POST /api/v1/supermarkets` | Add a shop, optionally with its standing order |
| `PATCH /api/v1/supermarkets/{id}` | Edit a shop; a rename updates its history |
| `POST /api/v1/supermarkets/{id}/standing-order` | Replace the usual allocation |
| `POST /api/v1/deliveries/trips` | Build a trip from directory shops |
| `POST /api/v1/deliveries/{id}/transfer` | Move planned batter between two stops |
| `GET /api/v1/deliveries/extras` | Outstanding extra requests |
| `POST /api/v1/deliveries/extras/resolve` | Close them once planned in or moved |
| `POST /api/v1/deliveries/{id}/stops/{stop}` | Confirm a delivery, with extras |

The client's read-only endpoints are documented in [CLIENT_API.md](CLIENT_API.md).

## Standing a backend up

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
ROUTEOS_CLIENT_API_KEY=<key for the customer's system> \
  .venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
```

For a USB-connected phone expose the port with `adb reverse tcp:8000 tcp:8000`.

Startup migrations preserve existing routes, trips and delivery evidence. The
upgrade from the earlier schema rebuilds `delivery_assignments` and creates
directory entries for shops that older stops only named.