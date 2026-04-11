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
        from django.conf import settings as s
        send_mail(
            subject=subject,
            message="Please view this email in an HTML-compatible client.",
            from_email=s.EMAIL_HOST_USER,
            recipient_list=[to_email],
            html_message=html_content,
            fail_silently=False,
        )
    except Exception as e:
        logger.error("Gmail SMTP error: %s", e)


# ── @shared_task functions can be called two ways: ────────────────
#   1. send_booking_confirmation_email.delay(id)  → Celery worker
#   2. send_booking_confirmation_email(id)         → direct call in thread
# Both work identically. The decorator adds .delay() / .apply_async()
# without changing how the function itself runs when called normally.


def _time_label(item) -> str:
    """Returns a human-readable time string for a booking item."""
    if item.slot:
        return item.slot.label
    if item.arrival_time:
        return item.arrival_time.strftime('%I:%M %p')
    return '—'


def _persons_label(item) -> str:
    """Returns a compact persons string, e.g. '2A' or '2A + 1C'."""
    label = f"{item.num_adults}A"
    if item.num_children:
        label += f" + {item.num_children}C"
    return label


# @shared_task
# def send_booking_confirmation_email(booking_id: int):
#     """Customer confirmation email."""
#     from apps.bookings.models import Booking
#     booking = Booking.objects.prefetch_related(
#         'items__activity', 'items__slot'
#     ).get(id=booking_id)

#     rows = ""
#     for item in booking.items.all():
#         rows += f"""
#         <tr>
#           <td style="padding:8px;border:1px solid #ddd">{item.activity.name}</td>
#           <td style="padding:8px;border:1px solid #ddd">{item.visit_date}</td>
#           <td style="padding:8px;border:1px solid #ddd">{_time_label(item)}</td>
#           <td style="padding:8px;border:1px solid #ddd">{_persons_label(item)}</td>
#           <td style="padding:8px;border:1px solid #ddd">₹{item.price_snapshot}</td>
#         </tr>"""

#     html = f"""
#     <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px;">
#       <h2 style="color:#2d7a4f;">🌿 Booking Confirmed — Mangrove Spot</h2>
#       <p>Hi {booking.customer_name},</p>
#       <p>Your booking is confirmed! Reference: <strong>{booking.reference}</strong></p>
#       <table style="border-collapse:collapse;width:100%;margin:16px 0;">
#         <tr style="background:#2d7a4f;color:white;">
#           <th style="padding:8px;text-align:left">Activity</th>
#           <th style="padding:8px;text-align:left">Date</th>
#           <th style="padding:8px;text-align:left">Time</th>
#           <th style="padding:8px;text-align:left">Persons</th>
#           <th style="padding:8px;text-align:left">Amount</th>
#         </tr>
#         {rows}
#       </table>
#       <p style="font-size:1.1em;"><strong>Total Paid: ₹{booking.grand_total}</strong></p>
#       <p>📍 Nedungolam, Paravur, Kollam, Kerala 691334</p>
#       <p>📞 9496141619</p>
#       <p style="color:#666;font-size:0.9em;">Questions? Reply to this email or call us.</p>
#     </div>
#     """
#     _send_email(
#         booking.customer_email,
#         f"Booking Confirmed — {booking.reference}",
#         html,
#     )
@shared_task
def send_booking_confirmation_email(booking_id: int):
    """Customer confirmation email with correct payment split."""
    from apps.bookings.models import Booking
    booking = Booking.objects.prefetch_related(
        'items__activity', 'items__slot'
    ).get(id=booking_id)

    rows = ""
    for item in booking.items.all():
        rows += f"""
        <tr>
          <td style="padding:8px;border:1px solid #ddd">{item.activity.name}</td>
          <td style="padding:8px;border:1px solid #ddd">{item.visit_date}</td>
          <td style="padding:8px;border:1px solid #ddd">{_time_label(item)}</td>
          <td style="padding:8px;border:1px solid #ddd">{_persons_label(item)}</td>
          <td style="padding:8px;border:1px solid #ddd;text-align:right;">
            ₹{float(item.price_snapshot):,.0f}
          </td>
        </tr>"""

    grand_total  = float(booking.grand_total)
    amount_paid  = float(booking.amount_paid)   # 50% charged online
    balance_due  = float(booking.balance_due)   # 50% due at arrival

    html = f"""
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
        {rows}
        <tr style="background:#f5f5f5;">
          <td colspan="4"
              style="padding:8px;font-weight:bold;text-align:right;border:1px solid #ddd;">
            Total Booking Value
          </td>
          <td style="padding:8px;font-weight:bold;text-align:right;border:1px solid #ddd;">
            ₹{grand_total:,.0f}
          </td>
        </tr>
      </table>

      <!-- Payment split -->
      <div style="background:#f0faf4;border:1px solid #b2dfdb;border-radius:8px;
                  padding:16px;margin:16px 0;">
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
            <td style="padding:5px 0;text-align:right;font-weight:bold;
                       color:#e65100;border-top:1px solid #ddd;">
              ₹{balance_due:,.0f}
            </td>
          </tr>
        </table>
      </div>

      <div style="background:#fff3e0;border-left:4px solid #e65100;
                  padding:10px 14px;border-radius:4px;margin-bottom:16px;">
        <p style="margin:0;color:#444;font-size:13px;">
          Please carry <strong>₹{balance_due:,.0f}</strong> to pay at the venue on arrival.
        </p>
      </div>

      <p>📍 Nedungolam, Paravur, Kollam, Kerala 691334</p>
      <p>📞 9496141619</p>
      <p style="color:#888;font-size:12px;">
        Questions? Reply to this email or call us at mangrovespot.care@gmail.com
      </p>
    </div>
    """
    _send_email(
        booking.customer_email,
        f"Booking Confirmed — {booking.reference}",
        html,
    )



