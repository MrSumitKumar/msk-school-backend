from rest_framework import generics, status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from .models import School, SubscriptionPlan, Subscription, Payment, Invoice, Notification, Branch
from .serializers import (
    SchoolSerializer, SchoolCreateSerializer, SubscriptionPlanSerializer, SchoolSettingsSerializer,
    SubscriptionSerializer, SubscriptionHistorySerializer, PaymentSerializer, InvoiceSerializer, NotificationSerializer, BranchSerializer
)
from accounts.permissions import IsSuperAdmin, IsSchoolAdmin
from audit.services import log_action
import razorpay
import requests
import hashlib
import base64
import hmac
import json
import uuid
from django.conf import settings
from decimal import Decimal


class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            instance = serializer.save()
            # Ensure unique name constraint handled gracefully
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        # Better error details for debugging
        errors = serializer.errors
        return Response({
            'error': 'Validation failed',
            'details': errors,
            'hint': 'Check name must be "basic/pro/premium", price > 0, modules/features as JSON strings'
        }, status=status.HTTP_400_BAD_REQUEST)


class SchoolListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return SchoolCreateSerializer if self.request.method == 'POST' else SchoolSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return School.objects.all().prefetch_related('users')
        return School.objects.filter(id=user.school_id)


class SchoolDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SchoolSerializer
    queryset = School.objects.all().prefetch_related('users')


from rest_framework.parsers import MultiPartParser, FormParser

