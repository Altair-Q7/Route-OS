# RouteOS + ERPNext: first local integration

RouteOS continues to record GPS and navigate. ERPNext owns the delivery trip,
driver, vehicle, customers and Delivery Notes. RouteOS imports submitted trips
and writes GPS/delivery evidence to a separate **RouteOS Delivery Tracking**
document. It does **not** submit, cancel or modify Delivery Notes, inventory,
invoices, payments, or the standard ERPNext trip status.

## Start on this computer

ERPNext Docker must already be running. From any directory:

```bash
python3 "/home/altair/Altair/Projects/Route App/Route-OS/tools/run-routeos-erpnext-demo.py" --check
python3 "/home/altair/Altair/Projects/Route App/Route-OS/tools/run-routeos-erpnext-demo.py"
```

The launcher finds RouteOS relative to its own file, so moving the repository
does not break it. Use the new script path after moving the folder. It defaults
to ERPNext at `http://127.0.0.1:8080` and RouteOS port 8001. Options:
`--container`, `--site`, `--erp-url`, `--port`.

On first run it installs one custom tracking DocType, a restricted integration
role and API user. Existing ERP role permissions are preserved. That user can
read Delivery Trips/Drivers and create/update the separate tracking document;
it cannot change stock or accounting. API secrets are captured in memory and
passed to the backend environment, never saved in Git or sent to the phone.
These ERP schema/user additions persist after stopping the launcher. Running it
again reuses the same user and keys, not a new set of credentials.

It uses the existing backend database unless `ROUTEOS_DATABASE` overrides it.
Do not start two backend instances against that database: one integration
worker is supported. The launcher does not kill unrelated processes. Stop
your existing local backend first. Ctrl+C stops the launched server, not ERPNext.

## Phone connection for a local demo

The new Deliveries button requires rebuilding the embedded Flutter AAR and
Android app; a standalone `flutter run` is not sufficient.

For a **debug** phone build, forward the backend port:

```bash
adb reverse tcp:8001 tcp:8001
```

The debug build installs separately as `app.routeos.debug`, labelled **RouteOS
Test**. Open that app, not the regular release app. Its account/server settings
and map downloads are separate; the release app's saved data stays untouched.

In the app's server settings use `http://127.0.0.1:8001` and sign in to the
local backend. Changing servers signs out the current account; end any ride
or recording first. Release builds intentionally require HTTPS, so this HTTP
demo cannot be used with the existing release APK. A remote Render server also
cannot reach this computer's localhost ERPNext.

## Run a delivery

1. Finish ERPNext's Company setup, create a Driver/Vehicle, and create and submit
   a Delivery Trip with stops. Scheduled/In Transit trips are eligible.
2. Sign in as RouteOS admin, open **Deliveries**, choose **Assign ERPNext trip**
   and select the matching RouteOS driver. Mapping is explicit, not name guessing.
3. Driver opens Deliveries and sees only their assignments. Start a saved route
   normally using the **same vehicle number** as ERPNext, then choose **Link my
   current ride**. This does not generate navigation routes from ERP addresses.
4. Linked Delivery Notes supply product names, assigned quantities and units.
   For stops without a Delivery Note, admin chooses **Assign products** before
   linking a ride (for example Milk: 10 L, Batter: 2 kg). Products are locked
   after ride linking; ERP-sourced product manifests cannot be overridden here.
5. Driver explicitly confirms **arrived**, **delivered**, **partial**, or
   **failed** per stop. Delivered/partial confirmations require an actual
   quantity for every assigned product. Full delivery must match the assigned
   quantities; partial delivery needs some goods delivered, a shortage, and a
   reason. Failed means none delivered and requires a reason. Over-delivery,
   negative quantities and more than three decimal places are rejected.
   Product totals keep litres, kg and packets separate. GPS proximity and ending
   a ride never mean delivered. Final outcomes cannot be overwritten.
   Old confirmations without product data are retained, not given invented quantities.
6. Admin views driver GPS in the existing map, and linked GPS, ride timestamps,
   stop outcomes, reasons and sync errors in Deliveries. Refresh the delivery
   panel for current data; the existing live-map refresh is unchanged.
7. Background sync runs every 30 seconds while the backend is running. Errors
   stay in SQLite and retry with backoff. **Sync to ERPNext** queues a retry
   without blocking the phone. In ERPNext open the **RouteOS Delivery Tracking**
   list; each record links to its Delivery Trip and contains JSON evidence.
   Product quantities and reasons are included in that evidence and audit events;
   no ERPNext stock quantity or invoice is updated by a driver confirmation.

Re-importing a trip does not erase confirmations. A trip is imported as a
snapshot: later changes in ERPNext stops/driver are not automatically merged.
One trip links to one ride, and one ERP driver links to one RouteOS driver per
ERP site. Only the latest 100 assignments/trips are shown in this first version.
Signature/photo proof, multi-ride trips, dispatch notifications, route generation,
historical pagination and a graphical ERPNext live map are not implemented.

## Hosted setup later

Configure these only on the backend, not in Flutter:

```text
ROUTEOS_ERPNEXT_URL=https://your-erp.example.com
ROUTEOS_ERPNEXT_API_KEY=<restricted integration user's API key>
ROUTEOS_ERPNEXT_API_SECRET=<restricted integration user's API secret>
```

Install the tracking schema on that ERP site using `backend/setup_erpnext.py`
inside its Frappe bench with `--site SITE --apply`. Use one RouteOS backend
worker and persistent RouteOS database storage. Render Free's ephemeral SQLite
does not provide durable delivery evidence across redeploys/restarts.
