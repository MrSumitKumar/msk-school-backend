from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from schools.models import Subscription, Notification
from accounts.models import User
from django.core.mail import send_mail
from django.conf import settings

class Command(BaseCommand):
    help = 'Checks subscriptions for expiry and creates notifications/sends emails'

    def send_expiry_alert(self, subscription, days_left):
        school = subscription.school
        
        # Get School Admin users
        admins = User.objects.filter(school=school, role='school_admin')
        admin_emails = [admin.email for admin in admins if admin.email]

        if days_left == 0:
            subject = f"Urgent: {school.name} Subscription Expired Today!"
            body = f"Hello,\n\nYour subscription for {school.name} has expired today. Your access to premium features has been restricted. Please renew immediately to restore full access."
            msg_type = 'error'
            notif_msg = "Your subscription has expired today. Please renew."
        else:
            subject = f"Reminder: {school.name} Subscription expires in {days_left} days"
            body = f"Hello,\n\nYour subscription for {school.name} will expire in {days_left} days on {subscription.end_date}. Please renew your subscription to avoid service interruption."
            msg_type = 'warning'
            notif_msg = f"Your subscription will expire in {days_left} days."

        # Create In-App Notification
        Notification.objects.create(
            school=school,
            message=notif_msg,
            notification_type=msg_type
        )
        
        # Send Email
        if admin_emails:
            try:
                send_mail(
                    subject,
                    body,
                    settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@schoolerp.com',
                    admin_emails,
                    fail_silently=True,
                )
                self.stdout.write(self.style.SUCCESS(f"Sent email alert to {school.name} ({admin_emails}) - {days_left} days left"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Failed to send email to {school.name}: {e}"))

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        
        # 1. Check for expired subscriptions and update status
        expired_subs = Subscription.objects.filter(
            end_date__lt=today,
            status__in=['active', 'trial']
        )
        
        count_expired = 0
        for sub in expired_subs:
            sub.status = 'expired'
            sub.is_active = False
            sub.save()
            self.send_expiry_alert(sub, 0)
            count_expired += 1
            
        if count_expired > 0:
            self.stdout.write(self.style.WARNING(f"Updated {count_expired} subscriptions to 'expired' status."))
            
        # 2. Daily Reminders (7 days and 3 days before expiry)
        for days_left in [7, 3]:
            target_date = today + timedelta(days=days_left)
            expiring_subs = Subscription.objects.filter(
                end_date=target_date,
                status='active'
            )
            for sub in expiring_subs:
                self.send_expiry_alert(sub, days_left)
                
        self.stdout.write(self.style.SUCCESS('Successfully completed subscription expiry check.'))
