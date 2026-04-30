from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('fees', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='feestructure',
            name='installments',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='feestructure',
            name='discount_percent',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name='feestructure',
            name='late_fee_penalty_percent',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name='feestructure',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='feestructure',
            name='notes',
            field=models.TextField(blank=True),
        ),
        migrations.CreateModel(
            name='FeeInstallment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('installment_number', models.PositiveIntegerField(default=1)),
                ('due_date', models.DateField()),
                ('amount_due', models.DecimalField(decimal_places=2, max_digits=10)),
                ('amount_paid', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('discount_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('penalty_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('status', models.CharField(choices=[('paid', 'Paid'), ('pending', 'Pending'), ('overdue', 'Overdue'), ('partial', 'Partial')], default='pending', max_length=10)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('fee_structure', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fee_installment_records', to='fees.feestructure')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fee_installments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['fee_structure', 'installment_number'],
                'unique_together': {('student', 'fee_structure', 'installment_number')},
            },
        ),
        migrations.AddField(
            model_name='feepayment',
            name='amount_due',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='feepayment',
            name='installment',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payments', to='fees.feeinstallment'),
        ),
    ]
