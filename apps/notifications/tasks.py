from celery import shared_task
from django.conf import settings
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import logging

logger = logging.getLogger(__name__)


def _send_email(to_email, subject, html_content):
    """Internal helper to send email via SendGrid."""
    message = Mail(
        from_email=settings.DEFAULT_FROM_EMAIL,
        to_emails=to_email,
        subject=subject,
        html_content=html_content,
    )
    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        sg.send(message)
    except Exception as e:
        logger.error(f"SendGrid error: {e}")


@shared_task
def send_booking_confirmation_email(booking_id):
    """Sends booking confirmation email to customer."""
    from apps.bookings.models import Booking
    booking = Booking.objects.prefetch_related('items__activity', 'items__slot').get(id=booking_id)

    items_html = ""
    for item in booking.items.all():
        items_html += f"""
        <tr>
            <td>{item.activity.name}</td>
            <td>{item.visit_date}</td>
            <td>{item.slot.label}</td>
            <td>{item.num_persons}</td>
            <td>₹{item.price_snapshot}</td>
        </tr>"""

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;">
        <h2 style="color:#2d7a4f;">🌿 Booking Confirmed — Mangrove Spot</h2>
        <p>Hi {booking.customer_name},</p>
        <p>Your booking is confirmed! Reference: <strong>{booking.reference}</strong></p>
        <table border="1" cellpadding="8" style="border-collapse:collapse;width:100%;">
            <tr style="background:#2d7a4f;color:white;">
                <th>Activity</th><th>Date</th><th>Time</th><th>Persons</th><th>Amount</th>
            </tr>
            {items_html}
        </table>
        <p style="font-size:1.2em;"><strong>Total Paid: ₹{booking.grand_total}</strong></p>
        <p>📍 Nedungolam, Paravur, Kollam, Kerala 691334</p>
        <p>📞 9496141619</p>
        <p style="color:#666;">Questions? Reply to this email or call us.</p>
    </div>
    """
    _send_email(booking.customer_email, f"Booking Confirmed — {booking.reference}", html)


@shared_task
def send_owner_new_booking_alert(booking_id):
    """Sends new booking alert to owner."""
    from apps.bookings.models import Booking
    booking = Booking.objects.prefetch_related('items__activity').get(id=booking_id)

    admin_url = f"{settings.FRONTEND_URL}/admin/bookings/{booking.reference}"
    html = f"""
    <div style="font-family:Arial,sans-serif;">
        <h2>🔔 New Booking — {booking.reference}</h2>
        <p><strong>Customer:</strong> {booking.customer_name}</p>
        <p><strong>Phone:</strong> {booking.customer_phone}</p>
        <p><strong>Email:</strong> {booking.customer_email}</p>
        <p><strong>Total:</strong> ₹{booking.grand_total}</p>
        <p><a href="{admin_url}">View in Admin Panel</a></p>
    </div>
    """
    _send_email(settings.ADMIN_EMAIL, f"New Booking: {booking.reference}", html)


@shared_task
def send_cancellation_email(booking_id):
    """Sends cancellation email to customer."""
    from apps.bookings.models import Booking
    booking = Booking.objects.get(id=booking_id)
    html = f"""
    <div style="font-family:Arial,sans-serif;">
        <h2 style="color:#d9534f;">Booking Cancelled — {booking.reference}</h2>
        <p>Hi {booking.customer_name},</p>
        <p>Your booking <strong>{booking.reference}</strong> has been cancelled.</p>
        <p>Refund of <strong>₹{booking.grand_total}</strong> will be processed in 3–5 business days.</p>
        <p>📞 9496141619 | mangrovespot.care@gmail.com</p>
    </div>
    """
    _send_email(booking.customer_email, f"Booking Cancelled — {booking.reference}", html)


@shared_task
def release_expired_slot_holds():
    """
    Celery Beat task — runs every 5 minutes.
    Releases slot holds for pending bookings past their 15-min hold window.
    """
    from apps.bookings.models import Booking
    from django.utils import timezone
    expired = Booking.objects.filter(
        status='pending',
        items__slot_hold_expires__lt=timezone.now()
    ).distinct()
    count = expired.count()
    expired.update(status='expired')
    logger.info(f"Released {count} expired slot holds")
    return count


@shared_task
def send_24hr_reminders():
    """
    Celery Beat task — runs daily at 8 PM IST.
    Sends reminder emails for tomorrow's activities.
    """
    from apps.bookings.models import BookingItem
    from datetime import date, timedelta
    tomorrow = date.today() + timedelta(days=1)
    items = BookingItem.objects.filter(
        visit_date=tomorrow,
        booking__status='confirmed'
    ).select_related('booking', 'activity', 'slot')
    for item in items:
        html = f"""
        <div style="font-family:Arial,sans-serif;">
            <h2 style="color:#2d7a4f;">⏰ Reminder — Tomorrow at Mangrove Spot</h2>
            <p>Hi {item.booking.customer_name},</p>
            <p>Reminder: <strong>{item.activity.name}</strong> tomorrow at <strong>{item.slot.label}</strong></p>
            <p>📍 Nedungolam, Paravur, Kollam, Kerala</p>
            <p>What to bring: Comfortable clothes, water, sunscreen.</p>
            <p>📞 9496141619</p>
        </div>
        """
        _send_email(item.booking.customer_email, f"Reminder: {item.activity.name} tomorrow!", html)
