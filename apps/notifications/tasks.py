
"""
apps/notifications/tasks.py
"""
import logging
import re
from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


def _slot_label(item):
    if item.slot:
        return item.slot.label
    if item.arrival_time:
        return item.arrival_time.strftime("%I:%M %p")
    return "-"


def _guests_label(item):
    label = f"{item.num_adults} Adult{'s' if item.num_adults != 1 else ''}"
    if item.num_children:
        label += f", {item.num_children} Child{'ren' if item.num_children != 1 else ''}"
    return label


def _strip_tags(html):
    return re.sub(r"<[^>]+>", " ", html).strip()


def _send(to, subject, html):
    msg = EmailMultiAlternatives(
        subject=subject,
        body=_strip_tags(html),
        from_email=f"MangroveSpot Adventures <{settings.DEFAULT_FROM_EMAIL}>",
        to=[to],
        reply_to=[getattr(settings, "ADMIN_EMAIL", settings.DEFAULT_FROM_EMAIL)],
    )
    msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=False)


@shared_task(
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=5,
    name="notifications.send_confirmation_emails",
)
def send_confirmation_emails(self, booking_id):
    from apps.bookings.models import Booking
    try:
        booking = Booking.objects.prefetch_related(
            "items__activity", "items__slot"
        ).get(pk=booking_id)
    except Booking.DoesNotExist:
        logger.error("send_confirmation_emails: booking %s not found", booking_id)
        return

    if booking.status not in ("confirmed", "completed"):
        logger.warning("send_confirmation_emails: booking %s status=%s skipping", booking.reference, booking.status)
        return

    items = list(booking.items.select_related("activity", "slot").all())
    grand_total  = float(booking.grand_total)
    amount_paid  = float(booking.amount_paid)
    balance_due  = float(booking.balance_due)
    frontend_url = getattr(settings, "FRONTEND_URL", "https://mangrovespot.in")
    admin_email  = getattr(settings, "ADMIN_EMAIL", settings.DEFAULT_FROM_EMAIL)

    table_rows = ""
    for item in items:
        table_rows += (
            "<tr>"
            f"<td style='padding:9px 12px;border-bottom:1px solid #f0f0f0;'>{item.activity.name}</td>"
            f"<td style='padding:9px 12px;border-bottom:1px solid #f0f0f0;'>{item.visit_date}</td>"
            f"<td style='padding:9px 12px;border-bottom:1px solid #f0f0f0;'>{_slot_label(item)}</td>"
            f"<td style='padding:9px 12px;border-bottom:1px solid #f0f0f0;'>{_guests_label(item)}</td>"
            f"<td style='padding:9px 12px;border-bottom:1px solid #f0f0f0;text-align:right;font-weight:600;'>Rs.{float(item.price_snapshot):,.0f}</td>"
            "</tr>"
        )

    customer_html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#f4f7f6;font-family:Arial,sans-serif;">