class SchoolSettingsView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def get_school(self, request):
        return request.user.school

    def get(self, request):
        school = self.get_school(request)
        if not school:
            return Response({'error': 'No school associated with this account'}, status=status.HTTP_404_NOT_FOUND)
        serializer = SchoolSerializer(school, context={'request': request})
        return Response(serializer.data)

    def patch(self, request):
        school = self.get_school(request)
        if not school:
            return Response({'error': 'No school associated with this account'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = SchoolSettingsSerializer(school, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            instance = serializer.save()
            
            # Audit Logging
            log_action(
                request, 'UPDATE', 'School', instance.id, instance.name,
                f"Updated settings for school: {instance.name}"
            )
            
            # Return full school data with absolute URLs
            return Response(SchoolSerializer(instance, context={'request': request}).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SubscriptionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Subscription.objects.all().select_related('school', 'plan')
    serializer_class = SubscriptionSerializer

    def get_permissions(self):
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsSuperAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = Subscription.objects.all().select_related('school', 'plan')
        school_id = self.request.query_params.get('school')
        status_filter = self.request.query_params.get('status')
        if school_id:
            queryset = queryset.filter(school_id=school_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        school = data.get('school')
        plan = data.get('plan')
        amount = request.data.get('amount', 0)

        subscription, created = Subscription.objects.update_or_create(
            school=school,
            defaults={
                'plan': plan,
                'start_date': data.get('start_date'),
                'end_date': data.get('end_date'),
                'status': data.get('status'),
                'is_active': data.get('status') in ['active', 'trial'],
            }
        )
        
        SubscriptionHistory.objects.create(
            school=school,
            plan=plan,
            start_date=subscription.start_date,
            end_date=subscription.end_date,
            status=subscription.status,
            action='activation' if created else 'update',
            amount=amount
        )

        self._sync_school(subscription)
        
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(SubscriptionSerializer(subscription).data, status=status_code)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        amount = request.data.get('amount', 0)

        instance = serializer.save()
        
        SubscriptionHistory.objects.create(
            school=instance.school,
            plan=instance.plan,
            start_date=instance.start_date,
            end_date=instance.end_date,
            status=instance.status,
            action='update',
            amount=amount
        )

        self._sync_school(instance)
        return Response(SubscriptionSerializer(instance).data)

    def _sync_school(self, subscription):
        school = subscription.school
        school.subscription_plan = subscription.plan
        school.subscription_start = subscription.start_date
        school.subscription_end = subscription.end_date
        school.is_active = subscription.status in ['active', 'trial']
        school.save()

class PaymentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return Payment.objects.all().order_by('-payment_date')
        return Payment.objects.filter(school_id=user.school_id).order_by('-payment_date')

class InvoiceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = InvoiceSerializer
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return Invoice.objects.all().order_by('-created_at')
        return Invoice.objects.filter(payment__school_id=user.school_id).order_by('-created_at')

class SubscriptionHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SubscriptionHistorySerializer
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return SubscriptionHistory.objects.all().order_by('-created_at')
        return SubscriptionHistory.objects.filter(school_id=user.school_id).order_by('-created_at')

class NotificationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return Notification.objects.all()
        return Notification.objects.filter(school_id=user.school_id)

class BranchViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return Branch.objects.all()
        return Branch.objects.filter(school_id=user.school_id)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def super_admin_dashboard_stats(request):
    if request.user.role != 'super_admin':
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    
    total_schools = School.objects.count()
    active_subscriptions = Subscription.objects.filter(status='active').count()
    
    # Calculate monthly revenue
    thirty_days_ago = timezone.now() - timedelta(days=30)
    monthly_revenue = Payment.objects.filter(
        payment_status='completed',
        payment_date__gte=thirty_days_ago
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Count subscriptions expiring in next 7 days
    seven_days_later = timezone.now().date() + timedelta(days=7)
    expiring_soon = Subscription.objects.filter(
        status='active',
        end_date__lte=seven_days_later,
        end_date__gte=timezone.now().date()
    ).count()

    return Response({
        'total_schools': total_schools,
        'active_subscriptions': active_subscriptions,
        'monthly_revenue': monthly_revenue,
        'expiring_subscriptions': expiring_soon
    })

# ─── School Admin Billing APIs ───────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_subscription(request):
    """Returns the active subscription details for the school admin's school."""
    school = request.user.school
    if not school:
        return Response({'error': 'No school associated'}, status=404)
    
    sub = Subscription.objects.select_related('plan').filter(school=school, is_active=True).first()
    if not sub:
        return Response({'active_plan': None})
    
    return Response({
        'active_plan': SubscriptionSerializer(sub).data,
        'server_time': timezone.now()
    })


# ─── Razorpay Payment Views ───────────────────────────

def _activate_subscription_and_invoice(payment):
    """
    Helper: activate subscription, sync school, generate invoice.
    Idempotent — skips if payment already completed.
    """
    if payment.payment_status == 'completed':
        return

    plan = payment.plan
    school = payment.school

    # 1. Create / update subscription
    sub, created = Subscription.objects.update_or_create(
        school=school,
        defaults={
            'plan': plan,
            'start_date': timezone.now().date(),
            'end_date': (timezone.now() + timedelta(days=30 * plan.duration_months)).date(),
            'status': 'active',
            'is_active': True,
        }
    )

    # 2. Sync school fields
    school.subscription_plan = plan
    school.subscription_start = sub.start_date
    school.subscription_end = sub.end_date
    school.save()

    # 2.5 Log History
    SubscriptionHistory.objects.create(
        school=school,
        plan=plan,
        start_date=sub.start_date,
        end_date=sub.end_date,
        status='active',
        action='renewal' if not created else 'activation',
        amount=payment.amount
    )

    # 3. Mark payment completed & set invoice
    invoice_number = f"INV-{school.id}-{payment.id}-{uuid.uuid4().hex[:6].upper()}"
    payment.payment_status = 'completed'
    payment.invoice_number = invoice_number
    payment.save(update_fields=['payment_status', 'invoice_number'])

    # 4. Auto-generate invoice
    Invoice.objects.get_or_create(
        payment=payment,
        defaults={
            'invoice_number': invoice_number,
            'school_name': school.name,
            'plan_name': plan.name,
            'amount': payment.amount,
            'payment_date': timezone.now(),
            'status': 'paid',
        }
    )

    # 5. Notify school
    Notification.objects.create(
        school=school,
        message=f"✅ Payment successful! Your {plan.name.upper()} plan is now active until {sub.end_date}.",
        notification_type='billing'
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_razorpay_order(request):
    """
    Creates a Razorpay order for the selected plan.
    Returns: { order_id, amount, currency, key_id, plan_name }
    """
    plan_id = request.data.get('plan_id')
    school = request.user.school

    if not plan_id or not school:
        return Response({'error': 'plan_id and school are required'}, status=400)

    key_id = getattr(settings, 'RAZORPAY_KEY_ID', '')
    key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '')

    if not key_id or not key_secret:
        return Response(
            {'error': 'Razorpay credentials are not configured. Please set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env file.'},
            status=500
        )

    try:
        plan = SubscriptionPlan.objects.get(id=plan_id)
    except SubscriptionPlan.DoesNotExist:
        return Response({'error': 'Plan not found'}, status=404)

    # Razorpay amount is in paise (multiply INR by 100)
    amount_paise = int(plan.price * 100)

    try:
        client = razorpay.Client(auth=(key_id, key_secret))
        order = client.order.create({
            'amount': amount_paise,
            'currency': 'INR',
            'receipt': f'school_{school.id}_plan_{plan.id}_{uuid.uuid4().hex[:8]}',
            'notes': {
                'school_id': str(school.id),
                'school_name': school.name,
                'plan_id': str(plan.id),
                'plan_name': plan.name,
            }
        })
    except Exception as e:
        return Response({'error': f'Razorpay order creation failed: {str(e)}'}, status=500)

    # Save a pending payment record with the Razorpay order_id as transaction_id
    Payment.objects.create(
        school=school,
        plan=plan,
        amount=plan.price,
        payment_method='razorpay',
        transaction_id=order['id'],   # Razorpay order_id stored here initially
        payment_status='pending',
    )

    return Response({
        'order_id': order['id'],
        'amount': amount_paise,
        'currency': 'INR',
        'key_id': key_id,
        'plan_name': plan.name,
        'school_name': school.name,
        'contact_email': school.contact_email,
        'contact_phone': school.contact_phone,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_razorpay_payment(request):
    """
    Verifies Razorpay payment signature after checkout completes.
    Accepts: { razorpay_order_id, razorpay_payment_id, razorpay_signature }
    """
    razorpay_order_id = request.data.get('razorpay_order_id')
    razorpay_payment_id = request.data.get('razorpay_payment_id')
    razorpay_signature = request.data.get('razorpay_signature')
    school = request.user.school

    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        return Response({'error': 'razorpay_order_id, razorpay_payment_id, and razorpay_signature are required'}, status=400)

    key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '')
    if not key_secret:
        return Response({'error': 'Razorpay secret key not configured'}, status=500)

    # Verify HMAC-SHA256 signature
    generated_signature = hmac.new(
        key_secret.encode('utf-8'),
        f'{razorpay_order_id}|{razorpay_payment_id}'.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    if generated_signature != razorpay_signature:
        return Response({'error': 'Invalid payment signature. Payment verification failed.'}, status=400)

    # Look up the pending payment by order_id (stored as transaction_id initially)
    try:
        payment = Payment.objects.get(transaction_id=razorpay_order_id, school=school)
    except Payment.DoesNotExist:
        return Response({'error': 'Payment record not found for this order'}, status=404)

    # Update transaction_id to the actual Razorpay payment_id
    payment.transaction_id = razorpay_payment_id
    payment.save()

    # Activate subscription and generate invoice
    _activate_subscription_and_invoice(payment)

    return Response({
        'status': 'success',
        'message': f'Payment verified! Your {payment.plan.name.upper()} plan is now active.',
        'payment_id': razorpay_payment_id,
        'plan': payment.plan.name,
    })


# ─── Razorpay Webhook (for server-to-server events) ──

@api_view(['POST'])
def razorpay_webhook(request):
    """
    Handles Razorpay webhook events for server-side payment confirmation.
    Set webhook URL in Razorpay Dashboard -> Webhooks.
    """
    webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '')
    
    if webhook_secret:
        # Verify webhook signature
        razorpay_signature = request.headers.get('X-Razorpay-Signature', '')
        body = request.body
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            body,
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected_signature, razorpay_signature):
            return Response({'error': 'Invalid webhook signature'}, status=400)

    try:
        event = request.data
        event_type = event.get('event')

        if event_type == 'payment.captured':
            payload = event['payload']['payment']['entity']
            order_id = payload.get('order_id')
            payment_id = payload.get('id')

            try:
                payment = Payment.objects.get(transaction_id=order_id)
                payment.transaction_id = payment_id
                payment.save()
                _activate_subscription_and_invoice(payment)
            except Payment.DoesNotExist:
                pass  # Already processed or unknown

        return Response({'status': 'ok'})
    except Exception as e:
        return Response({'error': str(e)}, status=500)


# ─── PhonePe Views (preserved) ───────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_phonepe_order(request):
    """Creates a Real PhonePe payment request for a selected plan."""
    print(f"DEBUG: Entering create_phonepe_order for user: {request.user}")
    
    plan_id = request.data.get('plan_id')
    school = getattr(request.user, 'school', None)
    
    print(f"DEBUG: plan_id: {plan_id}, school: {school}")
    
    if not plan_id or not school:
        print(f"DEBUG: Invalid request - plan_id: {plan_id}, school: {school}")
        return Response({'error': 'Invalid request: plan_id and school are required'}, status=400)

    # --- PhonePe Credentials (Now using dynamic settings) ---
    merchant_id = str(getattr(settings, 'PHONEPE_MERCHANT_ID', '')).strip()
    salt_key = str(getattr(settings, 'PHONEPE_SALT_KEY', '')).strip()
    salt_index = str(getattr(settings, 'PHONEPE_SALT_INDEX', '1')).strip()
    api_url = str(getattr(settings, 'PHONEPE_API_URL', 'https://api-preprod.phonepe.com/apis/hermes/pg/v1/pay')).strip()
    # -----------------------------------------------------------

    try:
        plan = SubscriptionPlan.objects.get(id=plan_id)
    except SubscriptionPlan.DoesNotExist:
        return Response({'error': 'Plan not found'}, status=404)

    # Enforce 15-day restriction
    existing_sub = Subscription.objects.filter(school=school, status__in=['active', 'trial']).first()
    if existing_sub:
        today = timezone.now().date()
        if existing_sub.end_date > today:
            days_remaining = (existing_sub.end_date - today).days
            if days_remaining > 15:
                return Response({
                    'error': 'Upgrade available only when plan is near expiry (within 15 days).',
                    'days_remaining': days_remaining
                }, status=status.HTTP_400_BAD_REQUEST)

    transaction_id = f"MT{uuid.uuid4().hex[:14].upper()}"
    amount_in_paise = int(plan.price * 100)
    
    # Use simple redirect URL to avoid nested param issues in hash
    base_url = "http://localhost:5173/admin/billing"
    redirect_url = f"{base_url}?tid={transaction_id}"
    callback_url = "https://webhook.site/0e3b9e4a-5f0a-4a5f-8f0a-5f0a4a5f8f0a" # Valid looking placeholder

    payload = {
        "merchantId": merchant_id,
        "merchantTransactionId": transaction_id,
        "merchantUserId": f"USR{school.id}",
        "amount": amount_in_paise,
        "redirectUrl": redirect_url,
        "redirectMode": "REDIRECT",
        "callbackUrl": callback_url,
        "paymentInstrument": {
            "type": "PAY_PAGE"
        }
    }

    # Crucial: PhonePe expects no spaces in the JSON payload for hashing
    json_payload = json.dumps(payload, separators=(',', ':'))
    base64_payload = base64.b64encode(json_payload.encode('utf-8')).decode('utf-8')

    # Hash Path must be EXACTLY the endpoint path
    checksum_path = "/pg/v1/pay"
    string_to_hash = base64_payload + checksum_path + salt_key
    sha256_hash = hashlib.sha256(string_to_hash.encode('utf-8')).hexdigest()
    x_verify = f"{sha256_hash}###{salt_index}"

    headers = {
        "Content-Type": "application/json",
        "X-VERIFY": x_verify,
        "accept": "application/json"
    }

    # Terminal logs for verification
    print(f"DEBUG: Initiating PhonePe Pay for {plan.name}")
    print(f"DEBUG: Merchant ID: {merchant_id}")
    print(f"DEBUG: Payload: {json_payload}")
    print(f"DEBUG: X-VERIFY: {x_verify}")
    print(f"DEBUG: API URL: {api_url}")
    
    try:
        response = requests.post(api_url, json={"request": base64_payload}, headers=headers)
        print(f"DEBUG: Status Code: {response.status_code}")
        print(f"DEBUG: Response Text: {response.text}")
        res_data = response.json()
        
        if res_data.get('success'):
            # Defensive check for redirect URL
            instrument = res_data.get('data', {}).get('instrumentResponse', {})
            # Sandbox might return list or direct object
            if isinstance(instrument, list) and len(instrument) > 0:
                instrument = instrument[0]
            
            redirect_info = instrument.get('redirectInfo', {})
            payment_url = redirect_info.get('url')

            if payment_url:
                Payment.objects.create(
                    school=school, plan=plan, amount=plan.price,
                    payment_method='phonepe', transaction_id=transaction_id,
                    payment_status='pending'
                )
                return Response({
                    'payment_url': payment_url,
                    'transaction_id': transaction_id
                })
            else:
                return Response({'error': 'Payment URL missing from PhonePe response'}, status=400)
        else:
            # Enhanced error logging for debugging
            print(f"DEBUG: PhonePe Response (FAILED) - Status: {response.status_code}")
            print(f"DEBUG: PhonePe Response Body: {res_data}")
            return Response({
                'error': res_data.get('message', 'PhonePe request failed'),
                'details': res_data.get('code', 'UNKNOWN_CODE'),
                'phonepe_response': res_data
            }, status=400)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_phonepe_payment(request):
    """Checks the status of a PhonePe payment (Polling/Manual Check)."""
    transaction_id = request.data.get('transaction_id')
    school = request.user.school

    if not transaction_id:
        return Response({'error': 'Transaction ID is required'}, status=400)

    # --- PhonePe Credentials (Dynamic) ---
    merchant_id = str(getattr(settings, 'PHONEPE_MERCHANT_ID', '')).strip()
    salt_key = str(getattr(settings, 'PHONEPE_SALT_KEY', '')).strip()
    salt_index = str(getattr(settings, 'PHONEPE_SALT_INDEX', '1')).strip()
    # -----------------------------------------------------------
    
    status_path = f"/pg/v1/status/{merchant_id}/{transaction_id}"
    string_to_hash = status_path + salt_key
    sha256_hash = hashlib.sha256(string_to_hash.encode('utf-8')).hexdigest()
    x_verify = f"{sha256_hash}###{salt_index}"

    headers = {
        "Content-Type": "application/json",
        "X-VERIFY": x_verify,
        "X-MERCHANT-ID": merchant_id
    }

    try:
        # Use hermes for status checks as well
        status_url = f"https://api-preprod.phonepe.com/apis/hermes/pg/v1/status/{merchant_id}/{transaction_id}"
        
        print(f"DEBUG: Verifying PhonePe Payment: {transaction_id}")
        print(f"DEBUG: Status URL: {status_url}")
        print(f"DEBUG: X-VERIFY: {x_verify}")
             
        response = requests.get(status_url, headers=headers)
        print(f"DEBUG: Status Code: {response.status_code}")
        print(f"DEBUG: Response Text: {response.text}")
        res_data = response.json()

        if res_data.get('success') and res_data.get('code') == 'PAYMENT_SUCCESS':
            payment = Payment.objects.get(transaction_id=transaction_id)
            _activate_subscription_and_invoice(payment)
            return Response({'status': 'success', 'message': 'Payment verified successfully.'})
        else:
            return Response({'status': 'pending', 'message': res_data.get('message', 'Payment not successful yet.')})
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_binance_order(request):
    """Creates a Real Binance Pay order for a selected plan."""
    plan_id = request.data.get('plan_id')
    school = request.user.school
    
    if not plan_id or not school:
        return Response({'error': 'Invalid request'}, status=400)

    api_key = getattr(settings, 'BINANCE_API_KEY', '')
    api_secret = getattr(settings, 'BINANCE_API_SECRET', '')
    if not api_key or not api_secret:
        return Response({'error': 'Binance Pay credentials (API Key or Secret) are not configured in .env file.'}, status=500)
    
    try:
        plan = SubscriptionPlan.objects.get(id=plan_id)
    except SubscriptionPlan.DoesNotExist:
        return Response({'error': 'Plan not found'}, status=404)

    merchant_trade_no = uuid.uuid4().hex[:16].upper()
    base_url = "http://localhost:5173/admin/billing"
    
    payload = {
        "env": {"terminalType": "WEB", "returnUrl": f"{base_url}?mtn={merchant_trade_no}"},
        "merchantTradeNo": merchant_trade_no,
        "orderAmount": float(plan.price),
        "currency": "USDT",
        "description": f"Upgrade to {plan.name} Plan",
        "goodsDetails": [{
            "goodsType": "01",
            "goodsCategory": "Services",
            "referenceGoodsId": str(plan.id),
            "goodsName": plan.name,
            "goodsDetail": f"{plan.max_students} Students limit"
        }]
    }

    timestamp = str(int(timezone.now().timestamp() * 1000))
    nonce = uuid.uuid4().hex[:32]
    json_payload = json.dumps(payload)
    signature_payload = f"{timestamp}\n{nonce}\n{json_payload}\n"
    
    signature = hmac.new(
        api_secret.encode('utf-8'),
        signature_payload.encode('utf-8'),
        hashlib.sha512
    ).hexdigest().upper()

    headers = {
        "Content-Type": "application/json",
        "BinancePay-Timestamp": timestamp,
        "BinancePay-Nonce": nonce,
        "BinancePay-Certificate-SN": getattr(settings, 'BINANCE_API_KEY', ''),
        "BinancePay-Signature": signature
    }

    try:
        response = requests.post(
            getattr(settings, 'BINANCE_API_URL', 'https://bpay.binanceapi.com/binancepay/openapi/v2/order'),
            json=payload, headers=headers
        )
        res_data = response.json()

        if res_data.get('status') == 'SUCCESS':
            Payment.objects.create(
                school=school, plan=plan, amount=plan.price,
                payment_method='binance', transaction_id=merchant_trade_no,
                payment_status='pending'
            )
            return Response({
                'payment_url': res_data['data']['checkoutUrl'],
                'prepay_id': res_data['data']['prepayId'],
                'merchant_trade_no': merchant_trade_no
            })
        else:
            return Response({'error': res_data.get('errorMessage', 'Binance Pay request failed')}, status=400)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_binance_payment(request):
    """Verifies Binance payment status via Query Order API."""
    merchant_trade_no = request.data.get('merchant_trade_no')

    if not merchant_trade_no:
        return Response({'error': 'Merchant Trade No is required'}, status=400)

    payload = {"merchantTradeNo": merchant_trade_no}
    json_payload = json.dumps(payload)
    
    timestamp = str(int(timezone.now().timestamp() * 1000))
    nonce = uuid.uuid4().hex[:32]
    signature_payload = f"{timestamp}\n{nonce}\n{json_payload}\n"
    api_secret = getattr(settings, 'BINANCE_API_SECRET', '')
    
    signature = hmac.new(
        api_secret.encode('utf-8'),
        signature_payload.encode('utf-8'),
        hashlib.sha512
    ).hexdigest().upper()

    headers = {
        "Content-Type": "application/json",
        "BinancePay-Timestamp": timestamp,
        "BinancePay-Nonce": nonce,
        "BinancePay-Certificate-SN": getattr(settings, 'BINANCE_API_KEY', ''),
        "BinancePay-Signature": signature
    }

    try:
        query_url = getattr(settings, 'BINANCE_API_URL', '').replace('/order', '/order/query')
        if not query_url or '/order/query' not in query_url:
            query_url = "https://bpay.binanceapi.com/binancepay/openapi/v2/order/query"

        response = requests.post(query_url, json=payload, headers=headers)
        res_data = response.json()

        if res_data.get('status') == 'SUCCESS' and res_data['data']['status'] == 'PAID':
            payment = Payment.objects.get(transaction_id=merchant_trade_no)
            _activate_subscription_and_invoice(payment)
            return Response({'status': 'success', 'message': 'Payment verified successfully.'})
        else:
            return Response({'status': 'pending', 'message': 'Payment not confirmed by Binance yet.'})
    except Exception as e:
        return Response({'error': str(e)}, status=500)
