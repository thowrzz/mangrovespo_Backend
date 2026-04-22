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



"""
apps/notifications/tasks.py

All email tasks.  Key reliability settings on every task:
  bind=True               — access self.request.retries for back-off
  acks_late=True          — task stays in queue until it SUCCEEDS
                            (if worker crashes mid-send, it requeues)
  reject_on_worker_lost=True — requeue if worker process is killed
  max_retries=5           — give up after 5 failures (don't loop forever)
  Exponential back-off    — 10s, 20s, 40s, 80s, 160s between retries
                            covers Gmail rate limits and SMTP blips

The main task is send_confirmation_emails() — call this after payment.
It sends BOTH the customer confirmation AND the owner alert in one shot,
using a single DB query for both, so there's no extra DB overhead.
"""

import logging
from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


# ── Internal helpers ──────────────────────────────────────────────

def _slot_label(item) -> str:
    if item.slot:
        return item.slot.label
    if item.arrival_time:
        return item.arrival_time.strftime("%I:%M %p")
    return "—"


def _guests_label(item) -> str:
    label = f"{item.num_adults} Adult{'s' if item.num_adults != 1 else ''}"
    if item.num_children:
        label += f", {item.num_children} Child{'ren' if item.num_children != 1 else ''}"
    return label


def _send(to: str, subject: str, html: str, from_label: str = "MangroveSpot Adventures"):
    """
    Send one email. Raises on failure so the Celery retry kicks in.
    Never silently swallows errors.
    """
    msg = EmailMultiAlternatives(
        subject    = subject,
        body       = _strip_tags(html),
        from_email = f"{from_label} <{settings.DEFAULT_FROM_EMAIL}>",
        to         = [to],
        reply_to   = [getattr(settings, "ADMIN_EMAIL", settings.DEFAULT_FROM_EMAIL)],
    )
    msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=False)   # raises smtplib.SMTPException on failure


def _strip_tags(html: str) -> str:
    """Minimal HTML→plain-text for the text/plain part."""
    import re
    return re.sub(r"<[^>]+>", " ", html).strip()


# ─────────────────────────────────────────────────────────────────
# MAIN TASK: send_confirmation_emails
# ─────────────────────────────────────────────────────────────────

@shared_task(
    bind                  = True,
    acks_late             = True,           # don't ack until task succeeds
    reject_on_worker_lost = True,           # requeue if worker dies
    max_retries           = 5,
    name                  = "notifications.send_confirmation_emails",
)
def send_confirmation_emails(self, booking_id: int):
    """
    Sends two emails after a confirmed payment:
      1. Customer confirmation (reference, payment split, venue info)
      2. Owner/admin new-booking alert

    Both use one DB fetch. If SMTP fails, retries up to 5 times
    with exponential back-off (10s → 20s → 40s → 80s → 160s).

    Called from payments/views.py via transaction.on_commit() so
    it only runs after booking.status = 'confirmed' is committed.
    """
    from apps.bookings.models import Booking

    # ── Fetch booking ─────────────────────────────────────────────
    try:
        booking = Booking.objects.prefetch_related(
            "items__activity", "items__slot"
        ).get(pk=booking_id)
    except Booking.DoesNotExist:
        # Booking was deleted — nothing to send, don't retry
        logger.error(
            "send_confirmation_emails: booking %s not found — aborting",
            booking_id,
        )
        return

    # ── Guard: only email confirmed bookings ──────────────────────
    if booking.status not in ("confirmed", "completed"):
        logger.warning(
            "send_confirmation_emails: booking %s status='%s' — "
            "expected confirmed, skipping",
            booking.reference, booking.status,
        )
        return

    # ── Build shared activity rows ────────────────────────────────
    items        = list(booking.items.select_related("activity", "slot").all())
    grand_total  = float(booking.grand_total)
    amount_paid  = float(booking.amount_paid)
    balance_due  = float(booking.balance_due)
    frontend_url = getattr(settings, "FRONTEND_URL", "https://mangrovespot.in")
    admin_email  = getattr(settings, "ADMIN_EMAIL", settings.DEFAULT_FROM_EMAIL)

    table_rows_html = ""
    for item in items:
        table_rows_html += f"""
        <tr>
          <td style="padding:9px 12px;border-bottom:1px solid #f0f0f0;">{item.activity.name}</td>
          <td style="padding:9px 12px;border-bottom:1px solid #f0f0f0;">{item.visit_date}</td>
          <td style="padding:9px 12px;border-bottom:1px solid #f0f0f0;">{_slot_label(item)}</td>
          <td style="padding:9px 12px;border-bottom:1px solid #f0f0f0;">{_guests_label(item)}</td>
          <td style="padding:9px 12px;border-bottom:1px solid #f0f0f0;text-align:right;font-weight:600;">
            ₹{float(item.price_snapshot):,.0f}
          </td>
        </tr>"""

    # ── 1. Customer confirmation email ────────────────────────────
    customer_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Booking Confirmed — {booking.reference}</title>
