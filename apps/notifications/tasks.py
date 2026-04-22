# from celery import shared_task
# from django.conf import settings
# from sendgrid import SendGridAPIClient
# from sendgrid.helpers.mail import Mail
# import logging

# logger = logging.getLogger(__name__)


# def _send_email(to_email, subject, html_content):
#     """Internal helper to send email via SendGrid."""
#     message = Mail(
#         from_email=settings.DEFAULT_FROM_EMAIL,
#         to_emails=to_email,
#         subject=subject,
#         html_content=html_content,
#     )
#     try:
#         sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
#         sg.send(message)
#     except Exception as e:
#         logger.error(f"SendGrid error: {e}")


# @shared_task
# def send_booking_confirmation_email(booking_id):
#     """Sends booking confirmation email to customer."""
#     from apps.bookings.models import Booking
#     booking = Booking.objects.prefetch_related('items__activity', 'items__slot').get(id=booking_id)

#     items_html = ""
#     for item in booking.items.all():
#         items_html += f"""
#         <tr>
#             <td>{item.activity.name}</td>
#             <td>{item.visit_date}</td>
#             <td>{item.slot.label}</td>
#             <td>{item.num_persons}</td>
#             <td>₹{item.price_snapshot}</td>
#         </tr>"""

#     html = f"""
#     <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;">
#         <h2 style="color:#2d7a4f;">🌿 Booking Confirmed — Mangrove Spot</h2>
#         <p>Hi {booking.customer_name},</p>
#         <p>Your booking is confirmed! Reference: <strong>{booking.reference}</strong></p>
#         <table border="1" cellpadding="8" style="border-collapse:collapse;width:100%;">
#             <tr style="background:#2d7a4f;color:white;">
#                 <th>Activity</th><th>Date</th><th>Time</th><th>Persons</th><th>Amount</th>
#             </tr>
#             {items_html}
#         </table>
#         <p style="font-size:1.2em;"><strong>Total Paid: ₹{booking.grand_total}</strong></p>
#         <p>📍 Nedungolam, Paravur, Kollam, Kerala 691334</p>
#         <p>📞 9496141619</p>
#         <p style="color:#666;">Questions? Reply to this email or call us.</p>
#     </div>
#     """
#     _send_email(booking.customer_email, f"Booking Confirmed — {booking.reference}", html)


# @shared_task
# def send_owner_new_booking_alert(booking_id):
#     """Sends new booking alert to owner."""
#     from apps.bookings.models import Booking
#     booking = Booking.objects.prefetch_related('items__activity').get(id=booking_id)

#     admin_url = f"{settings.FRONTEND_URL}/admin/bookings/{booking.reference}"
#     html = f"""
#     <div style="font-family:Arial,sans-serif;">
#         <h2>🔔 New Booking — {booking.reference}</h2>
#         <p><strong>Customer:</strong> {booking.customer_name}</p>
#         <p><strong>Phone:</strong> {booking.customer_phone}</p>
#         <p><strong>Email:</strong> {booking.customer_email}</p>
#         <p><strong>Total:</strong> ₹{booking.grand_total}</p>
#         <p><a href="{admin_url}">View in Admin Panel</a></p>
#     </div>
#     """
#     _send_email(settings.ADMIN_EMAIL, f"New Booking: {booking.reference}", html)


# @shared_task
# def send_cancellation_email(booking_id):
#     """Sends cancellation email to customer."""
#     from apps.bookings.models import Booking
#     booking = Booking.objects.get(id=booking_id)
#     html = f"""
#     <div style="font-family:Arial,sans-serif;">
#         <h2 style="color:#d9534f;">Booking Cancelled — {booking.reference}</h2>
#         <p>Hi {booking.customer_name},</p>
#         <p>Your booking <strong>{booking.reference}</strong> has been cancelled.</p>
#         <p>Refund of <strong>₹{booking.grand_total}</strong> will be processed in 3–5 business days.</p>
#         <p>📞 9496141619 | mangrovespot.care@gmail.com</p>
#     </div>
#     """
#     _send_email(booking.customer_email, f"Booking Cancelled — {booking.reference}", html)


# @shared_task
# def release_expired_slot_holds():
#     """
#     Celery Beat task — runs every 5 minutes.
#     Releases slot holds for pending bookings past their 15-min hold window.
#     """
#     from apps.bookings.models import Booking
#     from django.utils import timezone
#     expired = Booking.objects.filter(
#         status='pending',
#         items__slot_hold_expires__lt=timezone.now()
#     ).distinct()
#     count = expired.count()
#     expired.update(status='expired')
#     logger.info(f"Released {count} expired slot holds")
#     return count


