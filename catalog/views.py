from django.shortcuts import render, get_object_or_404, redirect
from .models import Student, Course, Enrollment, Profile, Comment
from django.db import IntegrityError
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required


# helper: 取得目前登入的 Student（若無則回傳 None）
def get_current_student(request):
    if not request.user.is_authenticated:
        return None
    # 嘗試以 username (作為 student_id) 找 Student
    student = Student.objects.filter(student_id=request.user.username).first()
    if student:
        return student
    # 嘗試以使用者姓名匹配（如果設定 first_name）
    if request.user.first_name:
        student = Student.objects.filter(name=request.user.first_name).first()
        if student:
            return student
    # 若使用者為學生角色但尚未有 Student 紀錄，自動建立一個（便利性）
    if hasattr(request.user, 'profile') and request.user.profile.role == 'student':
        student, created = Student.objects.get_or_create(student_id=request.user.username, defaults={'name': request.user.first_name or request.user.username})
        return student
    return None


# 首頁
def index(request):
    # Provide some dashboard counts for the homepage
    course_count = Course.objects.count()
    student_count = Student.objects.count()
    my_avg = None
    if request.user.is_authenticated:
        student = get_current_student(request)
        if student:
            enrollments = Enrollment.objects.filter(student=student)
            my_avg = round(sum(e.average for e in enrollments) / len(enrollments), 2) if enrollments else None

    return render(request, 'index.html', {
        'course_count': course_count,
        'student_count': student_count,
        'my_avg': my_avg,
    })


# 註冊（簡易）
def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        name = request.POST.get('name')
        student_id = request.POST.get('student_id')
        if username and password:
            user = User.objects.create_user(username=username, password=password)
            user.first_name = name or ''
            user.save()
            # create Student record linking by student_id (site registration only creates students)
            Student.objects.create(name=name or username, student_id=student_id or username)
            # ensure profile exists and is explicitly a student
            prof, _ = Profile.objects.get_or_create(user=user)
            prof.role = 'student'
            prof.save()
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
            return redirect('course_list')
    return render(request, 'register.html')


# 登入/登出 可使用 Django 的內建視圖或簡易實作
def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('course_list')
    return render(request, 'login.html')


def user_logout(request):
    logout(request)
    return redirect('index')


@login_required
def edit_profile(request):
    # allow editing own name and avatar
    user = request.user
    prof, _ = Profile.objects.get_or_create(user=user)
    if request.method == 'POST':
        name = request.POST.get('name')
        avatar = request.FILES.get('avatar')
        if name is not None:
            user.first_name = name
            user.save()
            # also update Student.name if exists
            try:
                student = Student.objects.get(student_id=user.username)
                student.name = name
                student.save()
            except Student.DoesNotExist:
                pass
        if avatar:
            prof.avatar = avatar
            prof.save()
        return redirect('course_list')
    avatar_url = prof.avatar.url if prof.avatar else None
    return render(request, 'edit_profile.html', {'name': user.first_name, 'avatar_url': avatar_url})


# 課程列表
@login_required
def course_list(request):
    student = get_current_student(request)
    enrollments = Enrollment.objects.filter(student=student) if student else []
    avg_score = round(sum(e.average for e in enrollments) / len(enrollments), 2) if enrollments else 0

    # 所有課程
    all_courses = Course.objects.all()

    # 已選課程的課程 id
    enrolled_course_ids = enrollments.values_list('course__id', flat=True) if student else []

    # 可加選課程 (排除已選課)
    available_courses = [c for c in all_courses if c.id not in enrolled_course_ids]

    # role flags for template
    is_teacher = hasattr(request.user, 'profile') and request.user.profile.role == 'teacher'
    is_student = hasattr(request.user, 'profile') and request.user.profile.role == 'student' and student is not None

    # 教師的開課清單（如果是教師）
    teaching_courses = []
    if is_teacher:
        teaching_courses = Course.objects.filter(teacher_user=request.user)

    return render(request, 'course_list.html', {
        'enrollments': enrollments,
        'avg_score': avg_score,
        'courses': available_courses,
        'is_teacher': is_teacher,
        'is_student': is_student,
        'teaching_courses': teaching_courses,
    })


