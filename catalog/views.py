from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db.models import Q
from .forms import ReviewForm, SupportTicketForm, PostForm, ReplyForm
from .models import Course, Enrollment, Category, Review, Lesson, LessonProgress, SupportTicket, Post, Reply, QuizResult, Bundle, BundleOrder

from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import HexColor, Color
from io import BytesIO
import os
from django.conf import settings
from reportlab.graphics.shapes import Drawing, Path
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import qr
import uuid
# from pathlib import Path
from reportlab.pdfgen import canvas
from django.core.mail import send_mail
import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.http import FileResponse, Http404
from django.db.models import Count
from django.db import models
from django.contrib.auth.models import User


def course_list(request):
    courses = Course.objects.all()
    return render(request, 'catalog/course_list.html', {'courses': courses})

def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    reviews = course.reviews.all()
    lessons = course.lessons.all()
    total_lessons = lessons.count()

    # Default values
    enrolled = False
    lessons_done = 0
    lesson_progress = {}

    # Check enrollment and progress if user is authenticated
    if request.user.is_authenticated:
        enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()
        lessons_done = LessonProgress.objects.filter(user=request.user, lesson__course=course, completed=True).count()

        # Get progress for each lesson
        progresses = LessonProgress.objects.filter(user=request.user, lesson__in=lessons)
        progress_map = {p.lesson_id: p for p in progresses}
        lesson_progress = {lesson.id: progress_map.get(lesson.id) for lesson in lessons}

    # Handle review submission
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('login')
        
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.course = course
            review.save()
            return redirect('course_detail', pk=pk)
    else:
        form = ReviewForm()

    # Calculate progress percentage
    progress = int((lessons_done / total_lessons) * 100) if total_lessons > 0 else 0

    return render(request, 'catalog/course_detail.html', {
        'course': course,
        'reviews': reviews,
        'lessons': lessons,
        'form': form,
        'enrolled': enrolled,
        'progress': progress,
        'lesson_progress': lesson_progress,
        'lessons_done': lessons_done,
        'total_lessons': total_lessons,
    })

def search(request):
    query = request.GET.get('q')
    category_id = request.GET.get('category')
    courses = Course.objects.all()

    if query:
        courses = courses.filter(
        Q(title__icontains=query) |
        Q(description__icontains=query) |
        Q(instructor__username__icontains=query) |
        Q(instructor__first_name__icontains=query) |
        Q(instructor__last_name__icontains=query)
    )

    if category_id:
        courses = courses.filter(category_id=category_id)

    categories = Category.objects.all()

    return render(request, 'catalog/search_results.html', {
        'results': courses,
        'query': query,
        'categories': categories,
        'selected_category': int(category_id) if category_id else None,
    })



@login_required
def enroll_course(request, pk):
    course = get_object_or_404(Course, pk=pk)
    Enrollment.objects.get_or_create(user=request.user, course=course)
    return HttpResponseRedirect(reverse('course_detail', args=[pk]))


@login_required
def my_courses(request):
    enrollments = Enrollment.objects.filter(user=request.user)
    return render(request, 'catalog/my_courses.html', {'enrollments': enrollments})

def categories_list(request):
    categories = Category.objects.all()
    return render(request, 'catalog/categories_list.html', {'categories': categories})

