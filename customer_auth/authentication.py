# import logging
# from rest_framework.authentication import BaseAuthentication
# from rest_framework.exceptions import AuthenticationFailed
# from .tokens import decode_customer_token
# from .models import CustomerSession

# logger = logging.getLogger(__name__)


# class CustomerJWTAuthentication(BaseAuthentication):
#     """
#     Authenticates customer requests using the custom HMAC JWT
#     issued by make_customer_token(). Header: Authorization: Bearer <token>
#     Sets request.user to CustomerPrincipal (not a Django User).
#     """

#     def authenticate(self, request):
#         auth_header = request.headers.get('Authorization', '')
#         logger.debug("CustomerJWTAuthentication: header=%r", auth_header[:60])

#         if not auth_header.startswith('Bearer '):
#             return None

#         token = auth_header[7:].strip()
#         if not token:
#             return None

#         payload = decode_customer_token(token)
#         logger.debug("CustomerJWTAuthentication: payload=%r", payload)

#         if payload is None:
#             raise AuthenticationFailed('Invalid or expired customer token.')

#         if payload.get('type') != 'customer':
#             return None  # Let other authenticators handle admin JWTs

#         try:
#             customer = CustomerSession.objects.get(id=payload['sub'])
#         except CustomerSession.DoesNotExist:
#             raise AuthenticationFailed('Customer account not found.')

#         return (CustomerPrincipal(customer), token)

#     def authenticate_header(self, request):
#         return 'Bearer realm="customer"'


# class CustomerPrincipal:
#     """
#     Wraps CustomerSession to work as request.user in DRF views.
#     Satisfies DRF's IsAuthenticated permission check.
#     """

#     def __init__(self, customer: CustomerSession):
#         self._customer = customer
#         self.id        = customer.id
#         self.pk        = customer.id
#         self.email     = customer.email
#         self.name      = customer.name
#         self.is_active = True

#     @property
#     def is_authenticated(self):
#         return True

#     @property
#     def is_staff(self):
#         return False

#     @property
#     def is_anonymous(self):
#         return False

#     @property
#     def is_superuser(self):
#         return False

#     def __str__(self):
#         return self.email


import logging
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .tokens import decode_customer_token
from .models import CustomerSession


logger = logging.getLogger(__name__)


class CustomerJWTAuthentication(BaseAuthentication):
    """
    Authenticates customer requests using the custom HMAC JWT
    issued by make_customer_token(). Header: Authorization: Bearer <token>
    Sets request.user to CustomerPrincipal (not a Django User).

    Return rules (BaseAuthentication contract):
      None              → not our token, pass to next authenticator
      (principal, token) → authenticated successfully
      raise AuthenticationFailed → our token but invalid (stop all auth)
    """

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization', '')
        logger.debug("CustomerJWTAuthentication: header=%r", auth_header[:60])

        if not auth_header.startswith('Bearer '):
            return None

        token = auth_header[7:].strip()
        if not token:
            return None

        payload = decode_customer_token(token)
        logger.debug("CustomerJWTAuthentication: payload=%r", payload)

        # ✅ FIX: was raise AuthenticationFailed — that blocked JWTAuthentication
        # from running on admin tokens. Return None so DRF tries the next class.
        if payload is None:
            return None

        # Has a payload but not a customer token (e.g. admin SimpleJWT)
        if payload.get('type') != 'customer':
            return None

        # Positively identified as a customer token — now we can raise on errors
        try:
            customer = CustomerSession.objects.get(id=payload['sub'])
        except CustomerSession.DoesNotExist:
            raise AuthenticationFailed('Customer account not found.')

        return (CustomerPrincipal(customer), token)

    def authenticate_header(self, request):
        return 'Bearer realm="customer"'


class CustomerPrincipal:
    """
    Wraps CustomerSession to work as request.user in DRF views.
    Satisfies DRF's IsAuthenticated permission check.
    """

    def __init__(self, customer: CustomerSession):
        self._customer = customer
        self.id        = customer.id
        self.pk        = customer.id
        self.email     = customer.email
        self.name      = customer.name
        self.is_active = True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_staff(self):
        return False

    @property
    def is_anonymous(self):
        return False

    @property
    def is_superuser(self):
        return False

    def __str__(self):
        return self.email