</head>
<body style="margin:0;padding:0;background:#f4f7f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<div style="max-width:600px;margin:24px auto;padding:0 16px;">
<div style="background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">

  <!-- Header -->
  <div style="background:#16a34a;padding:32px;text-align:center;">
    <div style="font-size:40px;margin-bottom:12px;">🌿</div>
    <h1 style="color:#fff;font-size:22px;font-weight:700;margin:0 0 6px;">Booking Confirmed!</h1>
    <p style="color:rgba(255,255,255,0.85);font-size:14px;margin:0;">MangroveSpot Adventures · Paravur, Kerala</p>
  </div>

  <!-- Reference -->
  <div style="background:#f0fdf4;border-bottom:1px solid #dcfce7;padding:20px 32px;text-align:center;">
    <p style="font-size:11px;text-transform:uppercase;letter-spacing:0.08em;color:#6b7280;margin:0 0 8px;">
      Booking Reference
    </p>
    <p style="font-size:30px;font-weight:800;color:#16a34a;letter-spacing:0.12em;
              font-family:'Courier New',monospace;margin:0 0 6px;">
      {booking.reference}
    </p>
    <p style="font-size:12px;color:#6b7280;margin:0;">Show this code at the venue entrance</p>
  </div>

  <!-- Body -->
  <div style="padding:28px 32px;">

    <p style="font-size:15px;color:#1a1a1a;margin:0 0 20px;">
      Hi <strong style="color:#16a34a;">{booking.customer_name}</strong>,<br>
      Your booking is confirmed and your 50% advance payment has been received.
      See you soon!
    </p>

    <!-- Activities table -->
    <p style="font-size:11px;text-transform:uppercase;letter-spacing:0.08em;
              color:#9ca3af;margin:0 0 12px;">Activities Booked</p>
    <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
      <thead>
        <tr style="background:#f9fafb;">
          <th style="padding:9px 12px;text-align:left;font-size:11px;color:#6b7280;font-weight:600;">Activity</th>
          <th style="padding:9px 12px;text-align:left;font-size:11px;color:#6b7280;font-weight:600;">Date</th>
          <th style="padding:9px 12px;text-align:left;font-size:11px;color:#6b7280;font-weight:600;">Time</th>
          <th style="padding:9px 12px;text-align:left;font-size:11px;color:#6b7280;font-weight:600;">Guests</th>
          <th style="padding:9px 12px;text-align:right;font-size:11px;color:#6b7280;font-weight:600;">Amount</th>
        </tr>
      </thead>
      <tbody>{table_rows_html}</tbody>
    </table>

    <!-- Payment summary -->
    <p style="font-size:11px;text-transform:uppercase;letter-spacing:0.08em;
              color:#9ca3af;margin:0 0 12px;">Payment Summary</p>
    <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:12px;padding:16px 20px;margin-bottom:16px;">
      <div style="display:flex;justify-content:space-between;padding:6px 0;font-size:14px;">
        <span style="color:#6b7280;">Total booking value</span>
        <span style="font-weight:600;color:#1a1a1a;">₹{grand_total:,.0f}</span>
      </div>
      <div style="display:flex;justify-content:space-between;padding:6px 0;font-size:14px;
                  border-top:1px solid #e5e7eb;margin-top:4px;">
        <span style="color:#6b7280;">✅ Paid online (50% advance)</span>
        <span style="font-weight:700;color:#16a34a;">₹{amount_paid:,.0f}</span>
      </div>
      <div style="display:flex;justify-content:space-between;padding:6px 0;font-size:14px;">
        <span style="color:#6b7280;">⏳ Balance due at arrival (50%)</span>
        <span style="font-weight:700;color:#d97706;">₹{balance_due:,.0f}</span>
      </div>
    </div>

    <!-- Balance reminder -->
    <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:10px;
                padding:12px 16px;margin-bottom:24px;">
      <p style="margin:0;color:#92400e;font-size:13px;">
        🏕&nbsp; Please carry <strong>₹{balance_due:,.0f}</strong> in cash or UPI
        to pay at the venue on arrival.
      </p>
    </div>

    <!-- Venue info -->
    <div style="border-top:1px solid #f3f4f6;padding-top:16px;font-size:13px;color:#6b7280;line-height:1.8;">
      <p style="margin:0;">📍 Nedungolam, Paravur, Kollam, Kerala 691334</p>
      <p style="margin:0;">📞 9496141619</p>
      <p style="margin:0;">✉️ mangrovespot.care@gmail.com</p>
    </div>

    <!-- CTA -->
    <div style="text-align:center;margin-top:24px;">
      <a href="{frontend_url}/my-bookings"
         style="display:inline-block;background:#16a34a;color:#fff;text-decoration:none;
                font-weight:700;font-size:14px;padding:14px 32px;border-radius:10px;">
        View My Booking →
      </a>
    </div>

  </div><!-- /body -->

  <!-- Footer -->
  <div style="padding:16px 32px;border-top:1px solid #f3f4f6;text-align:center;">
    <p style="font-size:11px;color:#9ca3af;margin:0;">
      This confirmation was sent to {booking.customer_email}.<br>
      <strong>MangroveSpot Adventures</strong> · Paravur, Kerala, India
    </p>
  </div>

