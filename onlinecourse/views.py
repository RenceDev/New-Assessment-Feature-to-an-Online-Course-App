from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth import login, logout, authenticate
from django.views import generic  # <-- Add this import
from .models import Course, Enrollment, Question, Choice, Submission
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

# User registration view
def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)

# User login view
def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)

# User logout view
def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')

# Check if a user is enrolled in a course
def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled

# CourseListView: Displays list of courses
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses

# CourseDetailView: Displays details of a specific course
class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'

# Enroll in a course
def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))

# Function to collect the selected choices from the exam form from the request object
def extract_answers(request):
    submitted_answers = []
    for key in request.POST:
        if key.startswith('choice'):
            value = request.POST[key]
            choice_id = int(value)
            submitted_answers.append(choice_id)
    return submitted_answers

# Submit view to create an exam submission record for a course enrollment
def submit(request, course_id):
    # Get the course object based on the provided course_id
    course = get_object_or_404(Course, pk=course_id)
    
    # Get the current user from the request
    user = request.user
    
    # Get the associated enrollment for the user and the course
    enrollment = Enrollment.objects.get(user=user, course=course)
    
    # Create a new Submission object referring to the enrollment
    submission = Submission.objects.create(enrollment=enrollment)
    
    # Extract the selected choices from the HTTP request
    choices = extract_answers(request)
    
    # Add the selected choices to the submission object
    submission.choices.set(choices)
    
    # Get the submission ID
    submission_id = submission.id
    
    # Redirect to the exam result view, passing the course_id and submission_id
    return HttpResponseRedirect(reverse(viewname='onlinecourse:exam_result', args=(course_id, submission_id,)))

# Function to display the exam result
def show_exam_result(request, course_id, submission_id):
    # Get the course and submission objects
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(Submission, pk=submission_id)

    # Get the user's selected choices from the submission
    selected_choices = submission.choices.all()

    # Calculate the total score
    total_questions = Question.objects.filter(course=course).count()
    correct_answers = 0

    # Compare each selected choice with the correct answer
    for choice in selected_choices:
        if choice.is_correct:
            correct_answers += 1

    # Calculate the grade as a percentage
    grade = (correct_answers / total_questions) * 100 if total_questions > 0 else 0

    # Render the exam result page with the calculated grade
    return render(request, 'onlinecourse/exam_result_bootstrap.html', {
        'course': course,
        'submission': submission,
        'grade': grade,
        'correct_answers': correct_answers,
        'total_questions': total_questions
    })
