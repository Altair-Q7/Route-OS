"""Opt-in real ERPNext round-trip test; never collected by pytest.

Creates labelled temporary master/trip records, but no Delivery Notes or ledger
transactions. Removes only those exact fixtures in finally. Uses a temporary
RouteOS database and keeps API secrets out of console output.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


def bench(code):
    prefix = "import os,json,frappe\nos.chdir('sites')\nfrappe.init(site='localhost')\nfrappe.connect()\nfrappe.set_user('Administrator')\n"
    result = subprocess.run(["docker", "exec", "-i", "-w", "/home/frappe/frappe-bench",
                             "erpnext-backend-1", "env/bin/python", "-"],
                            input=prefix + code, text=True, capture_output=True, timeout=90)
    if result.returncode:
        raise RuntimeError(result.stderr)
    return json.loads(result.stdout.strip().splitlines()[-1])


def main():
    label = "RouteOS TEST " + uuid.uuid4().hex[:8]
    fixture = None
    original_defaults = bench("print(json.dumps({'currency_enabled': frappe.db.get_value('Currency','INR','enabled'), 'company':frappe.db.get_single_value('Global Defaults','default_company'), 'ledger_counts':{dt:frappe.db.count(dt) for dt in ['GL Entry','Stock Ledger Entry','Delivery Note','Sales Invoice']}}))")
    try:
        fixture = bench(f"""
label = {label!r}
frappe.flags.ignore_chart_of_accounts = True
try:
    company = frappe.get_doc({{'doctype':'Company','company_name':label,'abbr':label[-8:].upper(),
                              'default_currency':'INR','country':'India'}}).insert()
    group = frappe.get_doc({{'doctype':'Customer Group','customer_group_name':label+' Group','is_group':0}}).insert()
    territory = frappe.get_doc({{'doctype':'Territory','territory_name':label+' Territory','is_group':0}}).insert()
    template_created = not frappe.db.exists('Address Template','India')
    if template_created:
        frappe.get_doc({{'doctype':'Address Template','country':'India',
                        'template':'TEST ONLY: {{{{ address_line1 }}}} {{{{ city }}}}'}}).insert()
    customer = frappe.get_doc({{'doctype':'Customer','customer_name':label,'customer_type':'Individual',
                               'customer_group':group.name,'territory':territory.name}}).insert()
    address = frappe.get_doc({{'doctype':'Address','address_title':label,'address_type':'Shipping',
                              'address_line1':'TEST ONLY - not a real delivery','city':'Kattoor','country':'India',
                              'links':[{{'link_doctype':'Customer','link_name':customer.name}}]}}).insert()
    driver = frappe.get_doc({{'doctype':'Driver','full_name':label,'status':'Active'}}).insert()
    unit = frappe.get_doc({{'doctype':'UOM','uom_name':label+' Fuel Unit','must_be_whole_number':0}}).insert()
    vehicle = frappe.get_doc({{'doctype':'Vehicle','license_plate':'TEST-'+label[-8:],'make':'Test',
                              'model':'Test','last_odometer':0,'fuel_type':'Diesel','uom':unit.name,
                              'company':company.name}}).insert()
    trip = frappe.get_doc({{'doctype':'Delivery Trip','company':company.name,'driver':driver.name,
                           'vehicle':vehicle.name,'departure_time':frappe.utils.now_datetime(),
                           'delivery_stops':[{{'customer':customer.name,'address':address.name}},
                                             {{'customer':customer.name,'address':address.name}}]}}).insert()
    trip.submit()
    frappe.db.commit()
    print(json.dumps({{'company':company.name,'customer':customer.name,'address':address.name,
                      'driver':driver.name,'vehicle':vehicle.name,'trip':trip.name,
                      'group':group.name,'territory':territory.name,'unit':unit.name,
                      'template_created':template_created}}))
except Exception:
    frappe.db.rollback()
    raise
finally:
    frappe.destroy()
""")
        # Retrieve already-provisioned credentials without rotating keys or changing ERP permissions.
        credentials = bench("""
from frappe.utils.password import get_decrypted_password
user = 'routeos.integration@localhost.invalid'
print(json.dumps({'key':frappe.db.get_value('User',user,'api_key'),
                  'secret':get_decrypted_password('User',user,'api_secret')}))