# 課程詳細頁（含留言）
@login_required
def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    # By default teacher/staff see all enrollments; students should only see their own
    current_student = get_current_student(request)
    if hasattr(request.user, 'profile') and getattr(request.user.profile, 'role', None) == 'student' and current_student:
        enrollments = Enrollment.objects.filter(course=course, student=current_student)
    else:
        enrollments = Enrollment.objects.filter(course=course)
    comments = course.comments.select_related('author').order_by('-created_at')

    # determine permissions: teacher of this course or staff can see all scores
    is_course_teacher = hasattr(request.user, 'profile') and request.user.profile.role == 'teacher' and course.teacher_user == request.user
    is_staff = request.user.is_staff

    if request.method == 'POST' and request.POST.get('comment'):
        Comment.objects.create(course=course, author=request.user, content=request.POST.get('comment'))
        return redirect('course_detail', pk=pk)

    return render(request, 'course_detail.html', {
        'course': course,
        'enrollments': enrollments,
        'comments': comments,
        'is_course_teacher': is_course_teacher,
        'is_staff': is_staff,
        'current_student': current_student,
    })


# 新增課程（管理者或教師）
@login_required
def add_course(request):
    # only teachers can add courses via site
    if not (hasattr(request.user, 'profile') and request.user.profile.role == 'teacher'):
        return redirect('course_list')

    if request.method == 'POST':
        name = request.POST.get('name')
        course_code = request.POST.get('course_code')
        try:
            course = Course.objects.create(name=name, course_code=course_code, teacher_user=request.user)
        except IntegrityError:
            pass
        return redirect('course_list')
    return render(request, 'add_course.html')


# 學生加選課程
@login_required
def enroll_course(request, course_id):
    # only students can enroll
    if not (hasattr(request.user, 'profile') and request.user.profile.role == 'student'):
        return redirect('course_list')
    student = get_current_student(request)
    if not student:
        return redirect('course_list')
    course = get_object_or_404(Course, id=course_id)
    Enrollment.objects.get_or_create(student=student, course=course)
    return redirect('course_list')


# 學生退選課程
@login_required
def drop_course(request, course_id):
    student = get_current_student(request)
    if not student:
        return redirect('course_list')
    Enrollment.objects.filter(student=student, course_id=course_id).delete()
    return redirect('course_list')


# 教師檢視修課名單與輸入成績
@login_required
def teacher_manage_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    # 權限檢查：只有該課程的任課教師或管理員可以管理
    is_course_teacher = hasattr(request.user, 'profile') and request.user.profile.role == 'teacher' and course.teacher_user == request.user
    if not (is_course_teacher or request.user.is_staff):
        return redirect('course_detail', pk=course_id)

    enrollments = Enrollment.objects.filter(course=course)
    comments = course.comments.select_related('author').order_by('-created_at')

    if request.method == 'POST':
        # If a comment is present, create it (teachers may leave notes)
        if request.POST.get('comment'):
            Comment.objects.create(course=course, author=request.user, content=request.POST.get('comment'))
            return redirect('teacher_manage_course', course_id=course_id)

        # Otherwise expect grade fields mid_{enrollment_id}, final_{enrollment_id}
        for e in enrollments:
            mid = request.POST.get(f'mid_{e.id}')
            final = request.POST.get(f'final_{e.id}')
            if mid is not None:
                try:
                    e.midterm_score = float(mid)
                except ValueError:
                    pass
            if final is not None:
                try:
                    e.final_score = float(final)
                except ValueError:
                    pass
            e.save()
        return redirect('teacher_manage_course', course_id=course_id)

    return render(request, 'teacher_manage_course.html', {
        'course': course,
        'enrollments': enrollments,
        'comments': comments,
    })


# 編輯留言（只能編輯自己的留言）
@login_required
def edit_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if comment.author != request.user:
        return redirect('course_detail', pk=comment.course.id)
    if request.method == 'POST':
        comment.content = request.POST.get('content')
        comment.save()
        # If current user is the course teacher, return to teacher manage page
        course = comment.course
        if hasattr(request.user, 'profile') and request.user.profile.role == 'teacher' and course.teacher_user == request.user:
            return redirect('teacher_manage_course', course_id=course.id)
        return redirect('course_detail', pk=comment.course.id)
    return render(request, 'edit_comment.html', {'comment': comment})