</div><!-- /card -->
</div><!-- /wrapper -->
</body>
</html>"""

    try:
        _send(
            to      = booking.customer_email,
            subject = f"Booking Confirmed — {booking.reference} | MangroveSpot Adventures",
            html    = customer_html,
        )
        logger.info(
            "Customer confirmation email sent to %s for booking %s",
            booking.customer_email, booking.reference,
        )
    except Exception as exc:
        # Retry the whole task — both emails will resend on retry.
        # That's fine because customers don't mind getting two confirmations;
        # they mind NOT getting one.
        retry_num = self.request.retries
        countdown = 10 * (2 ** retry_num)   # 10s, 20s, 40s, 80s, 160s
        logger.warning(
            "send_confirmation_emails: customer email attempt %d failed "
            "for booking %s — retrying in %ds. Error: %s",
            retry_num + 1, booking.reference, countdown, exc,
        )
        raise self.retry(exc=exc, countdown=countdown)

    # ── 2. Owner/admin alert email ────────────────────────────────
    admin_rows_html = ""
    for item in items:
        admin_rows_html += f"""
        <tr>
          <td style="padding:7px 10px;border-bottom:1px solid #f0f0f0;">{item.activity.name}</td>
          <td style="padding:7px 10px;border-bottom:1px solid #f0f0f0;">{item.visit_date}</td>
          <td style="padding:7px 10px;border-bottom:1px solid #f0f0f0;">{_slot_label(item)}</td>
          <td style="padding:7px 10px;border-bottom:1px solid #f0f0f0;">{_guests_label(item)}</td>
          <td style="padding:7px 10px;border-bottom:1px solid #f0f0f0;text-align:right;font-weight:600;">
            ₹{float(item.price_snapshot):,.0f}
          </td>
        </tr>"""

    admin_panel_url = f"{frontend_url}/admin/bookings/{booking.pk}"

    owner_html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><title>New Booking — {booking.reference}</title></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
             background:#f4f7f6;margin:0;padding:0;">
<div style="max-width:600px;margin:24px auto;padding:0 16px;">
<div style="background:#fff;border-radius:16px;padding:28px 32px;
            box-shadow:0 2px 12px rgba(0,0,0,0.08);">

  <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">
    <div style="background:#16a34a;border-radius:10px;padding:10px;font-size:20px;">🔔</div>
    <div>
      <h2 style="margin:0;font-size:18px;color:#1a1a1a;">New Confirmed Booking</h2>
      <p style="margin:0;font-size:13px;color:#6b7280;">Reference: <strong>{booking.reference}</strong></p>
    </div>
  </div>

  <!-- Customer details -->
  <table style="width:100%;border-collapse:collapse;margin-bottom:20px;
                background:#f9fafb;border-radius:10px;overflow:hidden;">
    <tr>
      <td style="padding:9px 14px;color:#6b7280;font-size:13px;width:130px;">Customer</td>
      <td style="padding:9px 14px;font-weight:600;font-size:13px;">{booking.customer_name}</td>
    </tr>
    <tr>
      <td style="padding:9px 14px;color:#6b7280;font-size:13px;">Phone</td>
      <td style="padding:9px 14px;font-size:13px;">{booking.customer_phone}</td>
    </tr>
    <tr>
      <td style="padding:9px 14px;color:#6b7280;font-size:13px;">Email</td>
      <td style="padding:9px 14px;font-size:13px;">{booking.customer_email}</td>
    </tr>
    <tr>
      <td style="padding:9px 14px;color:#6b7280;font-size:13px;">Paid now</td>
      <td style="padding:9px 14px;font-weight:700;color:#16a34a;font-size:14px;">
        ₹{amount_paid:,.0f}
      </td>
    </tr>
    <tr>
      <td style="padding:9px 14px;color:#6b7280;font-size:13px;">Balance at arrival</td>
      <td style="padding:9px 14px;font-weight:700;color:#d97706;font-size:14px;">
        ₹{balance_due:,.0f}
      </td>
    </tr>
    <tr>
      <td style="padding:9px 14px;color:#6b7280;font-size:13px;">Grand total</td>
      <td style="padding:9px 14px;font-weight:700;font-size:14px;">₹{grand_total:,.0f}</td>
    </tr>
  </table>

  <!-- Activities -->
  <table style="width:100%;border-collapse:collapse;margin-bottom:20px;">
    <thead>
      <tr style="background:#16a34a;color:#fff;">
        <th style="padding:9px 10px;text-align:left;font-size:12px;">Activity</th>
        <th style="padding:9px 10px;text-align:left;font-size:12px;">Date</th>
        <th style="padding:9px 10px;text-align:left;font-size:12px;">Time</th>
        <th style="padding:9px 10px;text-align:left;font-size:12px;">Guests</th>
        <th style="padding:9px 10px;text-align:right;font-size:12px;">Amount</th>
      </tr>
    </thead>
    <tbody>{admin_rows_html}</tbody>
  </table>

  <a href="{admin_panel_url}"
     style="display:inline-block;background:#16a34a;color:#fff;text-decoration:none;
            font-weight:700;font-size:13px;padding:12px 24px;border-radius:8px;">
    Open in Admin Panel →
  </a>

</div>
</div>
</body>
</html>"""

    try:
        _send(
            to      = admin_email,
            subject = f"[MangroveSpot] New Booking {booking.reference} — ₹{grand_total:,.0f}",
            html    = owner_html,
        )
        logger.info("Owner alert sent for booking %s", booking.reference)
    except Exception as exc:
        # Don't retry the whole task for the admin email — customer already got theirs.
        # Just log it. Admin can check the dashboard.
        logger.error(
            "Owner alert failed for booking %s (customer email already sent): %s",
            booking.reference, exc,
        )


