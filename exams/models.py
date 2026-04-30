from django.db import models


class Exam(models.Model):
    EXAM_TYPE_CHOICES = [
        ('unit_test', 'Unit Test'), ('mid_term', 'Mid Term'),
        ('final', 'Final'), ('pre_board', 'Pre Board'), ('practical', 'Practical'),
    ]
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='exams')
    academic_session = models.ForeignKey(
        'academics.AcademicSession', on_delete=models.CASCADE, related_name='exams'
    )
    name = models.CharField(max_length=200)
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.school.name}"


class Question(models.Model):
    QUESTION_TYPE_CHOICES = [
        ('multiple_choice', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('short_answer', 'Short Answer'),
        ('long_answer', 'Long Answer'),
        ('fill_blank', 'Fill in the Blank'),
        ('matching', 'Matching'),
        ('essay', 'Essay'),
    ]

    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='questions')
    subject = models.ForeignKey('academics.Subject', on_delete=models.CASCADE, related_name='questions')
    grade = models.ForeignKey('academics.Grade', on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES)
    options = models.TextField(blank=True, null=True)  # For multiple choice options (JSON string)
    correct_answer = models.TextField(blank=True)  # Correct answer or explanation
    marks = models.IntegerField(default=1)
    difficulty_level = models.CharField(max_length=20, choices=[
        ('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')
    ], default='medium')
    tags = models.TextField(blank=True, null=True)  # For categorization (JSON string)
    created_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='created_questions')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.question_type}: {self.question_text[:50]}..."


class ExamPaper(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='papers')
    subject = models.ForeignKey('academics.Subject', on_delete=models.CASCADE, related_name='exam_papers')
    grade = models.ForeignKey('academics.Grade', on_delete=models.CASCADE, related_name='exam_papers')
    title = models.CharField(max_length=200)
    instructions = models.TextField(blank=True)
    total_marks = models.IntegerField(default=100)
    duration_minutes = models.IntegerField(default=60)
    created_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='created_exam_papers')
    created_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.exam.name} - {self.subject.name} - {self.title}"


class ExamPaperQuestion(models.Model):
    exam_paper = models.ForeignKey(ExamPaper, on_delete=models.CASCADE, related_name='questions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='exam_paper_questions')
    order = models.IntegerField(default=0)
    marks_allocated = models.IntegerField(default=1)

    class Meta:
        ordering = ['order']
        unique_together = ['exam_paper', 'question']

    def __str__(self):
        return f"Q{self.order}: {self.question.question_text[:30]}..."


class ExamSchedule(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='schedules')
    grade = models.ForeignKey('academics.Grade', on_delete=models.CASCADE, related_name='exam_schedules', null=True)
    subject = models.ForeignKey('academics.Subject', on_delete=models.CASCADE, related_name='exam_schedules')
    exam_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    max_marks = models.IntegerField(default=100)
    passing_marks = models.IntegerField(default=33)
    venue = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.exam.name} - {self.subject.name} - {self.exam_date}"


class ExamResult(models.Model):
    GRADE_CHOICES = [
        ('A+', 'A+'), ('A', 'A'), ('B+', 'B+'), ('B', 'B'),
        ('C', 'C'), ('D', 'D'), ('E', 'E (Fail)'),
    ]
    exam_schedule = models.ForeignKey(ExamSchedule, on_delete=models.CASCADE, related_name='results')
    student = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='results')
    marks_obtained = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    grade = models.CharField(max_length=5, choices=GRADE_CHOICES, blank=True)
    is_absent = models.BooleanField(default=False)
    remarks = models.CharField(max_length=200, blank=True)
    entered_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, related_name='entered_results'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('exam_schedule', 'student')

    def __str__(self):
        return f"{self.student.full_name} - {self.exam_schedule.subject.name} - {self.marks_obtained}"

    @property
    def percentage(self):
        if self.exam_schedule.max_marks:
            return round((float(self.marks_obtained) / self.exam_schedule.max_marks) * 100, 2)
        return 0

    @property
    def is_pass(self):
        return self.marks_obtained >= self.exam_schedule.passing_marks
