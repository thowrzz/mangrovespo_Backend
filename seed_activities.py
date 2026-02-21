#!/usr/bin/env python
"""
MangroveSpot — Seed 12 Real Activities
Run: python seed_activities.py
Make sure server is running first.
"""

import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.activities.models import Activity, TimeSlot

# Delete the test activity first
Activity.objects.all().delete()
print("Cleared existing activities...")

activities = [
    {
        "name": "Kayaking",
        "tagline": "Paddle through the serene mangrove canals",
        "description": "Experience the tranquil beauty of the Paravur backwaters from the seat of a kayak. Glide through narrow mangrove-lined canals, spot exotic birds, and enjoy the peaceful sounds of nature. Suitable for beginners and experienced paddlers alike. Life jackets and paddles provided. A guide accompanies every session.",
        "category": "water",
        "duration": "45 min",
        "base_price": 400,
        "pricing_type": "per_person",
        "min_persons": 1,
        "max_persons": 10,
        "rules_text": "Life jacket must be worn at all times. Minimum age: 8 years. Listen to guide instructions before starting.",
        "is_popular": True,
        "display_order": 1,
        "slots": [
            {"label": "6:30 AM Sunrise", "time": "06:30", "capacity": 10},
            {"label": "9:00 AM Morning", "time": "09:00", "capacity": 10},
            {"label": "4:00 PM Evening", "time": "16:00", "capacity": 10},
        ]
    },
    {
        "name": "Coracle Ride",
        "tagline": "Spin and glide on a traditional round boat",
        "description": "Try the iconic round coracle boat — a traditional fishing vessel used for centuries in Kerala. Your expert boatman will spin and navigate through the backwaters while you enjoy the unique experience. Perfect for families and first-time visitors. Great photo opportunity!",
        "category": "water",
        "duration": "20 min",
        "base_price": 300,
        "pricing_type": "per_group",
        "min_persons": 1,
        "max_persons": 3,
        "rules_text": "Max 3 persons per coracle. Life jacket provided. Not recommended for people with back problems.",
        "is_popular": True,
        "display_order": 2,
        "slots": [
            {"label": "7:00 AM", "time": "07:00", "capacity": 8},
            {"label": "10:00 AM", "time": "10:00", "capacity": 8},
            {"label": "3:00 PM", "time": "15:00", "capacity": 8},
            {"label": "5:00 PM", "time": "17:00", "capacity": 8},
        ]
    },
    {
        "name": "Country Boat Ride",
        "tagline": "Cruise the backwaters on a traditional wooden boat",
        "description": "Enjoy a relaxing cruise through the calm backwaters of Paravur on a traditional wooden country boat. Take in the scenic mangrove landscape, watch local fishermen at work, and feel the gentle breeze as you drift along. Ideal for families and groups wanting a slow, scenic experience.",
        "category": "water",
        "duration": "30 min",
        "base_price": 800,
        "pricing_type": "per_group",
        "extra_person_charge": 100,
        "min_persons": 1,
        "max_persons": 8,
        "rules_text": "Base price covers up to 4 persons. Additional ₹100 per person above 4. Life jackets provided. No standing while boat is moving.",
        "is_popular": False,
        "display_order": 3,
        "slots": [
            {"label": "7:00 AM", "time": "07:00", "capacity": 5},
            {"label": "9:30 AM", "time": "09:30", "capacity": 5},
            {"label": "2:00 PM", "time": "14:00", "capacity": 5},
            {"label": "5:00 PM", "time": "17:00", "capacity": 5},
        ]
    },
    {
        "name": "Bamboo Rafting",
        "tagline": "Float through the mangroves on a bamboo raft",
        "description": "Step onto a handcrafted bamboo raft and drift through the calm mangrove waterways. This unique experience connects you with traditional Kerala river culture. Pole your way gently through the water guided by an expert. A meditative, one-of-a-kind experience you won't find anywhere else.",
        "category": "water",
        "duration": "30 min",
        "base_price": 350,
        "pricing_type": "per_person",
        "min_persons": 1,
        "max_persons": 6,
        "rules_text": "Life jacket must be worn. Minimum age 10 years. Not suitable for non-swimmers without prior intimation.",
        "is_popular": False,
        "display_order": 4,
        "slots": [
            {"label": "8:00 AM", "time": "08:00", "capacity": 6},
            {"label": "11:00 AM", "time": "11:00", "capacity": 6},
            {"label": "4:00 PM", "time": "16:00", "capacity": 6},
        ]
    },
    {
        "name": "Zip Line",
        "tagline": "Soar above the mangroves at thrilling speed",
        "description": "Get your adrenaline pumping with our zip line that takes you soaring above the lush green mangrove canopy. With a full safety harness and trained staff, you'll fly across the treetops and enjoy a bird's-eye view of the backwaters below. One of the most exciting activities at Mangrove Spot!",
        "category": "thrill",
        "duration": "15 min",
        "base_price": 300,
        "pricing_type": "per_person",
        "min_persons": 1,
        "max_persons": 20,
        "rules_text": "Minimum age: 10 years. Weight limit: 100kg. Full safety harness provided. Not suitable for pregnant women or people with heart conditions.",
        "is_popular": True,
        "display_order": 5,
        "slots": [
            {"label": "9:00 AM", "time": "09:00", "capacity": 15},
            {"label": "11:00 AM", "time": "11:00", "capacity": 15},
            {"label": "2:00 PM", "time": "14:00", "capacity": 15},
            {"label": "4:00 PM", "time": "16:00", "capacity": 15},
        ]
    },
    {
        "name": "ATV Ride",
        "tagline": "Conquer the mud tracks on a quad bike",
        "description": "Ride an All-Terrain Vehicle through rugged mud trails and open tracks around the mangrove estate. Feel the power under you as you navigate through challenging terrain. Helmets and safety gear provided. Guided by trained instructors. Perfect for thrill-seekers who want an off-road adventure.",
        "category": "thrill",
        "duration": "20 min",
        "base_price": 500,
        "pricing_type": "per_person",
        "min_persons": 1,
        "max_persons": 10,
        "rules_text": "Minimum age: 14 years. Helmet and gear mandatory. No prior experience required — instructor guides you. Closed-toe shoes required.",
        "is_popular": False,
        "display_order": 6,
        "slots": [
            {"label": "9:00 AM", "time": "09:00", "capacity": 5},
            {"label": "11:00 AM", "time": "11:00", "capacity": 5},
            {"label": "2:00 PM", "time": "14:00", "capacity": 5},
            {"label": "4:00 PM", "time": "16:00", "capacity": 5},
        ]
    },
    {
        "name": "Archery",
        "tagline": "Test your aim with bow and arrow",
        "description": "Learn the ancient art of archery at our dedicated range. Our trained instructors will teach you the correct posture, aim, and release technique. Whether you are a beginner or have prior experience, this activity is both challenging and deeply satisfying. Bows, arrows, and safety equipment provided.",
        "category": "skill",
        "duration": "30 min",
        "base_price": 250,
        "pricing_type": "per_person",
        "min_persons": 1,
        "max_persons": 15,
        "rules_text": "Minimum age: 8 years. All equipment provided. Follow instructor directions at all times. No shooting outside the designated range.",
        "is_popular": False,
        "display_order": 7,
        "slots": [
            {"label": "9:00 AM", "time": "09:00", "capacity": 10},
            {"label": "11:00 AM", "time": "11:00", "capacity": 10},
            {"label": "2:00 PM", "time": "14:00", "capacity": 10},
            {"label": "4:00 PM", "time": "16:00", "capacity": 10},
        ]
    },
    {
        "name": "Fishing",
        "tagline": "Cast your line in the backwaters",
        "description": "Enjoy the meditative experience of fishing in the calm Paravur backwaters. Rods, bait, and equipment are all provided. Our guides will take you to the best spots and teach you techniques if needed. A perfect activity for all ages — relaxing, patient, and rewarding. Catch and release policy.",
        "category": "skill",
        "duration": "1 hr",
        "base_price": 300,
        "pricing_type": "per_person",
        "min_persons": 1,
        "max_persons": 8,
        "rules_text": "Fishing equipment provided. Catch and release only. No experience needed — guide assists. Minimum age: 6 years with adult supervision.",
        "is_popular": False,
        "display_order": 8,
        "slots": [
            {"label": "6:30 AM Sunrise", "time": "06:30", "capacity": 8},
            {"label": "9:00 AM", "time": "09:00", "capacity": 8},
            {"label": "4:00 PM", "time": "16:00", "capacity": 8},
        ]
    },
    {
        "name": "Nature Walk",
        "tagline": "Explore the mangrove ecosystem on foot",
        "description": "Walk through the mangrove forest with an expert naturalist guide who will introduce you to the unique flora and fauna of this coastal ecosystem. Learn about mangrove ecology, spot birds, crabs, and fish in their natural habitat. Educational and refreshing — ideal for families, school groups, and nature lovers.",
        "category": "land",
        "duration": "45 min",
        "base_price": 200,
        "pricing_type": "per_person",
        "min_persons": 1,
        "max_persons": 20,
        "rules_text": "Wear comfortable walking shoes. Carry water. Do not disturb wildlife. Stay with the group at all times.",
        "is_popular": False,
        "display_order": 9,
        "slots": [
            {"label": "7:00 AM", "time": "07:00", "capacity": 15},
            {"label": "9:00 AM", "time": "09:00", "capacity": 15},
            {"label": "4:30 PM", "time": "16:30", "capacity": 15},
        ]
    },
    {
        "name": "Mud Activities",
        "tagline": "Get down and dirty in the mangrove mud",
        "description": "Embrace the raw fun of playing in natural mangrove mud! This unique activity lets you experience the therapeutic properties of mangrove soil while having an absolute blast. Popular with groups, families, and team-building outings. You will get messy — and you'll love every second of it. Shower facilities available.",
        "category": "group_fun",
        "duration": "45 min",
        "base_price": 250,
        "pricing_type": "per_person",
        "min_persons": 4,
        "max_persons": 30,
        "rules_text": "Minimum 4 persons required. Wear clothes you don't mind getting dirty. Shower and changing facilities available on site. Not recommended for people with open wounds or skin conditions.",
        "is_popular": False,
        "display_order": 10,
        "slots": [
            {"label": "10:00 AM", "time": "10:00", "capacity": 20},
            {"label": "2:00 PM", "time": "14:00", "capacity": 20},
        ]
    },
    {
        "name": "Tug of War",
        "tagline": "Classic team battle by the waterside",
        "description": "Gather your group for an energetic game of Tug of War on the banks of the backwaters. Split into two teams, grab the rope, and pull with everything you've got! A fantastic group activity that builds teamwork, brings out competitive spirit, and creates memories. Great for corporate groups, school trips, and family outings.",
        "category": "group_fun",
        "duration": "30 min",
        "base_price": 1500,
        "pricing_type": "per_group",
        "min_persons": 10,
        "max_persons": 40,
        "rules_text": "Minimum 10 persons required for two equal teams. Flat footwear recommended. Pre-booking mandatory for groups above 20.",
        "is_popular": False,
        "requires_prebooking": True,
        "display_order": 11,
        "slots": [
            {"label": "10:00 AM", "time": "10:00", "capacity": 3},
            {"label": "2:00 PM", "time": "14:00", "capacity": 3},
            {"label": "4:00 PM", "time": "16:00", "capacity": 3},
        ]
    },
    {
        "name": "Cultural Performance",
        "tagline": "Experience traditional Kerala art forms live",
        "description": "Witness a live performance of Kerala's rich cultural heritage including Kalaripayattu (martial arts), folk music, and traditional dance. Performed by trained local artists, this show gives you a window into the ancient traditions of Kerala. Available for groups by advance booking. A truly memorable cultural experience.",
        "category": "cultural",
        "duration": "1 hr",
        "base_price": 3000,
        "pricing_type": "per_group",
        "min_persons": 10,
        "max_persons": 100,
        "rules_text": "Advance booking mandatory. Minimum group size 10 persons. Photography allowed. Show includes Kalaripayattu demonstration, folk music, and dance.",
        "is_popular": False,
        "requires_prebooking": True,
        "display_order": 12,
        "slots": [
            {"label": "6:30 PM Evening", "time": "18:30", "capacity": 5},
        ]
    },
]

created_count = 0
for data in activities:
    slots_data = data.pop("slots")
    activity = Activity.objects.create(**data)
    for slot in slots_data:
        TimeSlot.objects.create(
            activity=activity,
            label=slot["label"],
            time=slot["time"],
            capacity=slot["capacity"],
            is_active=True
        )
    print(f"  ✅ {activity.name} — {len(slots_data)} slots added")
    created_count += 1

print(f"\n🎉 Done! {created_count} activities created with all time slots.")
print(f"   Visit: http://127.0.0.1:8000/api/v1/activities/")