# ─────────────────────────────────────────────────────────────────
# CANCELLATION EMAIL
# ─────────────────────────────────────────────────────────────────

@shared_task(
    bind                  = True,
    acks_late             = True,
    reject_on_worker_lost = True,
    max_retries           = 4,
    name                  = "notifications.send_cancellation_email",
)
def send_cancellation_email(self, booking_id: int):
    """Customer cancellation notification with retry."""
    from apps.bookings.models import Booking

    try:
        booking = Booking.objects.get(pk=booking_id)
    except Booking.DoesNotExist:
        logger.error("send_cancellation_email: booking %s not found", booking_id)
        return

    frontend_url = getattr(settings, "FRONTEND_URL", "https://mangrovespot.in")
    admin_email  = getattr(settings, "ADMIN_EMAIL", settings.DEFAULT_FROM_EMAIL)
    amount_paid  = float(booking.amount_paid)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
             background:#f4f7f6;margin:0;padding:0;">
<div style="max-width:600px;margin:24px auto;padding:0 16px;">
<div style="background:#fff;border-radius:16px;overflow:hidden;
            box-shadow:0 2px 12px rgba(0,0,0,0.08);">
  <div style="background:#dc2626;padding:28px 32px;text-align:center;">
    <div style="font-size:36px;margin-bottom:10px;">❌</div>
    <h2 style="color:#fff;margin:0;font-size:20px;">Booking Cancelled</h2>
  </div>
  <div style="padding:28px 32px;">
    <p style="font-size:13px;color:#6b7280;margin:0 0 4px;">Booking Reference</p>
    <p style="font-size:22px;font-weight:700;color:#dc2626;font-family:monospace;
              letter-spacing:0.1em;margin:0 0 20px;">{booking.reference}</p>
    <p style="font-size:15px;color:#1a1a1a;">
      Hi {booking.customer_name},<br><br>
      Your booking has been cancelled. If a refund is applicable, it will be
      processed to your original payment method within 5–7 business days.
    </p>
    <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;
                padding:14px 18px;margin-top:16px;font-size:13px;color:#6b7280;">
      Questions? Contact us at
      <a href="mailto:{admin_email}" style="color:#16a34a;">{admin_email}</a>
      or call 9496141619.
    </div>
    <div style="text-align:center;margin-top:20px;">
      <a href="{frontend_url}"
         style="display:inline-block;background:#16a34a;color:#fff;text-decoration:none;
                font-weight:700;font-size:13px;padding:12px 24px;border-radius:8px;">
        Book Again →
      </a>
    </div>
  </div>