def category_courses(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    courses = Course.objects.filter(category=category)
    return render(request, 'catalog/category_courses.html', {'category': category, 'courses': courses})

@login_required
def profile(request):
    enrollments = Enrollment.objects.filter(user=request.user)
    completed_enrollments = enrollments.filter(is_completed=True)
    reviews = Review.objects.filter(user=request.user)

    return render(request, 'catalog/profile.html', {
        'enrollments': enrollments,
        'completed_enrollments': completed_enrollments,
        'reviews': reviews,
    })


@login_required
def mark_completed(request, pk):
    enrollment = get_object_or_404(Enrollment, user=request.user, course__pk=pk)
    enrollment.is_completed = True
    enrollment.save()
    return redirect('course_detail', pk=pk)

from .models import Lesson, LessonProgress

@login_required
def mark_lesson_complete(request, lesson_id):
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    progress, created = LessonProgress.objects.get_or_create(
        user=request.user,
        lesson=lesson,
        defaults={'completed': True}
    )
    if not created:
        progress.completed = True
        progress.save()
    return redirect('course_detail', pk=lesson.course.pk)

@login_required
def instructor_dashboard(request):
    # Only show courses for the logged-in instructor
    my_courses = Course.objects.filter(instructor=request.user)
    course_data = []
    for course in my_courses:
        enrolled_students = Enrollment.objects.filter(course=course)
        course_data.append({
            'course': course,
            'enrollments': enrolled_students,
            'num_enrollments': enrolled_students.count()
        })
    return render(request, 'catalog/instructor_dashboard.html', {
        'course_data': course_data
    })

@login_required
def submit_ticket(request):
    if request.method == 'POST':
        form = SupportTicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.user = request.user
            ticket.save()
            return redirect('ticket_thanks')
    else:
        form = SupportTicketForm()
    return render(request, 'catalog/submit_ticket.html', {'form': form})

def ticket_thanks(request):
    return render(request, 'catalog/ticket_thanks.html')

@login_required
def course_forum(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    posts = Post.objects.filter(course=course).order_by('-created_at')

    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            new_post = form.save(commit=False)
            new_post.user = request.user
            new_post.course = course
            new_post.save()

            # Notify instructor
            send_mail(
                subject=f"New Forum Post in {course.title}",
                message=f"{request.user.username} posted a message in {course.title}'s discussion forum.",
                from_email=None,
                recipient_list=[course.instructor.email],
            )

            return redirect('course_forum', course_id=course_id)
        else:
            form = PostForm()

        return render(request, 'catalog/course_forum.html', {
            'course': course,
            'posts': posts,
            'form': form
})

@login_required
def reply_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.method == 'POST':
        form = ReplyForm(request.POST)
        if form.is_valid():
            new_reply = form.save(commit=False)
            new_reply.user = request.user
            new_reply.post = post
            new_reply.save()
            return redirect('course_forum', course_id=post.course.pk)
    return redirect('course_forum', course_id=post.course.pk)


@login_required
def download_certificate(request, course_id):
    enrollment = get_object_or_404(
        Enrollment, user=request.user, course_id=course_id, is_completed=True
    )
    course = enrollment.course

    certificate_id = f"CERT-{uuid.uuid4().hex[:10].upper()}"

    # Calculate grade
    quizzes = course.quizzes.all()
    quiz_results = QuizResult.objects.filter(user=request.user, quiz__in=quizzes)
    if quiz_results.exists():
        total_questions = sum(result.total_questions for result in quiz_results)
        total_correct = sum(result.score for result in quiz_results)
        grade_percent = (total_correct / total_questions) * 100 if total_questions else 0
        grade_display = f"{grade_percent:.1f}%"
    else:
        grade_display = "N/A"

    enrollment.grade = grade_display
    enrollment.save()

    # Process skills
    if hasattr(course, "skills"):
        if isinstance(course.skills, list):
            skills = course.skills or ["General Competencies"]
        elif isinstance(course.skills, str):
            skills = [skill.strip() for skill in course.skills.split(',') if skill.strip()]
            skills = skills or ["General Competencies"]
        else:
            try:
                skills = [skill.name for skill in course.skills.all()] or ["General Competencies"]
            except AttributeError:
                skills = ["General Competencies"]
    else:
        skills = ["Software Development", "Problem Solving", "Technical Analysis", "Project Management"]

    # Create PDF buffer
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter)

    # === PREMIUM MINIMALIST BACKGROUND ===
    def create_premium_background():
    # Clean white base
        p.setFillColor(HexColor("#ffffff"))
        p.rect(0, 0, width, height, stroke=0, fill=1)

        # Subtle geometric accent - top right
        p.setFillColor(HexColor("#fafbfc"))
        path1 = p.beginPath()
        path1.moveTo(width * 0.75, height)
        path1.lineTo(width, height)
        path1.lineTo(width, height * 0.75)
        path1.close()
        p.drawPath(path1, fill=1, stroke=0)

        # Subtle geometric accent - bottom left
        p.setFillColor(HexColor("#f8f9fa"))
        path2 = p.beginPath()
        path2.moveTo(0, 0)
        path2.lineTo(width * 0.25, 0)
        path2.lineTo(0, height * 0.25)
        path2.close()
        p.drawPath(path2, fill=1, stroke=0)

    create_premium_background()

    # === ELEGANT MINIMAL BORDER ===
    def create_minimal_border():
        # Single elegant border
        p.setStrokeColor(HexColor("#e9ecef"))
        p.setLineWidth(1)
        p.rect(40, 40, width - 80, height - 80, stroke=1, fill=0)
        
        # Accent corners
        corner_length = 30
        p.setStrokeColor(HexColor("#6c757d"))
        p.setLineWidth(3)
        
        # Top-left corner
        p.line(40, height - 40, 40 + corner_length, height - 40)
        p.line(40, height - 40, 40, height - 40 - corner_length)
        
        # Top-right corner
        p.line(width - 40, height - 40, width - 40 - corner_length, height - 40)
        p.line(width - 40, height - 40, width - 40, height - 40 - corner_length)
        
        # Bottom-left corner
        p.line(40, 40, 40 + corner_length, 40)
        p.line(40, 40, 40, 40 + corner_length)
        
        # Bottom-right corner
        p.line(width - 40, 40, width - 40 - corner_length, 40)
        p.line(width - 40, 40, width - 40, 40 + corner_length)

    create_minimal_border()

    # === CLEAN HEADER ===
    def create_clean_header():
        # Institution name (smaller, elegant)
        p.setFont("Helvetica", 16)
        p.setFillColor(HexColor("#6c757d"))
        p.drawCentredString(width / 2, height - 80, "PROFESSIONAL LEARNING INSTITUTE")
        
        # Main certificate title
        p.setFont("Helvetica-Bold", 48)
        p.setFillColor(HexColor("#212529"))
        p.drawCentredString(width / 2, height - 130, "CERTIFICATE")
        
        # Subtitle
        p.setFont("Helvetica", 24)
        p.setFillColor(HexColor("#495057"))
        p.drawCentredString(width / 2, height - 160, "OF COMPLETION")
        
        # Elegant underline
        p.setStrokeColor(HexColor("#dee2e6"))
        p.setLineWidth(2)
        p.line(width / 2 - 150, height - 175, width / 2 + 150, height - 175)

    create_clean_header()

    # === CERTIFICATION STATEMENT ===
    def create_certification_statement():
        p.setFont("Helvetica", 18)
        p.setFillColor(HexColor("#6c757d"))
        p.drawCentredString(width / 2, height - 210, "This is to certify that")

    create_certification_statement()

    # === STUDENT NAME (PROMINENT) ===
    def create_student_name():
        student_name = request.user.get_full_name() or request.user.username
        
        # Name with elegant spacing
        p.setFont("Helvetica-Bold", 44)
        p.setFillColor(HexColor("#212529"))
        p.drawCentredString(width / 2, height - 260, student_name)
        
        # Refined underline
        name_width = len(student_name) * 20  # Approximate width
        p.setStrokeColor(HexColor("#6c757d"))
        p.setLineWidth(1)
        p.line(width / 2 - name_width / 2, height - 275, width / 2 + name_width / 2, height - 275)

    create_student_name()

    # === COURSE COMPLETION STATEMENT ===
    def create_course_statement():
        p.setFont("Helvetica", 18)
        p.setFillColor(HexColor("#6c757d"))
        p.drawCentredString(width / 2, height - 310, "has successfully completed the course")
        
        # Course title
        p.setFont("Helvetica-Bold", 28)
        p.setFillColor(HexColor("#212529"))
        p.drawCentredString(width / 2, height - 345, f'"{course.title}"')

    create_course_statement()

    # === COURSE DETAILS GRID ===
    def create_details_grid():
        details_y = height - 400
        
        # Grid background
        p.setFillColor(HexColor("#f8f9fa"))
        p.rect(width / 2 - 350, details_y - 25, 700, 50, stroke=0, fill=1)
        
        # Grid content
        course_duration = getattr(course, 'duration', '8 Weeks')
        learning_hours = getattr(course, 'total_hours', '40') + ' Hours'
        
        # Labels
        p.setFont("Helvetica", 12)
        p.setFillColor(HexColor("#6c757d"))
        p.drawCentredString(width / 2 - 200, details_y - 5, "DURATION")
        p.drawCentredString(width / 2, details_y - 5, "LEARNING HOURS")
        p.drawCentredString(width / 2 + 200, details_y - 5, "GRADE")
        
        # Values
        p.setFont("Helvetica-Bold", 16)
        p.setFillColor(HexColor("#212529"))
        p.drawCentredString(width / 2 - 200, details_y - 20, course_duration)
        p.drawCentredString(width / 2, details_y - 20, learning_hours)
        p.drawCentredString(width / 2 + 200, details_y - 20, grade_display)
        
        # Grid lines
        p.setStrokeColor(HexColor("#dee2e6"))
        p.setLineWidth(1)
        p.line(width / 2 - 100, details_y - 25, width / 2 - 100, details_y + 25)
        p.line(width / 2 + 100, details_y - 25, width / 2 + 100, details_y + 25)

    create_details_grid()

    # === SKILLS SECTION ===
    def create_skills_section():
        skills_y = height - 470
        
        # Skills header
        p.setFont("Helvetica", 14)
        p.setFillColor(HexColor("#6c757d"))
        p.drawCentredString(width / 2, skills_y, "SKILLS & COMPETENCIES")
        
        # Skills display (horizontal layout)
        displayed_skills = skills[:4]  # Show 4 skills max
        skill_spacing = 300
        start_x = width / 2 - (len(displayed_skills) - 1) * skill_spacing / 2
        
        p.setFont("Helvetica", 12)
        p.setFillColor(HexColor("#495057"))
        
        for idx, skill in enumerate(displayed_skills):
            x_pos = start_x + idx * skill_spacing
            p.drawCentredString(x_pos, skills_y - 20, skill)
            
            # Skill bullets
            p.setFillColor(HexColor("#6c757d"))
            p.circle(x_pos, skills_y - 35, 2, fill=1, stroke=0)
            p.setFillColor(HexColor("#495057"))

    create_skills_section()

    # === DATE SECTION ===
    def create_date_section():
        date_y = height - 530
        
        completion_date = getattr(enrollment, 'completed_at', None) or getattr(enrollment, 'enrolled_at', None)
        if completion_date:
            completion_date_str = completion_date.strftime('%B %d, %Y')
        else:
            completion_date_str = "Date Not Available"
        
        p.setFont("Helvetica", 14)
        p.setFillColor(HexColor("#6c757d"))
        p.drawCentredString(width / 2, date_y, f"Completed on {completion_date_str}")

    create_date_section()

    # === SIGNATURE SECTION ===
    def create_signature_section():
        sig_y = height - 580
        
        # Signature area
        instructor_user = course.instructor
        instructor_name = instructor_user.get_full_name() or instructor_user.username
        
        # Signature line
        p.setStrokeColor(HexColor("#6c757d"))
        p.setLineWidth(1)
        p.line(width / 2 - 100, sig_y, width / 2 + 100, sig_y)
        
        # Signature image or text
        signature_path = os.path.join(settings.BASE_DIR, 'catalog', 'static', 'images', 'signature.png')
        if os.path.exists(signature_path):
            p.drawImage(signature_path, width / 2 - 50, sig_y + 5, width=100, height=25, mask='auto')
        else:
            p.setFont("Helvetica-Oblique", 12)
            p.setFillColor(HexColor("#6c757d"))
            p.drawCentredString(width / 2, sig_y + 15, "Digital Signature")
        
        # Instructor name
        p.setFont("Helvetica-Bold", 14)
        p.setFillColor(HexColor("#212529"))
        p.drawCentredString(width / 2, sig_y - 15, instructor_name)
        
        # Title
        p.setFont("Helvetica", 10)
        p.setFillColor(HexColor("#6c757d"))
        p.drawCentredString(width / 2, sig_y - 30, "INSTRUCTOR")

    create_signature_section()

    # === MINIMAL LOGO SECTION ===
    def create_logo_section():
        logo_x, logo_y = width - 100, height - 100
        
        # Simple logo container
        p.setStrokeColor(HexColor("#dee2e6"))
        p.setLineWidth(1)
        p.circle(logo_x, logo_y, 35, fill=0, stroke=1)
        
        # Logo or text
        logo_path = os.path.join(settings.BASE_DIR, 'catalog', 'static', 'images', 'logo.png')
        if os.path.exists(logo_path):
            p.drawImage(logo_path, logo_x - 30, logo_y - 30, width=60, height=60, mask='auto')
        else:
            p.setFont("Helvetica-Bold", 10)
            p.setFillColor(HexColor("#6c757d"))
            p.drawCentredString(logo_x, logo_y, "LOGO")

    create_logo_section()

    # === VERIFICATION QR CODE ===
    def create_verification_qr():
        qr_x, qr_y = 100, 100
        
        # QR container
        p.setStrokeColor(HexColor("#dee2e6"))
        p.setLineWidth(1)
        p.rect(qr_x - 35, qr_y - 35, 70, 70, stroke=1, fill=0)
        
        # QR Code
        qr_code = qr.QrCodeWidget(f"https://yourdomain.com/verify/{enrollment.id}")
        bounds = qr_code.getBounds()
        size = 60
        qr_width = bounds[2] - bounds[0]
        qr_height = bounds[3] - bounds[1]
        d = Drawing(size, size, transform=[size / qr_width, 0, 0, size / qr_height, 0, 0])
        d.add(qr_code)
        renderPDF.draw(d, p, qr_x - 30, qr_y - 30)
        
        # QR label
        p.setFont("Helvetica", 8)
        p.setFillColor(HexColor("#6c757d"))
        p.drawCentredString(qr_x, qr_y - 50, "VERIFY CERTIFICATE")

    create_verification_qr()

    # === CLEAN FOOTER ===
    def create_clean_footer():
        footer_y = 60
        
        # Institution info
        p.setFont("Helvetica", 10)
        p.setFillColor(HexColor("#6c757d"))
        p.drawCentredString(width / 2, footer_y, "Professional Learning Institute • www.yourdomain.com")
        
        # Certificate ID (right aligned)
        p.setFont("Helvetica", 8)
        p.setFillColor(HexColor("#adb5bd"))
        p.drawRightString(width - 50, footer_y - 15, f"Certificate ID: {certificate_id}")
        
        # Verification URL (left aligned)
        p.drawString(50, footer_y - 15, f"Verify: yourdomain.com/verify/{enrollment.id}")

    create_clean_footer()

    # === SUBTLE SECURITY WATERMARK ===
    def create_security_watermark():
        p.setFont("Helvetica-Bold", 100)
        p.setFillColor(HexColor("#f8f9fa"))
        p.setFillAlpha(0.3)
        p.saveState()
        p.translate(width / 2, height / 2)
        p.rotate(45)
        p.drawCentredString(0, 0, "AUTHENTIC")
        p.restoreState()
        p.setFillAlpha(1.0)

    create_security_watermark()

    # === MINIMAL DECORATIVE ELEMENTS ===
    def create_minimal_decorations():
        # Subtle dots in corners
        p.setFillColor(HexColor("#dee2e6"))
        corner_positions = [
            (width - 70, height - 70),
            (70, height - 70),
            (width - 70, 70),
            (70, 70)
        ]
        
        for x, y in corner_positions:
            p.circle(x, y, 2, fill=1, stroke=0)

    create_minimal_decorations()

    # Finalize PDF
    p.showPage()
    p.save()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="certificate_{course_id}.pdf"'
    return response

@login_required
def take_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    questions = quiz.questions.all()

    if request.method == 'POST':
        score = 0
        total = questions.count()

        for question in questions:
            selected = int(request.POST.get(f"question_{question.id}"))
            if selected == question.correct_option:
                score += 1

        # Save result
        QuizResult.objects.create(user=request.user, quiz=quiz, score=score)

        return render(request, 'catalog/quiz_result.html', {
            'quiz': quiz,
            'score': score,
            'total': total,
        })

    return render(request, 'catalog/take_quiz.html', {
        'quiz': quiz,
        'questions': questions,
    })

def bundle_list(request):
    bundles = Bundle.objects.all()
    return render(request, 'catalog/bundle_list.html', {'bundles': bundles})

@login_required
def enroll_course(request, pk):
    course = get_object_or_404(Course, pk=pk)
    enrollment, created = Enrollment.objects.get_or_create(user=request.user, course=course)

    if created:
        send_mail(
            subject=f"New Enrollment for {course.title}",
            message=f"{request.user.username} has enrolled in your course: {course.title}.",
            from_email=None,
            recipient_list=[course.instructor.email],
        )

    return redirect('course_detail', pk=pk)


stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
def buy_bundle(request, bundle_id):
    bundle = get_object_or_404(Bundle, id=bundle_id)
    order = BundleOrder.objects.create(user=request.user, bundle=bundle)

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': bundle.name,
                },
                'unit_amount': int(bundle.price * 100),
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=request.build_absolute_uri(f'/bundles/success/{order.id}/'),
        cancel_url=request.build_absolute_uri('/bundles/'),
    )

    return redirect(checkout_session.url)

@login_required
def bundle_success(request, order_id):
    order = get_object_or_404(BundleOrder, id=order_id, user=request.user)
    order.paid = True
    order.save()

    # Mark user as enrolled in all courses in bundle
    for course in order.bundle.courses.all():
        Enrollment.objects.get_or_create(user=request.user, course=course)

    return render(request, 'catalog/bundle_success.html', {'bundle': order.bundle})

@login_required
def stream_video(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    enrolled = Enrollment.objects.filter(user=request.user, course=lesson.course, is_completed=False).exists()

    if not enrolled:
        raise Http404("Not authorized")

    video_path = lesson.video.path
    return FileResponse(open(video_path, 'rb'), content_type='video/mp4')
