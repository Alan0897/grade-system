from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Student(models.Model):
    name = models.CharField("學生姓名", max_length=100)
    student_id = models.CharField("學號", max_length=20, unique=True)

    def __str__(self):
        return f"{self.name} ({self.student_id})"


class Profile(models.Model):
    ROLE_CHOICES = (
        ("student", "學生"),
        ("teacher", "教師"),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField("身份", max_length=10, choices=ROLE_CHOICES, default="student")
    avatar = models.ImageField("大頭貼", upload_to="avatars/", null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

class Course(models.Model):
    name = models.CharField("課名", max_length=100)
    course_code = models.CharField("課號", max_length=20, unique=True)
    # legacy teacher name field (kept for backward compatibility)
    teacher = models.CharField("任課老師", max_length=50, blank=True)
    # link to User who is the teacher (nullable)
    teacher_user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="teaching_courses")

    def __str__(self):
        return f"{self.name} ({self.course_code})"


class Comment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField("內容")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.author.username} on {self.course.course_code}"

class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    midterm_score = models.FloatField("期中分數", default=0)
    final_score = models.FloatField("期末分數", default=0)

    class Meta:
        unique_together = ('student', 'course')

    @property
    def average(self):
        return (self.midterm_score + self.final_score) / 2

    def __str__(self):
        return f"{self.student} - {self.course}"


# Ensure a Profile exists for each User after save
@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance, created, **kwargs):
    # Use get_or_create unconditionally to avoid race conditions with admin inlines
    # (admin user add view creates the inline Profile; calling create twice causes UNIQUE constraint)
    Profile.objects.get_or_create(user=instance)
