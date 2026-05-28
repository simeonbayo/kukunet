from django.db import models

class CourseCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order']
        verbose_name_plural = "Course Categories"
    
    def __str__(self):
        return self.name

class Course(models.Model):
    LEVEL_CHOICES = [
        ('BEGINNER', 'Beginner'),
        ('INTERMEDIATE', 'Intermediate'),
        ('ADVANCED', 'Advanced'),
    ]
    
    instructor = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='courses')
    category = models.ForeignKey(CourseCategory, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    short_description = models.CharField(max_length=200)
    thumbnail = models.ImageField(upload_to='courses/thumbnails/')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='BEGINNER')
    duration_hours = models.IntegerField(default=1)
    is_published = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    @property
    def total_lessons(self):
        return self.lessons.count()
    
    @property
    def total_enrollments(self):
        return self.enrollments.count()

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    video_url = models.URLField()  # YouTube or Vimeo URL
    video_duration = models.IntegerField(default=0)  # seconds
    notes_file = models.FileField(upload_to='courses/notes/', null=True, blank=True)
    content = models.TextField(blank=True)  # Rich text content
    position = models.IntegerField(default=0)
    is_free_preview = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['position']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Enrollment(models.Model):
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    progress_percent = models.IntegerField(default=0)
    last_accessed = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['user', 'course']
    
    def __str__(self):
        return f"{self.user.full_name} - {self.course.title}"

class LessonProgress(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_position = models.IntegerField(default=0)  # Video position in seconds
    
    class Meta:
        unique_together = ['enrollment', 'lesson']

class Quiz(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='quizzes')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=200)
    passing_score = models.IntegerField(default=70)  # Percentage
    
    def __str__(self):
        return f"Quiz: {self.title}"

class QuizQuestion(models.Model):
    QUESTION_TYPES = [
        ('MCQ', 'Multiple Choice'),
        ('TRUE_FALSE', 'True/False'),
        ('TEXT', 'Text Answer'),
    ]
    
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='MCQ')
    points = models.IntegerField(default=1)
    order = models.IntegerField(default=0)
    
    def __str__(self):
        return self.question[:50]

class QuizOption(models.Model):
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name='options')
    option_text = models.CharField(max_length=200)
    is_correct = models.BooleanField(default=False)

class Certificate(models.Model):
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='certificates')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    certificate_number = models.CharField(max_length=50, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    download_count = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['user', 'course']
    
    def save(self, *args, **kwargs):
        if not self.certificate_number:
            import uuid
            self.certificate_number = f"KUKU-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)