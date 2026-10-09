"""Run inside a Frappe bench to install the isolated RouteOS tracking schema.

No ERPNext source files, delivery documents, stock or accounting are changed.
The local launcher captures --credentials output in memory; never paste it in logs.
"""
import argparse
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", default="localhost")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--credentials", action="store_true")
    args = parser.parse_args()
    import frappe
    from frappe.permissions import add_permission
    from frappe.utils.password import get_decrypted_password

    # Bench commands run from sites/, which Frappe also uses to resolve logs.
    if Path("sites").is_dir():
        os.chdir("sites")
    frappe.init(site=args.site)
    frappe.connect()
    try:
        if not args.apply:
            print(json.dumps({"tracking_schema_installed": bool(frappe.db.exists("DocType", "RouteOS Delivery Tracking")),
                              "company_count": frappe.db.count("Company"),
                              "delivery_trip_count": frappe.db.count("Delivery Trip")}))
            return
        frappe.set_user("Administrator")
        role = "RouteOS Integration"
        user = "routeos.integration@localhost.invalid"
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 0}).insert()
        if not frappe.db.exists("DocType", "RouteOS Delivery Tracking"):
            frappe.get_doc({
                "doctype": "DocType", "name": "RouteOS Delivery Tracking", "module": "Custom",
                "custom": 1, "autoname": "field:routeos_reference", "track_changes": 1,
                "fields": [
                    {"fieldname": "routeos_reference", "label": "RouteOS Reference", "fieldtype": "Data", "reqd": 1, "unique": 1},
                    {"fieldname": "delivery_trip", "label": "Delivery Trip", "fieldtype": "Link", "options": "Delivery Trip", "reqd": 1, "in_list_view": 1},
                    {"fieldname": "driver", "label": "Driver", "fieldtype": "Link", "options": "Driver", "in_list_view": 1},
                    {"fieldname": "tracking_status", "label": "Delivery Tracking Status", "fieldtype": "Data", "in_list_view": 1},
                    {"fieldname": "last_update_utc", "label": "Last Update (UTC)", "fieldtype": "Data"},
                    {"fieldname": "tracking_data", "label": "GPS and Delivery Evidence", "fieldtype": "Code", "options": "JSON"},
                ],
                "permissions": [
                    {"role": role, "read": 1, "write": 1, "create": 1},
                    {"role": "System Manager", "read": 1},
                    {"role": "Stock User", "read": 1},
                ],
            }).insert()
        for doctype in ("Delivery Trip", "Driver", "Delivery Note"):
            if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role}):
                # Frappe copies existing permissions first; preserve all ERP roles.
                add_permission(doctype, role, ptype="read")
        if not frappe.db.exists("User", user):
            frappe.get_doc({"doctype": "User", "email": user, "first_name": "RouteOS Integration",
                            "enabled": 1, "send_welcome_email": 0, "user_type": "System User",
                            "roles": [{"role": role}]}).insert()
        account = frappe.get_doc("User", user)
        if not account.enabled:
            raise RuntimeError("Integration user is disabled; enable it explicitly before continuing")
        if role not in [item.role for item in account.roles]:
            account.append("roles", {"role": role})
        if not account.api_key:
            account.api_key = frappe.generate_hash(length=20)
        secret = get_decrypted_password("User", user, "api_secret", raise_exception=False)
        if not secret:
            secret = frappe.generate_hash(length=32)
            account.api_secret = secret
        account.save()
        frappe.db.commit()
        frappe.clear_cache()
        if args.credentials:
            print(json.dumps({"api_key": account.api_key, "api_secret": secret}))
        else:
            print("RouteOS tracking schema and restricted integration user are ready.")
    finally:
        frappe.destroy()


if __name__ == "__main__":
    main()
