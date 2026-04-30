import logging
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from io import BytesIO
from .models import FeeCategory, FeeStructure, FeePayment, FeeInstallment
from .serializers import (
    FeeCategorySerializer,
    FeeStructureSerializer,
    FeePaymentSerializer,
    FeeInstallmentSerializer,
)
from accounts.permissions import IsSuperAdminOrSchoolAdmin, IsStudent, GlobalTenantPermission


class FeeCategoryListCreateView(generics.ListCreateAPIView):
    serializer_class = FeeCategorySerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsSuperAdminOrSchoolAdmin(), GlobalTenantPermission()]
        return [IsAuthenticated(), GlobalTenantPermission()]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return FeeCategory.objects.all()
        return FeeCategory.objects.filter(school=user.school)

    def perform_create(self, serializer):
        user = self.request.user
        if user.role != 'super_admin':
            serializer.save(school=user.school)
        else:
            serializer.save()


class FeeStructureListCreateView(generics.ListCreateAPIView):
    serializer_class = FeeStructureSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsSuperAdminOrSchoolAdmin(), GlobalTenantPermission()]
        return [IsAuthenticated(), GlobalTenantPermission()]

    def get_queryset(self):
        user = self.request.user
        qs = FeeStructure.objects.all()
        if user.role != 'super_admin':
            qs = qs.filter(school=user.school)

        grade = self.request.query_params.get('grade')
        if grade:
            qs = qs.filter(grade_id=grade)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        if user.role != 'super_admin':
            serializer.save(school=user.school)
        else:
            serializer.save()


class FeeStructureDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = FeeStructureSerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH']:
            return [IsAuthenticated(), IsSuperAdminOrSchoolAdmin(), GlobalTenantPermission()]
        return [IsAuthenticated(), GlobalTenantPermission()]

    def get_queryset(self):
        user = self.request.user
        qs = FeeStructure.objects.all()
        if user.role != 'super_admin':
            qs = qs.filter(school=user.school)
        return qs


class FeeInstallmentListCreateView(generics.ListCreateAPIView):
    serializer_class = FeeInstallmentSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsSuperAdminOrSchoolAdmin(), GlobalTenantPermission()]
        return [IsAuthenticated(), GlobalTenantPermission()]

    def get_queryset(self):
        user = self.request.user
        qs = FeeInstallment.objects.all()
        if user.role == 'super_admin':
            pass
        elif user.role == 'school_admin':
            qs = qs.filter(student__school=user.school)
        elif user.role == 'student':
            qs = qs.filter(student=user)
        else:
            return FeeInstallment.objects.none()

        student = self.request.query_params.get('student')
        fee_structure = self.request.query_params.get('fee_structure')
        if student:
            qs = qs.filter(student_id=student)
        if fee_structure:
            qs = qs.filter(fee_structure_id=fee_structure)
        return qs.select_related('student', 'fee_structure')


class FeeInstallmentDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = FeeInstallmentSerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH']:
            return [IsAuthenticated(), IsSuperAdminOrSchoolAdmin(), GlobalTenantPermission()]
        return [IsAuthenticated(), GlobalTenantPermission()]

    def get_queryset(self):
        user = self.request.user
        qs = FeeInstallment.objects.all()
        if user.role == 'super_admin':
            pass
        elif user.role == 'school_admin':
            qs = qs.filter(student__school=user.school)
        elif user.role == 'student':
            qs = qs.filter(student=user)
        else:
            return FeeInstallment.objects.none()
        return qs.select_related('student', 'fee_structure')


class FeePaymentListCreateView(generics.ListCreateAPIView):
    serializer_class = FeePaymentSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsSuperAdminOrSchoolAdmin(), GlobalTenantPermission()]
        return [IsAuthenticated(), GlobalTenantPermission()]

    def get_queryset(self):
        user = self.request.user
        qs = FeePayment.objects.all()

        if user.role == 'super_admin':
            pass
        elif user.role == 'school_admin':
            qs = qs.filter(student__school=user.school)
        elif user.role == 'student':
            qs = qs.filter(student=user)
        else:
            return FeePayment.objects.none()

        student = self.request.query_params.get('student')
        status = self.request.query_params.get('status')
        if student:
            qs = qs.filter(student_id=student)
        if status:
            qs = qs.filter(status=status)
        return qs.select_related(
            'student', 'fee_structure__category', 'fee_structure__academic_session', 'installment', 'collected_by'
        )

    def perform_create(self, serializer):
        serializer.save(collected_by=self.request.user)


class FeePaymentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = FeePaymentSerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsSuperAdminOrSchoolAdmin(), GlobalTenantPermission()]
        return [IsAuthenticated(), GlobalTenantPermission()]

    def get_queryset(self):
        user = self.request.user
        qs = FeePayment.objects.all()

        if user.role == 'super_admin':
            pass
        elif user.role == 'school_admin':
            qs = qs.filter(student__school=user.school)
        elif user.role == 'student':
            qs = qs.filter(student=user)
        else:
            return FeePayment.objects.none()

        return qs.select_related(
            'student', 'fee_structure__category', 'fee_structure__academic_session', 'installment', 'collected_by'
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, GlobalTenantPermission])
def generate_fee_receipt(request, payment_id):
    try:
        payment = FeePayment.objects.select_related(
            'student', 'fee_structure__category', 'fee_structure__school', 'collected_by'
        ).get(id=payment_id)

        user = request.user
        if user.role == 'super_admin':
            pass
        elif user.role == 'school_admin':
            if payment.student.school != user.school:
                return Response({'error': 'Access denied'}, status=403)
        elif user.role == 'student':
            if payment.student != user:
                return Response({'error': 'Access denied'}, status=403)
        else:
            return Response({'error': 'Access denied'}, status=403)

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        school = payment.fee_structure.school
        if getattr(school, 'logo', None):
            try:
                from reportlab.platypus import Image
                story.append(Image(school.logo.path, width=100, height=50))
            except Exception:
                pass

        story.append(Paragraph(f"<b>{school.name}</b>", styles['Title']))
        if school.address:
            story.append(Paragraph(f"{school.address}", styles['Normal']))
        story.append(Paragraph(f"{school.city}, {school.state} {school.pincode}".strip(', '), styles['Normal']))
        story.append(Paragraph(f"Phone: {school.contact_phone or 'N/A'} | Email: {school.contact_email or 'N/A'}", styles['Normal']))
        story.append(Spacer(1, 16))

        story.append(Paragraph("<b>FEE RECEIPT</b>", styles['Heading1']))
        story.append(Spacer(1, 12))

        payment_rows = [
            ['Receipt Number:', payment.receipt_number or f"RCPT-{payment.id}"],
            ['Payment Date:', payment.payment_date.strftime('%d/%m/%Y')],
            ['Student Name:', payment.student.full_name],
            ['Fee Category:', payment.fee_structure.category.name],
            ['Payment Mode:', payment.payment_mode.title()],
            ['Transaction ID:', payment.transaction_id or 'N/A'],
            ['Collected By:', payment.collected_by.full_name if payment.collected_by else 'N/A'],
        ]

        if payment.installment:
            payment_rows.insert(4, ['Installment:', f"{payment.installment.installment_number} of {payment.fee_structure.installments}"])
            payment_rows.insert(5, ['Due Date:', payment.installment.due_date.strftime('%d/%m/%Y')])
        elif payment.due_date:
            payment_rows.insert(4, ['Due Date:', payment.due_date.strftime('%d/%m/%Y')])

        summary_rows = [
            ['Base Amount:', f"₹{payment.amount_due:.2f}"],
            ['Discount:', f"₹{payment.discount_amount:.2f}"],
            ['Scholarship:', f"₹{payment.scholarship_amount:.2f}"],
            ['Late Fee:', f"₹{payment.late_fee_amount:.2f}"],
            ['Total Due:', f"₹{payment.total_due:.2f}"],
            ['Paid Amount:', f"₹{payment.amount_paid:.2f}"],
            ['Balance Due:', f"₹{payment.balance_due:.2f}"],
        ]

        table = Table(payment_rows, colWidths=[150, 300])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(table)
        story.append(Spacer(1, 18))

        summary_table = Table(summary_rows, colWidths=[150, 300])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 24))

        story.append(Paragraph('Thank you for your payment!', styles['Normal']))
        story.append(Paragraph('This receipt is valid for accounting and verification purposes.', styles['Italic']))

        doc.build(story)
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="fee_receipt_{payment.receipt_number or payment.id}.pdf"'
        return response

    except FeePayment.DoesNotExist:
        return Response({'error': 'Payment not found'}, status=404)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception('Fee receipt generation failed for payment %s', payment_id)
        return Response({'error': 'Unable to generate fee receipt at this time.'}, status=500)