<div style="max-width:600px;margin:24px auto;padding:0 16px;">
<div style="background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">
<div style="background:#16a34a;padding:32px;text-align:center;">
<div style="font-size:40px;margin-bottom:12px;">🌿</div>
<h1 style="color:#fff;font-size:22px;font-weight:700;margin:0 0 6px;">Booking Confirmed!</h1>
<p style="color:rgba(255,255,255,0.85);font-size:14px;margin:0;">MangroveSpot Adventures · Paravur, Kerala</p>
</div>
<div style="background:#f0fdf4;border-bottom:1px solid #dcfce7;padding:20px 32px;text-align:center;">
<p style="font-size:11px;color:#6b7280;margin:0 0 8px;">BOOKING REFERENCE</p>
<p style="font-size:30px;font-weight:800;color:#16a34a;font-family:monospace;margin:0 0 6px;">{booking.reference}</p>
<p style="font-size:12px;color:#6b7280;margin:0;">Show this code at the venue entrance</p>
</div>
<div style="padding:28px 32px;">
<p style="font-size:15px;color:#1a1a1a;margin:0 0 20px;">
Hi <strong style="color:#16a34a;">{booking.customer_name}</strong>,<br>
Your booking is confirmed and your 50% advance payment has been received. See you soon!
</p>
<table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
<thead><tr style="background:#f9fafb;">
<th style="padding:9px 12px;text-align:left;font-size:11px;color:#6b7280;">Activity</th>
<th style="padding:9px 12px;text-align:left;font-size:11px;color:#6b7280;">Date</th>
<th style="padding:9px 12px;text-align:left;font-size:11px;color:#6b7280;">Time</th>
<th style="padding:9px 12px;text-align:left;font-size:11px;color:#6b7280;">Guests</th>
<th style="padding:9px 12px;text-align:right;font-size:11px;color:#6b7280;">Amount</th>
</tr></thead>
<tbody>{table_rows}</tbody>
</table>
<div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:12px;padding:16px 20px;margin-bottom:16px;">
<p style="font-size:11px;color:#9ca3af;margin:0 0 10px;">PAYMENT SUMMARY</p>
<div style="display:flex;justify-content:space-between;padding:6px 0;font-size:14px;">
<span style="color:#6b7280;">Total booking value</span>
<span style="font-weight:600;">Rs.{grand_total:,.0f}</span>
</div>
<div style="display:flex;justify-content:space-between;padding:6px 0;font-size:14px;border-top:1px solid #e5e7eb;">
<span style="color:#6b7280;">Paid online (50%)</span>
<span style="font-weight:700;color:#16a34a;">Rs.{amount_paid:,.0f}</span>
</div>
<div style="display:flex;justify-content:space-between;padding:6px 0;font-size:14px;">
<span style="color:#6b7280;">Balance due at arrival (50%)</span>
<span style="font-weight:700;color:#d97706;">Rs.{balance_due:,.0f}</span>
</div>
</div>
<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:12px 16px;margin-bottom:24px;">
<p style="margin:0;color:#92400e;font-size:13px;">Please carry <strong>Rs.{balance_due:,.0f}</strong> cash/UPI to pay at the venue on arrival.</p>
</div>
<div style="border-top:1px solid #f3f4f6;padding-top:16px;font-size:13px;color:#6b7280;line-height:1.8;">
<p style="margin:0;">Location: Nedungolam, Paravur, Kollam, Kerala 691334</p>
<p style="margin:0;">Phone: 9496141619</p>
<p style="margin:0;">Email: mangrovespot.care@gmail.com</p>
</div>
</div>
<div style="padding:16px 32px;border-top:1px solid #f3f4f6;text-align:center;">
<p style="font-size:11px;color:#9ca3af;margin:0;">MangroveSpot Adventures · Paravur, Kerala, India</p>
</div>
</div></div></body></html>"""

    try:
        _send(
            to=booking.customer_email,
            subject=f"Booking Confirmed - {booking.reference} | MangroveSpot Adventures",
            html=customer_html,
        )
        logger.info("Customer confirmation email sent to %s for booking %s", booking.customer_email, booking.reference)
    except Exception as exc:
        countdown = 10 * (2 ** self.request.retries)
        logger.warning("Customer email failed for booking %s, retrying in %ds: %s", booking.reference, countdown, exc)
        raise self.retry(exc=exc, countdown=countdown)

    admin_rows = ""
    for item in items:
        admin_rows += (
            "<tr>"
            f"<td style='padding:7px 10px;border-bottom:1px solid #f0f0f0;'>{item.activity.name}</td>"
            f"<td style='padding:7px 10px;border-bottom:1px solid #f0f0f0;'>{item.visit_date}</td>"
            f"<td style='padding:7px 10px;border-bottom:1px solid #f0f0f0;'>{_slot_label(item)}</td>"
            f"<td style='padding:7px 10px;border-bottom:1px solid #f0f0f0;'>{_guests_label(item)}</td>"
            f"<td style='padding:7px 10px;border-bottom:1px solid #f0f0f0;text-align:right;font-weight:600;'>Rs.{float(item.price_snapshot):,.0f}</td>"
            "</tr>"
        )

    owner_html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"/></head>
<body style="font-family:Arial,sans-serif;background:#f4f7f6;margin:0;padding:0;">
<div style="max-width:600px;margin:24px auto;padding:0 16px;">
<div style="background:#fff;border-radius:16px;padding:28px 32px;box-shadow:0 2px 12px rgba(0,0,0,0.08);">
<h2 style="margin:0 0 4px;color:#1a1a1a;">New Confirmed Booking</h2>
<p style="margin:0 0 20px;color:#6b7280;">Reference: <strong>{booking.reference}</strong></p>
<table style="width:100%;border-collapse:collapse;margin-bottom:20px;background:#f9fafb;border-radius:10px;">
<tr><td style="padding:9px 14px;color:#6b7280;font-size:13px;width:130px;">Customer</td><td style="padding:9px 14px;font-weight:600;font-size:13px;">{booking.customer_name}</td></tr>
<tr><td style="padding:9px 14px;color:#6b7280;font-size:13px;">Phone</td><td style="padding:9px 14px;font-size:13px;">{booking.customer_phone}</td></tr>
<tr><td style="padding:9px 14px;color:#6b7280;font-size:13px;">Email</td><td style="padding:9px 14px;font-size:13px;">{booking.customer_email}</td></tr>
<tr><td style="padding:9px 14px;color:#6b7280;font-size:13px;">Paid now</td><td style="padding:9px 14px;font-weight:700;color:#16a34a;font-size:14px;">Rs.{amount_paid:,.0f}</td></tr>
<tr><td style="padding:9px 14px;color:#6b7280;font-size:13px;">Balance at arrival</td><td style="padding:9px 14px;font-weight:700;color:#d97706;font-size:14px;">Rs.{balance_due:,.0f}</td></tr>
<tr><td style="padding:9px 14px;color:#6b7280;font-size:13px;">Grand total</td><td style="padding:9px 14px;font-weight:700;font-size:14px;">Rs.{grand_total:,.0f}</td></tr>
</table>
<table style="width:100%;border-collapse:collapse;margin-bottom:20px;">
<thead><tr style="background:#16a34a;color:#fff;">
<th style="padding:9px 10px;text-align:left;font-size:12px;">Activity</th>
<th style="padding:9px 10px;text-align:left;font-size:12px;">Date</th>
<th style="padding:9px 10px;text-align:left;font-size:12px;">Time</th>
<th style="padding:9px 10px;text-align:left;font-size:12px;">Guests</th>
<th style="padding:9px 10px;text-align:right;font-size:12px;">Amount</th>
</tr></thead>
<tbody>{admin_rows}</tbody>
</table>
<a href="{frontend_url}/admin/bookings/{booking.pk}" style="display:inline-block;background:#16a34a;color:#fff;text-decoration:none;font-weight:700;font-size:13px;padding:12px 24px;border-radius:8px;">Open in Admin Panel</a>
</div></div></body></html>"""

    try:
        _send(
            to=admin_email,
            subject=f"[MangroveSpot] New Booking {booking.reference} - Rs.{grand_total:,.0f}",
            html=owner_html,
        )
        logger.info("Owner alert sent for booking %s", booking.reference)
    except Exception as exc:
        logger.error("Owner alert failed for booking %s: %s", booking.reference, exc)