# @shared_task
# def send_24hr_reminders():
#     """
#     Celery Beat task — runs daily at 8 PM IST.
#     Sends reminder emails for tomorrow's activities.
#     """
#     from apps.bookings.models import BookingItem
#     from datetime import date, timedelta
#     tomorrow = date.today() + timedelta(days=1)
#     items = BookingItem.objects.filter(
#         visit_date=tomorrow,
#         booking__status='confirmed'
#     ).select_related('booking', 'activity', 'slot')
#     for item in items:
#         html = f"""
#         <div style="font-family:Arial,sans-serif;">
#             <h2 style="color:#2d7a4f;">⏰ Reminder — Tomorrow at Mangrove Spot</h2>
#             <p>Hi {item.booking.customer_name},</p>
#             <p>Reminder: <strong>{item.activity.name}</strong> tomorrow at <strong>{item.slot.label}</strong></p>
#             <p>📍 Nedungolam, Paravur, Kollam, Kerala</p>
#             <p>What to bring: Comfortable clothes, water, sunscreen.</p>
#             <p>📞 9496141619</p>
#         </div>
#         """
#         _send_email(item.booking.customer_email, f"Reminder: {item.activity.name} tomorrow!", html)




from celery import shared_task
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def _send_email(to_email: str, subject: str, html_content: str):
    try:
        from django.core.mail import send_mail
        send_mail(
            subject=subject,
            message="Please view this email in an HTML-compatible client.",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[to_email],
            html_message=html_content,
            fail_silently=False,
        )
    except Exception as e:
        logger.error("Email send error: %s", e)


def _time_label(item) -> str:
    if item.slot:
        return item.slot.label
    if item.arrival_time:
        return item.arrival_time.strftime('%I:%M %p')
    return '—'


def _persons_label(item) -> str:
    label = f"{item.num_adults}A"
    if item.num_children:
        label += f" + {item.num_children}C"
    return label


