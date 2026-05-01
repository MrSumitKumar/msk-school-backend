from django.core.management.base import BaseCommand
from django.utils import timezone
from schools.models import Subscription, Notification

class Command(BaseCommand):
    help = 'Check for expired subscriptions and update status'

    def handle(self, *args, **options):
        today = timezone.now().date()
        
        # Mark expired
        expired_subs = Subscription.objects.filter(
            status__in=['active', 'trial'],
            end_date__lt=today
        )
        
        count = 0
        for sub in expired_subs:
            sub.status = 'expired'
            sub.is_active = False
            sub.save()
            
            # Sync school
            school = sub.school
            school.is_active = False
            school.save()
            
            # Notify
            Notification.objects.create(
                school=school,
                message="🚨 Your subscription has expired. Please renew to continue using all features.",
                notification_type='billing'
            )
            count += 1
            
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {count} expired subscriptions'))

        # Also check for near expiry (within 15 days) to create notifications if not already done
        near_expiry_date = today + timezone.timedelta(days=15)
        nearing_expiry = Subscription.objects.filter(
            status__in=['active', 'trial'],
            end_date__lte=near_expiry_date,
            end_date__gte=today
        )
        
        notify_count = 0
        for sub in nearing_expiry:
            days_left = (sub.end_date - today).days
            message = f"⚠️ Your subscription will expire in {days_left} days. Please renew soon."
            
            # Check if a recent notification exists to avoid spamming
            recent_notif = Notification.objects.filter(
                school=sub.school,
                message__contains="expire in",
                created_at__gte=timezone.now() - timezone.timedelta(days=1)
            ).exists()
            
            if not recent_notif:
                Notification.objects.create(
                    school=sub.school,
                    message=message,
                    notification_type='billing'
                )
                notify_count += 1
                
        self.stdout.write(self.style.SUCCESS(f'Sent {notify_count} renewal reminders'))