""")
        os.environ.update(ROUTEOS_DATABASE=tempfile.mkdtemp(prefix="routeos-live-erp-") + "/test.db",
                          ROUTEOS_DEVELOPMENT_AUTH="0", ROUTEOS_DEMO_PASSWORD="Demo123",
                          ROUTEOS_ERPNEXT_URL="http://127.0.0.1:8080",
                          ROUTEOS_ERPNEXT_API_KEY=credentials["key"], ROUTEOS_ERPNEXT_API_SECRET=credentials["secret"])
        import app
        from fastapi.testclient import TestClient
        from erpnext_integration import erp_request
        from urllib.parse import quote
        with TestClient(app.app) as client:
            def login(name):
                response = client.post("/api/v1/auth/login", json={"name": name, "password": "Demo123"})
                assert response.status_code == 200, response.text
                user = response.json()
                return user, {"Authorization": "Bearer " + user["auth_token"]}

            driver, driver_auth = login("D.B Cooper")
            _, admin_auth = login("Sreekandan Nair")
            _, other_auth = login("Sukumara Kurup")
            catalog = client.get("/api/v1/erpnext/catalog", headers=admin_auth)
            assert catalog.status_code == 200, catalog.text
            assert any(row["name"] == fixture["trip"] for row in catalog.json()["trips"])
            response = client.post("/api/v1/erpnext/import", headers=admin_auth,
                                   json={"trip": fixture["trip"], "driver_id": driver["id"]})
            assert response.status_code == 201, response.text
            assignment = response.json()
            for stop in assignment['stops']:
                response = client.post(f"/api/v1/deliveries/{assignment['id']}/stops/{stop['id']}/products",
                                       headers=admin_auth, json={'items':[
                    {'product_name':'Milk','planned_quantity':'10','uom':'L'},
                    {'product_name':'Batter','planned_quantity':'2','uom':'kg'},
                ]})
                assert response.status_code == 200, response.text
                assignment = response.json()
            assert client.get("/api/v1/deliveries", headers=other_auth).json()["assignments"] == []
            points = [{"latitude": 10.4, "longitude": 76.2}, {"latitude": 10.41, "longitude": 76.21}]
            track = client.post("/api/v1/tracks", headers=driver_auth,
                                json={"recorder_id": driver["id"], "points": points}).json()
            route = client.post("/api/v1/routes", headers=driver_auth, json={
                "name": label, "recorder_id": driver["id"], "track_id": track["id"], "route_type": "recorded"}).json()
            ride = client.post("/api/v1/rides", headers=driver_auth, json={
                "driver_id": driver["id"], "route_id": route["id"], "vehicle_type": "van",
                "vehicle_number": fixture["vehicle"]}).json()
            response = client.post(f"/api/v1/deliveries/{assignment['id']}/ride", headers=driver_auth,
                                   json={"ride_id": ride["id"]})
            assert response.status_code == 200, response.text
            response = client.post(f"/api/v1/rides/{ride['id']}/locations", headers=driver_auth,
                                   json={"driver_id": driver["id"], "latitude": 10.41, "longitude": 76.21,
                                         "sample_id": "live-erp-test", "accuracy_meters": 4})
            assert response.status_code == 201, response.text
            assert app.delivery_integration.sync()["synced"] == 1
            rows = erp_request("GET", "/api/resource/RouteOS Delivery Tracking", query={
                "filters": json.dumps([["delivery_trip", "=", fixture["trip"]]]), "fields": '["name","tracking_data"]'})
            assert len(rows) == 1
            snapshot = json.loads(rows[0]["tracking_data"])
            assert snapshot["location"]["latitude"] == 10.41
            assert all(stop["status"] == "pending" for stop in snapshot["stops"])
            print("PASS: actual ERP trip import, driver isolation, ride link, GPS and tracking document creation")

            # Fail authentication to simulate ERP being unavailable, without stopping the user's ERP stack.
            secret = os.environ["ROUTEOS_ERPNEXT_API_SECRET"]
            os.environ["ROUTEOS_ERPNEXT_API_SECRET"] = "invalid-test-secret"
            stop = assignment["stops"][0]
            path = f"/api/v1/deliveries/{assignment['id']}/stops/{stop['id']}"
            delivered = {'status':'delivered', 'items':[
                {'id':item['id'], 'delivered_quantity':item['planned_quantity']} for item in stop['items']]}
            response = client.post(path, headers=driver_auth, json=delivered)
            assert response.status_code == 200, response.text
            first = response.json()
            assert app.delivery_integration.sync(force=True)["failed"] == 1
            pending = client.get("/api/v1/deliveries", headers=driver_auth).json()["assignments"][0]
            assert pending["sync_pending"] and pending["last_error"]
            os.environ["ROUTEOS_ERPNEXT_API_SECRET"] = secret
            assert client.post(path, headers=driver_auth, json=delivered).json()["stops"] == first["stops"]
            second = assignment["stops"][1]
            response = client.post(f"/api/v1/deliveries/{assignment['id']}/stops/{second['id']}", headers=driver_auth,
                                   json={"status": "failed", "reason": "TEST ONLY: customer unavailable"})
            assert response.status_code == 200, response.text
            assert app.delivery_integration.sync(force=True)["synced"] == 1
            rows = erp_request("GET", "/api/resource/RouteOS Delivery Tracking", query={
                "filters": json.dumps([["delivery_trip", "=", fixture["trip"]]]), "fields": '["name","tracking_data"]'})
            assert len(rows) == 1
            snapshot = json.loads(rows[0]["tracking_data"])
            assert snapshot["status"] == "Closed with failures"
            assert len(snapshot["events"]) == 2
            assert snapshot['product_totals'][0]['delivered_quantity'] == '10'
            assert snapshot['product_totals'][1]['delivered_quantity'] == '2'
            assert snapshot['events'][0]['items'][0]['delivered_quantity'] == '10'
            print("PASS: live authentication failure retains evidence; retry updates the same ERP document")
            response = client.post(f"/api/v1/rides/{ride['id']}/end", headers=driver_auth, json={"driver_id": driver["id"]})
            assert response.status_code == 200
            # Verify the real lifespan worker, not just the manual sync function.
            deadline = time.monotonic() + 40
            while time.monotonic() < deadline:
                pending = client.get('/api/v1/deliveries',headers=driver_auth).json()['assignments'][0]
                if not pending['sync_pending']:
                    break
                time.sleep(.5)
            else:
                raise AssertionError('Background ERP worker did not sync the ended ride')
            snapshot = json.loads(erp_request("GET", "/api/resource/RouteOS Delivery Tracking/" + quote(rows[0]["name"], safe=""))["tracking_data"])
            assert snapshot["ride"]["status"] == "ended"
            trip = erp_request("GET", "/api/resource/Delivery Trip/" + quote(fixture["trip"], safe=""))
            assert trip["status"] == "Scheduled" and trip["docstatus"] == 1
            assert all(stop["visited"] == 0 for stop in trip["delivery_stops"])
            print("PASS: actual background worker synchronized ride end; standard ERP trip unchanged")
        with TestClient(app.app) as restarted:
            restored = restarted.get('/api/v1/deliveries',headers=driver_auth)
            assert restored.status_code == 200, restored.text
            restored = restored.json()['assignments'][0]
            assert restored['ride']['status'] == 'ended'
            assert restored['stops'][0]['status'] == 'delivered'
            assert restored['stops'][1]['status'] == 'failed'
            assert len(restored['events']) == 2
            print('PASS: restart preserved session, GPS, delivery outcomes and audit evidence')
    finally:
        if fixture:
            cleanup = bench(f"""
