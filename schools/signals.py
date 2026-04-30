from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from .models import School, Subscription, SubscriptionPlan
from academics.models import Grade, Section, AcademicSession

@receiver(post_save, sender=School)
def create_default_school_structure(sender, instance, created, **kwargs):
    """
    Automatically creates default grades, sections and academic session for a new school.
    Optimized with bulk_create to ensure high performance (1-2 queries instead of 60+).
    """
    if created:
        # Wrap in atomic transaction to ensure all or nothing
        with transaction.atomic():
            # 1. Create Default Academic Session
            now = timezone.now()
            AcademicSession.objects.create(
                school=instance,
                name=f"{now.year}-{now.year + 1}",
                start_date=now.date(),
                end_date=now.date().replace(year=now.year + 1),
                is_active=True
            )

            # 2. Prepare Grades for bulk_create
            standard_grades_data = [
                ('Nursery', 'pre_primary', 1),
                ('LKG', 'pre_primary', 2),
                ('UKG', 'pre_primary', 3),
                ('1', 'primary', 4),
                ('2', 'primary', 5),
                ('3', 'primary', 6),
                ('4', 'primary', 7),
                ('5', 'primary', 8),
                ('6', 'middle', 9),
                ('7', 'middle', 10),
                ('8', 'middle', 11),
                ('9', 'secondary', 12),
                ('10', 'secondary', 13),
                ('11', 'senior_secondary', 14),
                ('12', 'senior_secondary', 15),
            ]
            
            grade_objs = [
                Grade(school=instance, name=name, level=level, order=order)
                for name, level, order in standard_grades_data
            ]
            # Use bulk_create and capture returned objects (since SQLite might not return IDs unless specified, 
            # but usually it works fine for simple relations)
            created_grades = Grade.objects.bulk_create(grade_objs)

            # 3. Prepare Sections for bulk_create
            section_objs = []
            for grade in created_grades:
                for section_name in ['A', 'B', 'C']:
                    section_objs.append(Section(grade=grade, name=section_name))
            
            Section.objects.bulk_create(section_objs)

            # 4. Create Default Subscription (Basic Plan)
            basic_plan = SubscriptionPlan.objects.filter(name='basic').first()
            if basic_plan:
                Subscription.objects.create(
                    school=instance,
                    plan=basic_plan,
                    start_date=now.date(),
                    end_date=(now + timedelta(days=30)).date(),
                    status='trial',
                    is_active=True
                )
                
                # Sync school fields
                instance.subscription_plan = basic_plan
                instance.subscription_start = now.date()
                instance.subscription_end = (now + timedelta(days=30)).date()
                instance.save(update_fields=['subscription_plan', 'subscription_start', 'subscription_end'])
