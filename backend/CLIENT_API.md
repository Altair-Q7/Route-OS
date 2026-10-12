# RouteOS client API (read-only)

RouteOS runs the delivery operation for Saravana: the admin creates each trip in
the app, the driver confirms quantities at each supermarket, and your system
reads the confirmed results from this API.

RouteOS never writes to your stock, invoices or payments. Trips are entered by
the RouteOS admin from the supervisor's brief, so there is no inbound trip API.

## Authentication

Every request sends your provisioned key:

```
X-RouteOS-Client-Key: <your key>
```

The key is read-only. It cannot create trips, confirm deliveries or change any
data. Without a valid key the API returns `401`.

Use HTTPS in production and send the key only over that connection.

### Getting a key

A RouteOS admin issues keys for you; you cannot create your own. Each key is
shown **once** when it is created and cannot be retrieved again, so store it
safely at that moment.

Keys can be given an expiry date, and more than one can be active at once so you
can replace one without interrupting your polling:

1. Ask for a second key.
2. Configure it in your system.
3. Confirm your system is reading results with it.
4. Ask for the first key to be revoked.

A revoked or expired key stops working immediately and returns `401`.

## Polling for results

Poll every minute or two. Catch-up is automatic, so a downtime on either side
loses nothing: ask again from your last cursor and you receive everything that
changed while you were away.

```
GET /api/v1/client/deliveries?since=<ISO-8601 timestamp>
```

- Omit `since` for a full read the first time.
- Store the `updated_at` of the newest trip you processed and pass it back.
- Only trips whose outcomes changed since that moment are returned, so this stays
  small as the history grows.
- **Percent-encode the timestamp.** A raw `+` in a query string is decoded as a
  space, so `2026-10-10T09:00:00+00:00` must be sent as
  `2026-10-10T09%3A00%3A00%2B00%3A00`. Most HTTP clients do this automatically
  when you pass the value as a query parameter; do not concatenate it by hand.

Response:

```json
{
  "count": 1,
  "trips": [
    {
      "id": 42,
      "trip": "SAP-TRIP-1042",
      "source": "native",
      "status": "Closed with shortages",
      "driver_id": 3,
      "driver_name": "Batter Driver",
      "vehicle": "KL-07-AX-1234",
      "sync_pending": false,
      "last_sync": null,
      "created_at": "2026-10-10T09:00:00+00:00",
      "updated_at": "2026-10-10T11:41:00+00:00",
      "ride": { "id": 88, "status": "ended",
                "started_at": "2026-10-10T09:30:00+00:00",
                "ended_at": "2026-10-10T11:40:00+00:00" },
      "location": { "latitude": 9.93, "longitude": 76.27,
                    "speed_mps": 8.4, "bearing": 120,
                    "recorded_at": "2026-10-10T11:39:50+00:00" },
      "stops": [
        {
          "id": "STOP-1",
          "customer": "Metro Fresh",
          "address_text": "MG Road",
          "latitude": 9.93,
          "longitude": 76.27,
          "status": "partial",
          "reason": "Shop had no storage",
          "confirmed_at": "2026-10-10T11:41:00+00:00",
          "items": [
            { "product_name": "Dosa Batter", "uom": "kg",
              "planned_quantity": "25", "delivered_quantity": "22" },
            { "product_name": "Idli Batter", "uom": "packet",
              "planned_quantity": "5",  "delivered_quantity": "5" }
          ]
        }
      ],
      "product_totals": [
        { "product_name": "Dosa Batter", "uom": "kg",
          "planned_quantity": "25", "delivered_quantity": "22" }
      ]
    }
  ]
}
```

`updated_at` only advances when confirmations or assignment details change. Live
GPS samples are included in the trip body but do not by themselves re-trigger the
cursor, so poll on the delivery outcomes rather than on movement.

## Single trip

```
GET /api/v1/client/deliveries/{id}
```

Returns the same object as one entry of the list above. `404` if the id is
unknown.

## Health

```
GET /health
```

Returns `{"status":"ok","service":"routeos-backend","organic_maps":true}` with no
authentication. Use it for availability checks.

## Field notes

- `status` on a trip is one of `Assigned`, `In progress`, `Delivered`,
  `Closed with shortages` or `Closed with failures`.
- `status` on a stop is `pending`, `arrived`, `delivered`, `partial` or `failed`.
- `delivered` means every assigned quantity was handed over. `partial` means some
  goods were short and `reason` explains why. `failed` means nothing was handed
  over and `reason` explains why.
- Confirmed outcomes are final and cannot be overwritten by the driver.
- Quantities keep their own unit. kg, litres and packets are never added
  together; use `product_totals` per `uom` for invoicing.
- Delivered quantity never exceeds the assigned quantity. Extra goods a
  supermarket asks for at the door are handled by your back office, outside
  RouteOS, so they do not appear here.
- GPS evidence shows the driver's position and the time it was recorded. It is
  proof of presence, never proof that a delivery happened.

## Errors

| Code | Meaning |
| --- | --- |
| 401 | Missing or wrong `X-RouteOS-Client-Key` |
| 404 | Unknown trip id |
| 422 | `since` was not a valid ISO-8601 timestamp |
| 503 | Client API access is not configured on the server |

Retry `5xx` with a backoff. A failed poll is safe: the cursor only moves forward
when you have processed a response.