
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Student, Course, Enrollment, Profile, Comment
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('name', 'student_id')
    search_fields = ('name', 'student_id')
    verbose_name = "學生"
    verbose_name_plural = "學生列表"


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'midterm_score', 'final_score', 'average')
    list_filter = ('course',)
    search_fields = ('student__name', 'course__name')
    verbose_name = "修課紀錄"
    verbose_name_plural = "修課紀錄列表"


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name = '個人資料'
    fields = ('role', 'avatar')
    readonly_fields = ()


class CustomUserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    actions = ['make_teacher', 'make_student']

    def get_inline_instances(self, request, obj=None):
        # Avoid rendering the Profile inline on the user "add" form to prevent
        # double-creation of Profile (admin add + post_save signal creating one).
        if obj is None:
            return []
        return super().get_inline_instances(request, obj)

    def make_teacher(self, request, queryset):
        updated = 0
        for user in queryset:
            prof, _ = Profile.objects.get_or_create(user=user)
            if prof.role != 'teacher':
                prof.role = 'teacher'
                prof.save()
                updated += 1
        self.message_user(request, f"已將 {updated} 位使用者設為教師。", messages.SUCCESS)
    make_teacher.short_description = "設為教師"

    def make_student(self, request, queryset):
        updated = 0
        for user in queryset:
            prof, _ = Profile.objects.get_or_create(user=user)
            if prof.role != 'student':
                prof.role = 'student'
                prof.save()
                updated += 1
        self.message_user(request, f"已將 {updated} 位使用者設為學生。", messages.SUCCESS)
    make_student.short_description = "設為學生"


# unregister the default User admin and register a custom one with Profile inline
try:
    admin.site.unregister(User)
except Exception:
    pass
admin.site.register(User, CustomUserAdmin)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('course', 'author', 'created_at')
    search_fields = ('course__name', 'author__username', 'content')
    readonly_fields = ('created_at', 'updated_at')


# add a small admin view to create teacher accounts quickly
def create_teacher_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        email = request.POST.get('email')
        avatar = request.FILES.get('avatar')
        if username and password:
            user = User.objects.create_user(username=username, password=password, email=email, first_name=first_name or '')
            prof, _ = Profile.objects.get_or_create(user=user)
            prof.role = 'teacher'
            if avatar:
                prof.avatar = avatar
            prof.save()
            messages.success(request, f'教師帳號 {username} 已建立。')
            return redirect('admin:auth_user_changelist')
        else:
            messages.error(request, '請提供帳號與密碼')
    return render(request, 'admin/create_teacher.html')


# hook the view into admin urls
orig_get_urls = admin.site.get_urls

def get_urls():
    urls = [
        path('create-teacher/', admin.site.admin_view(create_teacher_view), name='create_teacher'),
    ]
    return urls + orig_get_urls()

admin.site.get_urls = get_urls


# improve CourseAdmin to allow setting teacher_user directly and searching
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'course_code', 'teacher_user')
    search_fields = ('name', 'course_code', 'teacher_user__username', 'teacher')
    list_filter = ('teacher_user',)
    raw_id_fields = ('teacher_user',)
    fields = ('name', 'course_code', 'teacher_user', 'teacher')
    verbose_name = "課程"
    verbose_name_plural = "課程列表"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "teacher_user":
            kwargs["queryset"] = User.objects.filter(profile__role='teacher')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