fixture = {fixture!r}
defaults = {original_defaults!r}
try:
    for name in frappe.get_all('RouteOS Delivery Tracking', filters={{'delivery_trip':fixture['trip']}}, pluck='name'):
        frappe.delete_doc('RouteOS Delivery Tracking', name)
    trip = frappe.get_doc('Delivery Trip',fixture['trip'])
    if trip.docstatus == 1:
        trip.cancel()
    frappe.delete_doc('Delivery Trip', fixture['trip'])
    for doctype,key in [('Vehicle','vehicle'),('Driver','driver'),('Address','address'),('Customer','customer')]:
        frappe.delete_doc(doctype, fixture[key])
    frappe.delete_doc('Customer Group',fixture['group'])
    frappe.delete_doc('Territory',fixture['territory'])
    frappe.delete_doc('UOM',fixture['unit'])
    for name in frappe.get_all('Department',filters={{'company':fixture['company']}},pluck='name',order_by='lft desc'):
        frappe.delete_doc('Department', name)
    frappe.delete_doc('Company',fixture['company'])
    if fixture['template_created']:
        frappe.db.set_value('Address Template','India','is_default',0)
        frappe.delete_doc('Address Template','India')
    frappe.db.set_value('Currency','INR','enabled',defaults['currency_enabled'])
    frappe.db.set_single_value('Global Defaults','default_company', defaults['company'])
    assert {{dt:frappe.db.count(dt) for dt in defaults['ledger_counts']}} == defaults['ledger_counts'], 'Financial/stock document counts changed'
    frappe.db.commit()
    print(json.dumps({{'test_company_remaining':bool(frappe.db.exists('Company',fixture['company'])),
                      'test_trip_remaining':bool(frappe.db.exists('Delivery Trip',fixture['trip']))}}))
finally:
    frappe.destroy()
""")
            assert not any(cleanup.values()), cleanup
            print("PASS: temporary ERP fixture records removed; original defaults restored")


if __name__ == "__main__":
    main()
