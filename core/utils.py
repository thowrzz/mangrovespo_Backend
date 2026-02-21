import random
from datetime import datetime


def generate_booking_reference():
    """
    Generates unique booking reference in format MS-YYYY-XXXX
    Example: MS-2026-4821
    Checks DB to ensure uniqueness.
    """
    from apps.bookings.models import Booking
    year = datetime.now().year
    for _ in range(100):  # max 100 attempts
        number = random.randint(1000, 9999)
        ref = f"MS-{year}-{number}"
        if not Booking.objects.filter(reference=ref).exists():
            return ref
    raise ValueError("Could not generate unique booking reference")
