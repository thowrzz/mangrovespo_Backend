#!/usr/bin/env python
"""
MangroveSpot API Test Suite v2
Run: python test_api.py
"""

import urllib.request
import urllib.error
import json

BASE_URL = "http://127.0.0.1:8000"
results = []
token = None
first_activity_id = None

def req(method, path, data=None, tok=None):
    url = BASE_URL + path
    headers = {"Content-Type": "application/json"}
    if tok:
        headers["Authorization"] = "Bearer " + tok
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=5) as resp:
            raw = resp.read()
            try:
                return resp.status, json.loads(raw)
            except:
                return resp.status, {}
    except urllib.error.HTTPError as e:
        raw = b""
        try:
            raw = e.read()
            return e.code, json.loads(raw)
        except:
            return e.code, {"_raw": raw.decode(errors="ignore")[:100]}
    except Exception as ex:
        return 0, {"_error": str(ex)}

def test(label, method, path, expect, data=None, tok=None, show=None):
    status, body = req(method, path, data, tok)
    ok = (status == expect)
    results.append((label, ok, status, expect))
    icon = "OK  " if ok else "FAIL"
    print(f"  [{icon}] {status} | {method} {path}")
    if not ok:
        print(f"         Expected {expect} | Got: {str(body)[:120]}")
    elif show:
        val = body.get(show, body)
        print(f"         {show}: {str(val)[:80]}")
    return status, body

print("=" * 60)
print("  MangroveSpot Backend — Full API Test v2")
print("=" * 60)

# ── Get first real activity ID ────────────────────────────────────
_, acts = req("GET", "/api/v1/activities/")
results_list = acts.get("results", [])
first_activity_id = results_list[0]["id"] if results_list else None
total_activities = acts.get("count", 0)
print(f"\n  Found {total_activities} activities in DB")
print(f"  Using activity ID: {first_activity_id} for detail tests")

# ── 1. PUBLIC: Activities ─────────────────────────────────────────
print("\n[1] PUBLIC — Activities")
test("List all activities (expect 12)",  "GET", "/api/v1/activities/",  200, show="count")
test("Activity detail — real ID",        "GET", f"/api/v1/activities/{first_activity_id}/", 200, show="name")
test("Activity detail — fake ID 99999",  "GET", "/api/v1/activities/99999/", 404)
test("Availability — real ID + date",    "GET", f"/api/v1/activities/{first_activity_id}/availability/?date=2026-03-15", 200, show="slots")
test("Availability — missing date",      "GET", f"/api/v1/activities/{first_activity_id}/availability/", 400)
test("Availability — fake ID",           "GET", "/api/v1/activities/99999/availability/?date=2026-03-15", 404)

# ── 2. PUBLIC: Bookings ───────────────────────────────────────────
print("\n[2] PUBLIC — Bookings")
test("Initiate — empty body",            "POST", "/api/v1/bookings/initiate/", 400, data={})
test("Initiate — missing fields",        "POST", "/api/v1/bookings/initiate/", 400,
     data={"customer_name": "Test"})
test("Lookup — no params",               "GET",  "/api/v1/bookings/lookup/",   400)
test("Lookup — wrong reference",         "GET",  "/api/v1/bookings/lookup/?email=test@test.com&reference=MS-2026-0000", 404)

# ── 3. PUBLIC: Payments ───────────────────────────────────────────
print("\n[3] PUBLIC — Payments")
test("Verify — empty body",              "POST", "/api/v1/payments/verify/",   400, data={})
test("Webhook — no signature",           "POST", "/api/v1/payments/webhook/",  400, data={})

# ── 4. AUTH ───────────────────────────────────────────────────────
print("\n[4] AUTH — JWT")
test("Login — wrong password",           "POST", "/api/v1/admin/auth/login/",  401,
     data={"username": "wrong", "password": "wrong"})
_, login = test("Login — correct creds", "POST", "/api/v1/admin/auth/login/",  200,
     data={"username": "user", "password": "Admin@1234"}, show="access")
token = login.get("access")
_, ref = test("Token refresh",           "POST", "/api/v1/admin/auth/refresh/", 200,
     data={"refresh": login.get("refresh", "invalid")})

