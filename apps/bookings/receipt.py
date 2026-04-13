from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from .models import Booking
import qrcode, io

@api_view(['GET'])
@permission_classes([AllowAny])
def download_receipt(request, reference):
    try:
        booking = Booking.objects.get(reference=reference)
    except Booking.DoesNotExist:
        from rest_framework.response import Response
        from rest_framework import status
        return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)

    buf = io.BytesIO()
    p = canvas.Canvas(buf, pagesize=A4)
    W, H = A4

    # Background
    p.setFillColorRGB(0.06, 0.06, 0.06)
    p.rect(0, 0, W, H, fill=1, stroke=0)

    # Green header bar
    p.setFillColorRGB(0.09, 0.64, 0.42)
    p.rect(0, H - 80*mm, W, 80*mm, fill=1, stroke=0)

    # Header text
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 24)
    p.drawString(20*mm, H - 30*mm, "MangroveSpot Adventures")
    p.setFont("Helvetica", 12)
    p.drawString(20*mm, H - 42*mm, "Paravur, Kerala  |  mangrovespot.in")
    p.setFont("Helvetica-Bold", 14)
    p.drawString(20*mm, H - 58*mm, "PAYMENT RECEIPT")

    # Booking reference box
    p.setFillColorRGB(0.1, 0.1, 0.1)
    p.roundRect(15*mm, H - 105*mm, W - 30*mm, 20*mm, 3*mm, fill=1, stroke=0)
    p.setFillColorRGB(0.09, 0.64, 0.42)
    p.setFont("Helvetica-Bold", 11)
    p.drawString(20*mm, H - 96*mm, "Booking Reference:")
    p.setFont("Helvetica-Bold", 16)
    p.drawString(75*mm, H - 96*mm, booking.reference)

    # Details
    p.setFillColorRGB(0.7, 0.7, 0.7)
    p.setFont("Helvetica", 10)
    y = H - 120*mm

    def row(label, value, highlight=False):
        nonlocal y
        p.setFillColorRGB(0.5, 0.5, 0.5)
        p.setFont("Helvetica", 10)
        p.drawString(20*mm, y, label)
        if highlight:
            p.setFillColorRGB(0.09, 0.64, 0.42)
            p.setFont("Helvetica-Bold", 11)
        else:
            p.setFillColorRGB(0.9, 0.9, 0.9)
            p.setFont("Helvetica", 11)
        p.drawString(75*mm, y, str(value))
        y -= 9*mm

    row("Customer", booking.customer_name)
    row("Email", booking.customer_email)
    row("Phone", booking.customer_phone)
    row("Visit Date", str(booking.items.first().visit_date) if booking.items.exists() else "—")
    row("Arrival Time", str(booking.items.first().arrival_time) if booking.items.exists() else "—")

    # Divider
    y -= 3*mm
    p.setStrokeColorRGB(0.2, 0.2, 0.2)
    p.line(15*mm, y, W - 15*mm, y)
    y -= 8*mm

    # Activities
    p.setFillColorRGB(0.09, 0.64, 0.42)
    p.setFont("Helvetica-Bold", 11)
    p.drawString(20*mm, y, "Activities Booked")
    y -= 8*mm

    for item in booking.items.all():
        p.setFillColorRGB(0.85, 0.85, 0.85)
        p.setFont("Helvetica", 10)
        guests = f"{item.num_adults}A"
        if item.num_children: guests += f" + {item.num_children}C"
        p.drawString(23*mm, y, f"• {item.activity.name}  ({guests})")
        p.setFillColorRGB(0.9, 0.9, 0.9)
        p.drawRightString(W - 15*mm, y, f"₹{item.price:,.0f}")
        y -= 8*mm

    # Payment summary
    y -= 5*mm
    p.setStrokeColorRGB(0.2, 0.2, 0.2)
    p.line(15*mm, y, W - 15*mm, y)
    y -= 10*mm

    row("Grand Total", f"₹{booking.grand_total:,.0f}")
    row("Paid Online (50%)", f"₹{booking.amount_paid:,.0f}", highlight=True)
    row("Balance at Arrival", f"₹{booking.balance_due:,.0f}")

    # Status badge
    y -= 5*mm
    p.setFillColorRGB(0.05, 0.3, 0.15)
    p.roundRect(15*mm, y - 5*mm, 50*mm, 12*mm, 2*mm, fill=1, stroke=0)
    p.setFillColorRGB(0.09, 0.64, 0.42)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(18*mm, y + 1*mm, f"STATUS: {booking.status.upper()}")

    # Footer
    p.setFillColorRGB(0.35, 0.35, 0.35)
    p.setFont("Helvetica", 8)
    p.drawCentredString(W/2, 15*mm, "Thank you for booking with MangroveSpot Adventures  •  mangrovespot.in")
    p.drawCentredString(W/2, 10*mm, f"Generated on {booking.created_at.strftime('%d %b %Y %I:%M %p')}")

    p.save()
    buf.seek(0)
    response = HttpResponse(buf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="MangroveSpot-{booking.reference}.pdf"'
    return response