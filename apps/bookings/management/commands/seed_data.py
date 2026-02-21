from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, time
import random

from apps.activities.models import Activity, TimeSlot
from apps.bookings.models import Booking, BookingItem


class Command(BaseCommand):
    help = "Seed test data for MangroveSpot admin dashboard"

    def handle(self, *args, **kwargs):

        # ── Print TimeSlot fields so we know what to use ──────
        ts_fields = [f.name for f in TimeSlot._meta.get_fields()]
        self.stdout.write(f"TimeSlot fields: {ts_fields}")

        # ── Activities ────────────────────────────────────────
        self.stdout.write("Seeding activities...")
        activity_data = [
            {"name": "Kayaking",         "base_price": 750,  "pricing_type": "per_person", "min_persons": 1, "max_persons": 10, "is_visible": True},
            {"name": "Bird Watching",    "base_price": 500,  "pricing_type": "per_person", "min_persons": 1, "max_persons": 15, "is_visible": True},
            {"name": "Mangrove Walk",    "base_price": 400,  "pricing_type": "per_person", "min_persons": 1, "max_persons": 20, "is_visible": True},
            {"name": "Boat Safari",      "base_price": 900,  "pricing_type": "per_group",  "min_persons": 1, "max_persons": 8,  "is_visible": True},
            {"name": "Photography Tour", "base_price": 600,  "pricing_type": "per_person", "min_persons": 1, "max_persons": 6,  "is_visible": True},
        ]

        activities = []
        for a in activity_data:
            obj, created = Activity.objects.get_or_create(
                name=a["name"], defaults=a
            )
            activities.append(obj)
            self.stdout.write(f"  {'created' if created else 'exists'}: {obj.name}")

        self.stdout.write(f"✅ {len(activities)} activities")

        # ── TimeSlots ─────────────────────────────────────────
        # We'll create minimal slots using only fields we know exist
        # id, created_at, updated_at, activity are safe — rest detected above
        self.stdout.write("Seeding timeslots...")
        slots = []

        slot_defs = [
            {"label": "Morning",   "slot_time": time(7, 0),  "capacity": 20},
            {"label": "Afternoon", "slot_time": time(11, 0), "capacity": 15},
            {"label": "Evening",   "slot_time": time(15, 0), "capacity": 12},
        ]

        # Build defaults only with fields that exist on TimeSlot
        for activity in activities:
            for sd in slot_defs:
                defaults = {}
                if "capacity"   in ts_fields: defaults["capacity"]   = sd["capacity"]
                if "label"      in ts_fields: defaults["label"]      = sd["label"]
                if "name"       in ts_fields: defaults["name"]       = sd["label"]
                if "slot_time"  in ts_fields: defaults["slot_time"]  = sd["slot_time"]
                if "time"       in ts_fields: defaults["time"]       = sd["slot_time"]
                if "start_time" in ts_fields: defaults["start_time"] = sd["slot_time"]
                if "is_active"  in ts_fields: defaults["is_active"]  = True

                # Use label or name as lookup key
                lookup_field = "label" if "label" in ts_fields else "name" if "name" in ts_fields else None

                if lookup_field:
                    slot, _ = TimeSlot.objects.get_or_create(
                        activity=activity,
                        **{lookup_field: sd["label"]},
                        defaults=defaults,
                    )
                else:
                    slot = TimeSlot.objects.create(activity=activity, **defaults)

                slots.append(slot)

        self.stdout.write(f"✅ {len(slots)} slots")

        # ── Bookings ──────────────────────────────────────────
        self.stdout.write("Seeding bookings...")
        customers = [
            ("Adarsh BS",      "9876543210", "adarsh@email.com"),
            ("Priya Nair",     "9876543211", "priya@email.com"),
            ("Rahul Menon",    "9876543212", "rahul@email.com"),
            ("Sneha Thomas",   "9876543213", "sneha@email.com"),
            ("Arjun Kumar",    "9876543214", "arjun@email.com"),
            ("Divya Pillai",   "9876543215", "divya@email.com"),
            ("Vishnu Raj",     "9876543216", "vishnu@email.com"),
            ("Meera Krishnan", "9876543217", "meera@email.com"),
            ("Kiran Das",      "9876543218", "kiran@email.com"),
            ("Anjali Raj",     "9876543219", "anjali@email.com"),
        ]

        statuses = ["confirmed", "confirmed", "confirmed", "completed", "completed", "pending", "cancelled"]
        today = timezone.localdate()
        created_count = 0

        for i, (name, phone, email) in enumerate(customers):
            ref = f"MS-2026-{100 + i:03d}"
            if Booking.objects.filter(reference=ref).exists():
                self.stdout.write(f"  skip: {ref}")
                continue

            days_ago    = i % 7
            created_dt  = timezone.now() - timedelta(days=days_ago)
            visit_dt    = today + timedelta(days=random.randint(1, 14))
            status      = statuses[i % len(statuses)]
            num_persons = random.randint(1, 4)

            chosen_slots  = random.sample(slots, random.randint(1, 2))
            grand_total   = sum(s.activity.base_price * num_persons for s in chosen_slots)

            booking = Booking.objects.create(
                customer_name=name,
                customer_phone=phone,
                customer_email=email,
                status=status,
                grand_total=grand_total,
                reference=ref,
            )
            Booking.objects.filter(pk=booking.pk).update(created_at=created_dt)

            for slot in chosen_slots:
                # Get price_snapshot field name
                bi_fields = [f.name for f in BookingItem._meta.get_fields()]
                item_data = {
                    "booking":    booking,
                    "activity":   slot.activity,
                    "slot":       slot,
                    "visit_date": visit_dt,
                    "num_persons": num_persons,
                }
                if "price_snapshot" in bi_fields:
                    item_data["price_snapshot"] = slot.activity.base_price
                elif "unit_price" in bi_fields:
                    item_data["unit_price"] = slot.activity.base_price

                BookingItem.objects.create(**item_data)

            created_count += 1
            self.stdout.write(f"  created: {ref} — {name} ({status})")

        self.stdout.write(self.style.SUCCESS(
            f"\n🚀 Done! {created_count} bookings | "
            f"{BookingItem.objects.count()} items | "
            f"{Activity.objects.count()} activities"
        ))