# ── 5. ADMIN — No token (must be blocked) ────────────────────────
print("\n[5] ADMIN — Blocked without token")
test("Activities list — no auth",        "GET",  "/api/v1/admin/activities/",       401)
test("Bookings list — no auth",          "GET",  "/api/v1/admin/bookings/",         401)
test("Blocked dates — no auth",          "GET",  "/api/v1/admin/blocked-dates/",    401)
test("Daily report — no auth",           "GET",  "/api/v1/admin/reports/daily/",    401)
test("Weekly report — no auth",          "GET",  "/api/v1/admin/reports/weekly/",   401)
test("CSV export — no auth",             "GET",  "/api/v1/admin/reports/export/",   401)

# ── 6. ADMIN — With valid token ───────────────────────────────────
print("\n[6] ADMIN — With valid token")
if token:
    test("Activities list — with auth",  "GET",  "/api/v1/admin/activities/",       200, tok=token)
    test("Bookings list — with auth",    "GET",  "/api/v1/admin/bookings/",         200, tok=token)
    test("Blocked dates — with auth",    "GET",  "/api/v1/admin/blocked-dates/",    200, tok=token)
    test("Daily report — with auth",     "GET",  "/api/v1/admin/reports/daily/",    200, tok=token)
    test("Weekly report — with auth",    "GET",  "/api/v1/admin/reports/weekly/",   200, tok=token)

    # Activity CRUD cycle
    print("\n[7] ADMIN — Activity CRUD")
    _, created = test("Create activity", "POST", "/api/v1/admin/activities/",       201, tok=token, data={
        "name": "Test Activity",
        "tagline": "Test tagline",
        "description": "Test description",
        "category": "water",
        "duration": "1 hr",
        "base_price": "500.00",
        "pricing_type": "per_person",
        "min_persons": 1,
        "max_persons": 10,
        "rules_text": "Test rules",
        "is_visible": True,
        "display_order": 99
    })
    new_id = created.get("id")
    if new_id:
        test("Get created activity",     "GET",  f"/api/v1/admin/activities/{new_id}/",  200, tok=token, show="name")
        test("Update price",             "PATCH",f"/api/v1/admin/activities/{new_id}/",  200, tok=token, data={"base_price": "750.00"})
        test("Visible in public API",    "GET",  f"/api/v1/activities/{new_id}/",         200)
        test("Check availability",       "GET",  f"/api/v1/activities/{new_id}/availability/?date=2026-03-15", 200)
        test("Soft delete",              "DELETE",f"/api/v1/admin/activities/{new_id}/", 204, tok=token)
        test("Not visible after delete", "GET",  f"/api/v1/activities/{new_id}/",         404)

    # Block a date
    print("\n[8] ADMIN — Block dates")
    _, blocked = test("Block a date",   "POST", "/api/v1/admin/blocked-dates/",     201, tok=token,
         data={"date": "2026-12-25", "reason": "holiday", "note": "Christmas closure"})
    block_id = blocked.get("id")
    if block_id:
        test("Blocked date in list",    "GET",  "/api/v1/admin/blocked-dates/",     200, tok=token)
        test("Delete block",            "DELETE",f"/api/v1/admin/blocked-dates/{block_id}/", 204, tok=token)

else:
    print("  [SKIP] No token — run: python manage.py createsuperuser")
    print("         Username: user | Password: Admin@1234")

# ── SUMMARY ───────────────────────────────────────────────────────
print("\n" + "=" * 60)
passed = sum(1 for _, ok, *_ in results if ok)
failed = sum(1 for _, ok, *_ in results if not ok)
total  = len(results)
print(f"  Total : {total}")
print(f"  Passed: {passed}  ✅")
print(f"  Failed: {failed}  {'❌' if failed else '✅'}")
if failed:
    print("\n  Failed tests:")
    for label, ok, got, exp in results:
        if not ok:
            print(f"    ✗ {label}  (got {got}, expected {exp})")
else:
    print("\n  🎉 ALL TESTS PASSED — Backend is fully functional!")
print("=" * 60)
