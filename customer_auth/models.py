import hashlib
import secrets
from django.db import models
from django.utils import timezone
from datetime import timedelta


class CustomerSession(models.Model):
    """
    Represents a verified customer identity.
    Created on first login (Google or OTP), reused on subsequent visits.
    Not a Django User — customers never access the admin.
    """
    email        = models.EmailField(unique=True)
    name         = models.CharField(max_length=200, blank=True)
    google_sub   = models.CharField(max_length=200, blank=True, db_index=True)
    avatar_url   = models.URLField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Customer Session"

    def __str__(self):
        return f"{self.name or self.email}"


class EmailOTP(models.Model):
    """
    One-time 6-digit code for email verification.
    Stored as SHA-256 hash — never plaintext.
    Expires after 10 minutes. Single-use.
    """
    email      = models.EmailField(db_index=True)
    code_hash  = models.CharField(max_length=64)   # SHA-256 hex
    created_at = models.DateTimeField(auto_now_add=True)
    used       = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Email OTP"
        ordering = ["-created_at"]

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.created_at + timedelta(minutes=10)

    @classmethod
    def generate(cls, email: str) -> str:
        """
        Invalidates all previous OTPs for this email,
        creates a new one, returns the plaintext code.
        """
        # Invalidate any existing unused codes for this email
        cls.objects.filter(email=email, used=False).update(used=True)

        code      = str(secrets.randbelow(900000) + 100000)  # 100000–999999
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        cls.objects.create(email=email, code_hash=code_hash)
        return code

    @classmethod
    def verify(cls, email: str, code: str) -> bool:
        """
        Returns True and marks the OTP used if valid.
        Returns False for wrong code, expired, or already used.
        """
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        try:
            otp = cls.objects.filter(
                email=email,
                code_hash=code_hash,
                used=False,
            ).latest("created_at")
        except cls.DoesNotExist:
            return False

        if otp.is_expired:
            return False

        otp.used = True
        otp.save(update_fields=["used"])
        return True