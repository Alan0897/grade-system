from django.contrib import admin
from django.urls import path
from catalog import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('courses/', views.course_list, name='course_list'),
    path('courses/<int:pk>/', views.course_detail, name='course_detail'),
    path('courses/add/', views.add_course, name='add_course'),  # 新增課程
    path('enroll/<int:course_id>/', views.enroll_course, name='enroll_course'),
    path('drop/<int:course_id>/', views.drop_course, name='drop_course'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('teacher/course/<int:course_id>/', views.teacher_manage_course, name='teacher_manage_course'),
    path('comment/edit/<int:comment_id>/', views.edit_comment, name='edit_comment'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
