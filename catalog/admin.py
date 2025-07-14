from django.contrib import admin
from .models import Category, Course, Enrollment, Review, Lesson, LessonProgress, SupportTicket, Bundle

admin.site.register(Bundle)
admin.site.register(SupportTicket)
admin.site.register(Lesson)
admin.site.register(Category)
admin.site.register(Course)