@shared_task
def send_owner_new_booking_alert(booking_id: int):
    """New booking alert to owner."""
    from apps.bookings.models import Booking
    booking = Booking.objects.prefetch_related('items__activity').get(id=booking_id)

    rows = ""
    for item in booking.items.all():
        rows += f"""
        <tr>
          <td style="padding:6px;border:1px solid #ddd">{item.activity.name}</td>
          <td style="padding:6px;border:1px solid #ddd">{item.visit_date}</td>
          <td style="padding:6px;border:1px solid #ddd">{_persons_label(item)}</td>
          <td style="padding:6px;border:1px solid #ddd">₹{item.price_snapshot}</td>
        </tr>"""

    admin_url = f"{settings.FRONTEND_URL}/admin/bookings/{booking.id}"
    html = f"""
    <div style="font-family:Arial,sans-serif;padding:20px;">
      <h2>🔔 New Booking — {booking.reference}</h2>
      <p><strong>Customer:</strong> {booking.customer_name}</p>
      <p><strong>Phone:</strong> {booking.customer_phone}</p>
      <p><strong>Email:</strong> {booking.customer_email}</p>
      <table style="border-collapse:collapse;width:100%;margin:12px 0;">
        <tr style="background:#2d7a4f;color:white;">
          <th style="padding:6px;text-align:left">Activity</th>
          <th style="padding:6px;text-align:left">Date</th>
          <th style="padding:6px;text-align:left">Persons</th>
          <th style="padding:6px;text-align:left">Amount</th>
        </tr>
        {rows}
      </table>
      <p><strong>Total: ₹{booking.grand_total}</strong></p>
      <p><a href="{admin_url}" style="background:#2d7a4f;color:white;padding:8px 16px;text-decoration:none;border-radius:4px;">View in Admin Panel</a></p>
    </div>
    """
    _send_email(
        settings.ADMIN_EMAIL,
        f"New Booking: {booking.reference} — ₹{booking.grand_total}",
        html,
    )



@shared_task
def send_cancellation_email(booking_id: int):
    """Cancellation email to customer."""
    from apps.bookings.models import Booking
    booking = Booking.objects.get(id=booking_id)
    html = f"""
    <div style="font-family:Arial,sans-serif;padding:20px;">
      <h2 style="color:#d9534f;">Booking Cancelled — {booking.reference}</h2>
      <p>Hi {booking.customer_name},</p>
      <p>Your booking <strong>{booking.reference}</strong> has been cancelled.</p>
      <p>Refund of <strong>₹{booking.grand_total}</strong> will be processed in 3–5 business days.</p>
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
    """
    Celery Beat — every 5 minutes.
    Expires pending bookings past their hold window.
    """
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
    """
    Celery Beat — daily at 8 PM IST.
    Reminder emails for tomorrow's bookings.
    """
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
          <h2 style="color:#2d7a4f;">⏰ Reminder — Tomorrow at Mangrove Spot</h2>
          <p>Hi {item.booking.customer_name},</p>
          <p>Reminder: <strong>{item.activity.name}</strong> tomorrow at <strong>{time_str}</strong></p>
          <p>📍 Nedungolam, Paravur, Kollam, Kerala</p>
          <p>What to bring: comfortable clothes, water, sunscreen.</p>
          <p>📞 9496141619</p>
        </div>
        """
        _send_email(
            item.booking.customer_email,
            f"Reminder: {item.activity.name} tomorrow!",
            html,
        )