@shared_task(
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=4,
    name="notifications.send_cancellation_email",
)
def send_cancellation_email(self, booking_id):
    from apps.bookings.models import Booking
    try:
        booking = Booking.objects.get(pk=booking_id)
    except Booking.DoesNotExist:
        logger.error("send_cancellation_email: booking %s not found", booking_id)
        return
    frontend_url = getattr(settings, "FRONTEND_URL", "https://mangrovespot.in")
    admin_email  = getattr(settings, "ADMIN_EMAIL", settings.DEFAULT_FROM_EMAIL)
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"/></head>
<body style="font-family:Arial,sans-serif;background:#f4f7f6;margin:0;padding:0;">
<div style="max-width:600px;margin:24px auto;padding:0 16px;">
<div style="background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">
<div style="background:#dc2626;padding:28px 32px;text-align:center;">
<div style="font-size:36px;margin-bottom:10px;">X</div>
<h2 style="color:#fff;margin:0;font-size:20px;">Booking Cancelled</h2>
</div>
<div style="padding:28px 32px;">
<p style="font-size:13px;color:#6b7280;margin:0 0 4px;">Booking Reference</p>
<p style="font-size:22px;font-weight:700;color:#dc2626;font-family:monospace;margin:0 0 20px;">{booking.reference}</p>
<p style="font-size:15px;color:#1a1a1a;">Hi {booking.customer_name},<br><br>
Your booking has been cancelled. If a refund is applicable, it will be processed within 5-7 business days.</p>
<div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:14px 18px;margin-top:16px;font-size:13px;color:#6b7280;">
Questions? Email <a href="mailto:{admin_email}" style="color:#16a34a;">{admin_email}</a> or call 9496141619.
</div>
</div></div></div></body></html>"""
    try:
        _send(
            to=booking.customer_email,
            subject=f"Booking Cancelled - {booking.reference} | MangroveSpot",
            html=html,
        )
        logger.info("Cancellation email sent for booking %s", booking.reference)
    except Exception as exc:
        countdown = 10 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)


@shared_task(name="notifications.send_booking_confirmation_email")
def send_booking_confirmation_email(booking_id):
    send_confirmation_emails(booking_id)


@shared_task(name="notifications.send_owner_new_booking_alert")
def send_owner_new_booking_alert(booking_id):
    pass


@shared_task(name="notifications.release_expired_slot_holds")
def release_expired_slot_holds():
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
    from apps.bookings.models import BookingItem
    from datetime import date, timedelta
    tomorrow = date.today() + timedelta(days=1)
    items = BookingItem.objects.filter(
        visit_date=tomorrow,
        booking__status="confirmed",
    ).select_related("booking", "activity", "slot")
    for item in items:
        html = f"""<div style="font-family:Arial,sans-serif;padding:20px;">
<h2 style="color:#16a34a;">See You Tomorrow at MangroveSpot!</h2>
<p>Hi {item.booking.customer_name},</p>
<p><strong>{item.activity.name}</strong> tomorrow at <strong>{_slot_label(item)}</strong></p>
<p>Location: Nedungolam, Paravur, Kollam, Kerala</p>
<p>Bring comfortable clothes, water, sunscreen. Carry Rs.{float(item.booking.balance_due):,.0f} for balance payment.</p>
<p>Phone: 9496141619</p>
</div>"""
        try:
            _send(to=item.booking.customer_email, subject=f"See You Tomorrow - {item.activity.name} at MangroveSpot!", html=html)
        except Exception as exc:
            logger.error("24h reminder failed for booking %s: %s", item.booking.reference, exc)
