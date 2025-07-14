from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.course_list, name='course_list'),
    path('course/<int:pk>/', views.course_detail, name='course_detail'),
    path('course/<int:pk>/enroll/', views.enroll_course, name='enroll_course'),
    path('search/', views.search, name='search'),
    path('my-courses/', views.my_courses, name='my_courses'),
    path('profile/', views.profile, name='profile'),
    path('course/<int:pk>/complete/', views.mark_completed, name='mark_completed'),
    path('categories/', views.categories_list, name='categories_list'),
    path('categories/<int:category_id>/', views.category_courses, name='category_courses'),
    path('lesson/<int:lesson_id>/complete/', views.mark_lesson_complete, name='mark_lesson_complete'),
    path('instructor/dashboard/', views.instructor_dashboard, name='instructor_dashboard'),
    path('support/submit/', views.submit_ticket, name='submit_ticket'),
    path('support/thanks/', views.ticket_thanks, name='ticket_thanks'),
    path('course/<int:course_id>/forum/', views.course_forum, name='course_forum'),
    path('post/<int:post_id>/reply/', views.reply_post, name='reply_post'),
    path('course/<int:course_id>/certificates/', views.download_certificate, name='download_certificate'),
    # path('verify/<int:enrollment_id>/', views.verify_certificate, name='verify_certificate'),
    path('quiz/<int:quiz_id>/', views.take_quiz, name='take_quiz'),
    path('bundles/', views.bundle_list, name='bundle_list'),
    path('bundles/buy/<int:bundle_id>/', views.buy_bundle, name='buy_bundle'),
    path('bundles/success/<int:order_id>/', views.bundle_success, name='bundle_success'),
    path('lesson/<int:lesson_id>/video/', views.stream_video, name='stream_video'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)