# ─────────────────────────────────────────────────────────────────────────────
# NEW: single task that fires BOTH customer + owner emails after payment.
# Call this everywhere instead of calling the two tasks separately.
#
# Usage:
#   send_confirmation_emails.delay(booking_id)   ← Celery (preferred)
#   send_confirmation_emails(booking_id)          ← direct call (fallback)
# ─────────────────────────────────────────────────────────────────────────────
@shared_task
def send_confirmation_emails(booking_id: int):
    """
    Fires immediately after payment is confirmed.
    Sends:
      1. Customer confirmation (booking reference, payment split, venue info)
      2. Owner new-booking alert (customer details, admin link)
    Both emails use the same DB fetch to keep it to one query.
    """
    from apps.bookings.models import Booking

    try:
        booking = Booking.objects.prefetch_related(
            'items__activity', 'items__slot'
        ).get(id=booking_id)
    except Booking.DoesNotExist:
        logger.error("send_confirmation_emails: booking %s not found", booking_id)
        return

    # ── Build activity rows (shared by both emails) ───────────────
    customer_rows = ""
    owner_rows    = ""
    for item in booking.items.all():
        name  = item.activity.name
        date  = str(item.visit_date)
        time  = _time_label(item)
        pax   = _persons_label(item)
        price = f"₹{float(item.price_snapshot):,.0f}"

        customer_rows += f"""
        <tr>
          <td style="padding:8px;border:1px solid #ddd">{name}</td>
          <td style="padding:8px;border:1px solid #ddd">{date}</td>
          <td style="padding:8px;border:1px solid #ddd">{time}</td>
          <td style="padding:8px;border:1px solid #ddd">{pax}</td>
          <td style="padding:8px;border:1px solid #ddd;text-align:right">{price}</td>
        </tr>"""

        owner_rows += f"""
        <tr>
          <td style="padding:6px;border:1px solid #ddd">{name}</td>
          <td style="padding:6px;border:1px solid #ddd">{date}</td>
          <td style="padding:6px;border:1px solid #ddd">{time}</td>
          <td style="padding:6px;border:1px solid #ddd">{pax}</td>
          <td style="padding:6px;border:1px solid #ddd;text-align:right">{price}</td>
        </tr>"""

    grand_total = float(booking.grand_total)
    amount_paid = float(booking.amount_paid)
    balance_due = float(booking.balance_due)

    # ── 1. Customer confirmation email ────────────────────────────
    customer_html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:24px;">
      <h2 style="color:#2d7a4f;margin-bottom:4px;">🌿 Booking Confirmed — MangroveSpot</h2>
      <p style="color:#888;font-size:13px;margin-top:0;">Paravur, Kollam, Kerala</p>

      <p>Hi <strong>{booking.customer_name}</strong>,</p>
      <p>Your booking is confirmed! Reference:
        <strong style="color:#2d7a4f;">{booking.reference}</strong>
      </p>

      <table style="border-collapse:collapse;width:100%;margin:16px 0;">
        <tr style="background:#2d7a4f;color:white;">
          <th style="padding:8px;text-align:left">Activity</th>
          <th style="padding:8px;text-align:left">Date</th>
          <th style="padding:8px;text-align:left">Time</th>
          <th style="padding:8px;text-align:left">Guests</th>
          <th style="padding:8px;text-align:right">Amount</th>
        </tr>
        {customer_rows}
        <tr style="background:#f5f5f5;">
          <td colspan="4" style="padding:8px;font-weight:bold;text-align:right;border:1px solid #ddd;">
            Total booking value
          </td>
          <td style="padding:8px;font-weight:bold;text-align:right;border:1px solid #ddd;">
            ₹{grand_total:,.0f}
          </td>
        </tr>
      </table>

      <div style="background:#f0faf4;border:1px solid #b2dfdb;border-radius:8px;padding:16px;margin:16px 0;">
        <p style="margin:0 0 10px;font-weight:bold;color:#2d7a4f;">Payment Summary</p>
        <table style="width:100%;border-collapse:collapse;">
          <tr>
            <td style="padding:5px 0;color:#444;">✅ Paid online (50%)</td>
            <td style="padding:5px 0;text-align:right;font-weight:bold;color:#2d7a4f;">
              ₹{amount_paid:,.0f}
            </td>
          </tr>
          <tr>
            <td style="padding:5px 0;color:#444;border-top:1px solid #ddd;">
              ⏳ Balance due at arrival (50%)
            </td>
            <td style="padding:5px 0;text-align:right;font-weight:bold;color:#e65100;border-top:1px solid #ddd;">
              ₹{balance_due:,.0f}
            </td>
          </tr>
        </table>
      </div>

      <div style="background:#fff3e0;border-left:4px solid #e65100;padding:10px 14px;
                  border-radius:4px;margin-bottom:16px;">
        <p style="margin:0;color:#444;font-size:13px;">
          Please carry <strong>₹{balance_due:,.0f}</strong> in cash to pay at the venue on arrival.
        </p>
      </div>

      <p>📍 Nedungolam, Paravur, Kollam, Kerala 691334</p>
      <p>📞 9496141619</p>
      <p style="color:#888;font-size:12px;">
        Questions? Reply to this email or contact us at mangrovespot.care@gmail.com
      </p>
    </div>
    """

    _send_email(
        booking.customer_email,
        f"Booking Confirmed — {booking.reference}",
        customer_html,
    )
    logger.info("Confirmation email sent to %s for booking %s", booking.customer_email, booking.reference)

    # ── 2. Owner alert email ──────────────────────────────────────
    admin_url = f"{settings.FRONTEND_URL}/admin/bookings/{booking.id}"

    owner_html = f"""
    <div style="font-family:Arial,sans-serif;padding:20px;max-width:600px;">
      <h2 style="color:#2d7a4f;">🔔 New Booking — {booking.reference}</h2>

      <table style="border-collapse:collapse;width:100%;margin-bottom:16px;">
        <tr><td style="padding:5px;color:#555;width:140px;">Customer</td>
            <td style="padding:5px;font-weight:bold;">{booking.customer_name}</td></tr>
        <tr><td style="padding:5px;color:#555;">Phone</td>
            <td style="padding:5px;">{booking.customer_phone}</td></tr>
        <tr><td style="padding:5px;color:#555;">Email</td>
            <td style="padding:5px;">{booking.customer_email}</td></tr>
        <tr><td style="padding:5px;color:#555;">Amount paid</td>
            <td style="padding:5px;color:#2d7a4f;font-weight:bold;">₹{amount_paid:,.0f}</td></tr>
        <tr><td style="padding:5px;color:#555;">Balance at arrival</td>
            <td style="padding:5px;color:#e65100;font-weight:bold;">₹{balance_due:,.0f}</td></tr>
        <tr><td style="padding:5px;color:#555;">Grand total</td>
            <td style="padding:5px;font-weight:bold;">₹{grand_total:,.0f}</td></tr>
      </table>

      <table style="border-collapse:collapse;width:100%;margin:12px 0;">
        <tr style="background:#2d7a4f;color:white;">
          <th style="padding:6px;text-align:left">Activity</th>
          <th style="padding:6px;text-align:left">Date</th>
          <th style="padding:6px;text-align:left">Time</th>
          <th style="padding:6px;text-align:left">Guests</th>
          <th style="padding:6px;text-align:right">Amount</th>
        </tr>
        {owner_rows}
      </table>

      <a href="{admin_url}"
         style="display:inline-block;background:#2d7a4f;color:white;padding:10px 20px;
                text-decoration:none;border-radius:6px;margin-top:8px;">
        View in Admin Panel →
      </a>
    </div>
    """

    owner_email = getattr(settings, 'ADMIN_EMAIL', settings.EMAIL_HOST_USER)
    _send_email(
        owner_email,
        f"New Booking: {booking.reference} — ₹{grand_total:,.0f}",
        owner_html,
    )
    logger.info("Owner alert sent for booking %s", booking.reference)


# ─────────────────────────────────────────────────────────────────────────────
# Keep the old task name working so nothing else breaks.
# It just calls the new combined task.
# ─────────────────────────────────────────────────────────────────────────────
@shared_task
def send_booking_confirmation_email(booking_id: int):
    """Backward-compat alias → delegates to send_confirmation_emails."""
    send_confirmation_emails(booking_id)


@shared_task
def send_owner_new_booking_alert(booking_id: int):
    """Backward-compat alias → no-op now, owner alert is in send_confirmation_emails."""
    pass


@shared_task
def send_cancellation_email(booking_id: int):
    """Cancellation email to customer."""
    from apps.bookings.models import Booking
    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        logger.error("send_cancellation_email: booking %s not found", booking_id)
        return

    html = f"""
    <div style="font-family:Arial,sans-serif;padding:20px;">
      <h2 style="color:#d9534f;">Booking Cancelled — {booking.reference}</h2>
      <p>Hi {booking.customer_name},</p>
      <p>Your booking <strong>{booking.reference}</strong> has been cancelled.</p>
      <p>Refund of <strong>₹{float(booking.amount_paid):,.0f}</strong>
         will be processed in 3–5 business days.</p>
      <p>📞 9496141619 | mangrovespot.care@gmail.com</p>
    </div>
    """
    _send_email(
        booking.customer_email,
        f"Booking Cancelled — {booking.reference}",
        html,
    )


@shared_task
def release_expired_slot_holds():
    """Celery Beat — every 5 minutes. Expires pending bookings past hold window."""
    from apps.bookings.models import Booking
    from django.utils import timezone
    expired = Booking.objects.filter(
        status='pending',
        items__slot_hold_expires__lt=timezone.now(),
    ).distinct()
    count = expired.count()
    expired.update(status='expired')
    logger.info("Released %d expired slot holds", count)
    return count


@shared_task
def send_24hr_reminders():
    """Celery Beat — daily at 8 PM IST. Reminder emails for tomorrow's bookings."""
    from apps.bookings.models import BookingItem
    from datetime import date, timedelta
    tomorrow = date.today() + timedelta(days=1)
    items = BookingItem.objects.filter(
        visit_date=tomorrow,
        booking__status='confirmed',
    ).select_related('booking', 'activity', 'slot')

    for item in items:
        time_str = _time_label(item)
        html = f"""
        <div style="font-family:Arial,sans-serif;padding:20px;">
          <h2 style="color:#2d7a4f;">⏰ Reminder — Tomorrow at MangroveSpot</h2>
          <p>Hi {item.booking.customer_name},</p>
          <p>Reminder: <strong>{item.activity.name}</strong> tomorrow at <strong>{time_str}</strong></p>
          <p>📍 Nedungolam, Paravur, Kollam, Kerala</p>
          <p>Bring: comfortable clothes, water, sunscreen.</p>
          <p>📞 9496141619</p>
        </div>
        """
        _send_email(
            item.booking.customer_email,
            f"Reminder: {item.activity.name} tomorrow!",
            html,
        )