</div>
</div>
</body>
</html>"""

    try:
        _send(
            to      = booking.customer_email,
            subject = f"Booking Cancelled — {booking.reference} | MangroveSpot",
            html    = html,
        )
        logger.info(
            "Cancellation email sent to %s for booking %s",
            booking.customer_email, booking.reference,
        )
    except Exception as exc:
        countdown = 10 * (2 ** self.request.retries)
        logger.warning(
            "send_cancellation_email: attempt %d failed for booking %s "
            "— retrying in %ds. Error: %s",
            self.request.retries + 1, booking_id, countdown, exc,
        )
        raise self.retry(exc=exc, countdown=countdown)


# ─────────────────────────────────────────────────────────────────
# BACKWARD-COMPAT ALIASES
# Any existing code that calls these names still works.
# ─────────────────────────────────────────────────────────────────

@shared_task(name="notifications.send_booking_confirmation_email")
def send_booking_confirmation_email(booking_id: int):
    """Alias → delegates to send_confirmation_emails."""
    send_confirmation_emails(booking_id)


@shared_task(name="notifications.send_admin_booking_notification")
def send_admin_booking_notification(booking_id: int):
    """Alias → no-op (now handled inside send_confirmation_emails)."""
    pass


# ─────────────────────────────────────────────────────────────────
# PERIODIC TASKS (Celery Beat)
# ─────────────────────────────────────────────────────────────────

@shared_task(name="notifications.release_expired_slot_holds")
def release_expired_slot_holds():
    """Every 5 minutes via Celery Beat. Expires pending bookings past hold window."""
    from apps.bookings.models import Booking
    from django.utils import timezone

    expired = Booking.objects.filter(
        status="pending",
        items__slot_hold_expires__lt=timezone.now(),
    ).distinct()
    count = expired.count()
    expired.update(status="expired")
    logger.info("Released %d expired slot holds", count)
    return count


@shared_task(name="notifications.send_24hr_reminders")
def send_24hr_reminders():
    """Daily at 8 PM IST via Celery Beat. Reminder for tomorrow's bookings."""
    from apps.bookings.models import BookingItem
    from datetime import date, timedelta

    tomorrow = date.today() + timedelta(days=1)
    items = BookingItem.objects.filter(
        visit_date=tomorrow,
        booking__status="confirmed",
    ).select_related("booking", "activity", "slot")

    for item in items:
        time_str = _slot_label(item)
        html = f"""
        <div style="font-family:Arial,sans-serif;padding:20px;">
          <h2 style="color:#16a34a;">⏰ See You Tomorrow at MangroveSpot!</h2>
          <p>Hi {item.booking.customer_name},</p>
          <p>Reminder: <strong>{item.activity.name}</strong>
             tomorrow at <strong>{time_str}</strong></p>
          <p>📍 Nedungolam, Paravur, Kollam, Kerala</p>
          <p>Please bring comfortable clothes, water, and sunscreen.
             Carry <strong>₹{float(item.booking.balance_due):,.0f}</strong>
             to pay the remaining balance at the venue.</p>
          <p>📞 9496141619</p>
        </div>"""
        try:
            _send(
                to      = item.booking.customer_email,
                subject = f"See You Tomorrow — {item.activity.name} at MangroveSpot!",
                html    = html,
            )
        except Exception as exc:
            logger.error(
                "24h reminder failed for booking %s: %s",
                item.booking.reference, exc,
            )