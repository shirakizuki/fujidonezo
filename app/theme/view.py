from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.utils.html import strip_tags
from django.urls import reverse
from django.http import JsonResponse
from .forms import LoginForm, RegistrationForm, PasswordResetRequestForm, SetNewPasswordForm, TaskForm
from .models import EmailVerificationToken, PasswordResetToken, Tasks, Labels
from datetime import timedelta, datetime
from django.db.models import Q
from django.http import JsonResponse
import json

def logout(request):
    auth_logout(request)
    return redirect('theme:login')

@login_required(login_url='/login/')
def app(request):
    return render(request, 'home/home.html', {'user': request.user})

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            # Create user
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
              # Create user (using email as username)
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_active=True  # Keep active but track verification in UserProfile
            )
            
            # Create verification token and send email
            send_verification_email(request, user)
            
            # Store email in session for resend functionality
            request.session['verification_email'] = email
            
            # Redirect to verification notification page
            messages.success(request, "Registration successful! Please check your email to verify your account.")
            return redirect('theme:verification_sent')
    else:
        form = RegistrationForm()
    
    return render(request, 'auth/register.html', {'form': form})

def send_verification_email(request, user):
    # Create or get token
    token, created = EmailVerificationToken.objects.get_or_create(
        user=user,
        defaults={
            'expires_at': timezone.now() + timedelta(minutes=5),
            'is_used': False
        }
    )
    
    # If token exists but is expired or used, reset
    if not created and (not token.is_valid or token.is_used):
        token.reset_token()
    else:
        # Update last_sent time
        token.last_sent = timezone.now()
        token.save()
    
    # Generate verification URL
    verification_url = f"{settings.SITE_URL}{reverse('theme:verify_email', kwargs={'token': token.token})}"
    
    # Prepare email context
    context = {
        'user': user,
        'verification_url': verification_url,
        'expiry_time': token.expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')
    }
    
    # Render the HTML email
    html_message = render_to_string('emails/verification_email.html', context)
    plain_message = strip_tags(html_message)
    
    # Send email
    send_mail(
        subject='Verify Your Donezo Account',
        message=plain_message,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False
    )
    
    return token

def login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            # Since Django's default User model uses username for authentication,
            # and we're using email, we need to find the user by email first
            try:
                user = User.objects.get(email=email)
                user = authenticate(request, username=user.username, password=password)
                if user is not None:
                    # Check if email is verified
                    if not user.profile.is_verified:
                        messages.warning(request, "Please verify your email address before logging in.")
                        return redirect('theme:resend_verification')
                        
                    auth_login(request, user)
                    messages.success(request, "Login successful!")
                    return redirect('theme:tasks')
                else:
                    messages.error(request, "Invalid email or password.")
            except User.DoesNotExist:
                messages.error(request, "Invalid email or password.")
    else:
        form = LoginForm()
    
    return render(request, 'auth/login.html', {'form': form})
    
def verify_email(request, token):
    """Handle email verification"""
    try:
        # Find the token
        verification_token = get_object_or_404(EmailVerificationToken, token=token)
        
        # Check if token is still valid
        if verification_token.is_valid:
            # Mark user as verified
            user = verification_token.user
            user.profile.is_verified = True
            user.profile.save()
            
            # Mark token as used
            verification_token.mark_used()
            
            return render(request, 'auth/verify_email.html', {'success': True})
        else:
            error_message = "Verification link has expired. Please request a new one."
            return render(request, 'auth/verify_email.html', {
                'success': False, 
                'error_message': error_message
            })
            
    except Exception as e:
        error_message = "Invalid verification link. Please request a new one."
        return render(request, 'auth/verify_email.html', {
            'success': False, 
            'error_message': error_message
        })
        
def verification_sent(request):
    """Show verification sent page"""
    return render(request, 'auth/resend_verification.html')
    
def resend_verification(request):
    """Handle resending verification emails"""
    if request.method == 'POST':
        # Check if user is logged in
        if request.user.is_authenticated:
            user = request.user
        else:
            # Try to get the user from the session
            email = request.session.get('verification_email')
            try:
                user = User.objects.get(email=email)
            except (User.DoesNotExist, TypeError):
                messages.error(request, "We couldn't find your account. Please try logging in again.")
                return redirect('theme:login')
        
        # Check if user is already verified
        if user.profile.is_verified:
            messages.info(request, "Your email is already verified.")
            return redirect('theme:login')
            
        # Get existing token
        try:
            token = EmailVerificationToken.objects.get(user=user)
            
            # Check if token can be resent
            if token.can_resend:
                send_verification_email(request, user)
                messages.success(request, "Verification email sent. Please check your inbox.")
            else:
                time_left = 90 - (timezone.now() - token.last_sent).seconds
                messages.warning(request, f"Please wait {time_left} seconds before requesting another email.")
        except EmailVerificationToken.DoesNotExist:
            # Create new token if it doesn't exist
            send_verification_email(request, user)
            messages.success(request, "Verification email sent. Please check your inbox.")
              # Store email in session for later
    if request.user.is_authenticated:
        request.session['verification_email'] = request.user.email
            
    return render(request, 'auth/resend_verification.html')
    
# PASSWORD
def send_password_reset_email(request, user):
    """Create a reset token and send email to the user"""
    # Create or get token
    token, created = PasswordResetToken.objects.get_or_create(
        user=user,
        defaults={
            'expires_at': timezone.now() + timedelta(minutes=5),
            'is_used': False
        }
    )
    
    # If token exists but is expired or used, reset it
    if not created and (not token.is_valid or token.is_used):
        token.reset_token()
    else:
        # Update last_sent time
        token.last_sent = timezone.now()
        token.save()
    
    # Generate reset URL
    reset_url = f"{settings.SITE_URL}{reverse('theme:password_reset_confirm', kwargs={'token': token.token})}"
    
    # Prepare email context
    context = {
        'user': user,
        'reset_url': reset_url,
        'expiry_time': token.expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')
    }
    
    # Render the HTML email
    html_message = render_to_string('emails/password_reset_email.html', context)
    plain_message = strip_tags(html_message)
    
    # Send email
    send_mail(
        subject='Reset Your Donezo Password',
        message=plain_message,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False
    )
    
    return token
    
def password_reset_request(request):
    """Handle initial password reset request"""
    # If user is already logged in, redirect to the app
    if request.user.is_authenticated:
        messages.info(request, "You are already logged in.")
        return redirect('theme:app')
        
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                send_password_reset_email(request, user)
                
                # Store email in session for potential resends
                request.session['reset_email'] = email
                
                return redirect('theme:password_reset_sent')
            except User.DoesNotExist:
                # Show generic message to prevent email enumeration
                messages.error(request, "If an account with this email exists, a password reset link has been sent.")
                return redirect('theme:password_reset_sent')
    else:
        form = PasswordResetRequestForm()
    
    return render(request, 'auth/password_reset_request.html', {'form': form})
    
def password_reset_sent(request):
    """Show reset sent page and handle resend requests"""
    if request.method == 'POST':
        # Try to get the user from the session
        email = request.session.get('reset_email')
        try:
            user = User.objects.get(email=email)
            
            # Get existing token
            try:
                token = PasswordResetToken.objects.get(user=user)
                
                # Check if token can be resent
                if token.can_resend:
                    send_password_reset_email(request, user)
                    messages.success(request, "Password reset email sent. Please check your inbox.")
                else:
                    time_left = 90 - (timezone.now() - token.last_sent).seconds
                    messages.warning(request, f"Please wait {time_left} seconds before requesting another email.")
            except PasswordResetToken.DoesNotExist:
                # Create new token if it doesn't exist
                send_password_reset_email(request, user)
                messages.success(request, "Password reset email sent. Please check your inbox.")
                
        except (User.DoesNotExist, TypeError):
            messages.error(request, "We couldn't find your account. Please try again.")
            return redirect('theme:password_reset_request')
            
    return render(request, 'auth/password_reset_sent.html')
    
def password_reset_confirm(request, token):
    """Handle password reset confirmation"""
    try:
        # Find the token
        reset_token = get_object_or_404(PasswordResetToken, token=token)
        
        # Check if token is still valid
        if reset_token.is_valid:
            if request.method == 'POST':
                form = SetNewPasswordForm(request.POST)
                if form.is_valid():
                    # Change the password
                    user = reset_token.user
                    user.set_password(form.cleaned_data['password'])
                    user.save()
                    
                    # Mark token as used
                    reset_token.mark_used()
                    
                    messages.success(request, "Your password has been reset successfully. You can now log in with your new password.")
                    return redirect('theme:password_reset_complete')
            else:
                form = SetNewPasswordForm()
                
            return render(request, 'auth/password_reset_confirm.html', {
                'form': form,
                'valid_token': True
            })
        else:
            error_message = "This password reset link has expired. Please request a new one."
            return render(request, 'auth/password_reset_confirm.html', {
                'valid_token': False,
                'error_message': error_message
            })
            
    except Exception as e:
        error_message = "This password reset link is invalid. Please request a new one."
        return render(request, 'auth/password_reset_confirm.html', {
            'valid_token': False,
            'error_message': error_message
        })
        
def password_reset_complete(request):
    """Show reset success page"""
    return render(request, 'auth/password_reset_complete.html')

# CALENDAR
@login_required(login_url='/login/')
def calendar(request):
    # Get all user tasks
    tasks = Tasks.objects.filter(user=request.user)
    
    # Get the current month and year
    today = timezone.now().date()
    current_month = today.month
    current_year = today.year
    
    # Group tasks by date
    calendar_tasks = {}
    for task in tasks:
        if task.due_date:
            date_str = task.due_date.strftime("%Y-%m-%d")
            if date_str not in calendar_tasks:
                calendar_tasks[date_str] = []
            
            # Get label names for the task (if any)
            label_names = [label.name for label in task.labels.all()]
            
            calendar_tasks[date_str].append({
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'completed': task.completed,
                'due_time': task.due_time.strftime('%H:%M') if task.due_time else None,
                'labels': label_names
            })
    
    # Get upcoming tasks for sidebar (sorted by due date)
    upcoming_tasks = Tasks.objects.filter(
        user=request.user, 
        completed=False, 
        due_date__gte=today
    ).order_by('due_date', 'due_time').select_related('user').prefetch_related('labels')[:4]
    
    # Format upcoming tasks for the sidebar
    upcoming_task_list = []
    for task in upcoming_tasks:
        # Get label names for task
        labels = list(task.labels.all())
        label_name = labels[0].name if labels else "Task"
        
        # Calculate time difference in hours if due_time exists
        hours_remaining = 0
        if task.due_time:
            # Calculate hours between now and due time/date
            now = timezone.now()
            due_datetime = timezone.make_aware(datetime.combine(task.due_date, task.due_time))
            time_diff = due_datetime - now
            hours_remaining = max(0, round(time_diff.total_seconds() / 3600, 2))
            
        upcoming_task_list.append({
            'id': task.id,
            'title': task.title,
            'label_name': label_name,
            'hours': hours_remaining,
            'due_date': task.due_date,
            'due_time': task.due_time
        })
      # Get completed tasks for sidebar
    completed_tasks = Tasks.objects.filter(
        user=request.user, 
        completed=True
    ).order_by('-due_date')[:5]  # Show last 5 completed tasks
    
    return render(request, 'home/calendar.html', {
        'user': request.user,
        'calendar_tasks': json.dumps(calendar_tasks, default=str),
        'today': today.strftime("%Y-%m-%d"),
        'current_month': current_month,
        'current_year': current_year,
        'tasks': tasks,
        'upcoming_tasks': upcoming_task_list,
        'completed_tasks': completed_tasks
    })

@login_required(login_url='/login/')
def help(request):
    return render(request, 'home/help.html', {'user': request.user})
    
def terms_of_service(request):
    """Display the Terms of Service page"""
    return render(request, 'auth/tos.html')
    
def privacy_policy(request):
    """Display the Privacy Policy page"""
    return render(request, 'auth/privacy-policy.html')

# TASKS
@login_required(login_url='/login/')
def all_tasks(request):
    import json  # Add import here to ensure it's available
    today = timezone.now().date()
    one_week = today + timedelta(days=7)
    
    # Get user tasks
    tasks = Tasks.objects.filter(user=request.user)
    
    # Process form submission
    if request.method == 'POST':
        print(f"Task form submitted with POST data: {request.POST}")
        form = TaskForm(request.POST)
        if form.is_valid():
            print("Form is valid, processing task creation/update")
            print(f"Form cleaned data: {form.cleaned_data}")
            
            # Create or update task
            task_id = request.POST.get('task_id', '')
            
            if task_id:  # Updating existing task
                try:
                    task = Tasks.objects.get(id=task_id, user=request.user)
                    task.title = form.cleaned_data['title']
                    task.description = form.cleaned_data['description']
                    task.completed = form.cleaned_data.get('completed', False)
                    task.due_date = form.cleaned_data.get('due_date')
                    task.due_time = form.cleaned_data.get('due_time')
                    task.save()
                    
                    # Update labels
                    selected_labels = request.POST.getlist('labels')
                    task.labels.clear()  # Remove existing labels
                    if selected_labels:
                        for label_id in selected_labels:
                            try:
                                label = Labels.objects.get(id=label_id, user=request.user)
                                task.labels.add(label)
                            except Labels.DoesNotExist:
                                continue
                    
                    messages.success(request, 'Task updated successfully!')
                except Tasks.DoesNotExist:
                    messages.error(request, 'Task not found.')
            else:  # Creating new task
                print("Creating new task")
                task = Tasks.objects.create(
                    user=request.user,
                    title=form.cleaned_data['title'],
                    description=form.cleaned_data['description'],
                    completed=form.cleaned_data.get('completed', False),
                    due_date=form.cleaned_data.get('due_date'),
                    due_time=form.cleaned_data.get('due_time')
                )
                print(f"New task created: {task.id}")
                
                # Add labels
                selected_labels = request.POST.getlist('labels')
                if selected_labels:
                    print(f"Adding labels: {selected_labels}")
                    for label_id in selected_labels:
                        try:
                            label = Labels.objects.get(id=label_id, user=request.user)
                            task.labels.add(label)
                        except Labels.DoesNotExist:
                            continue
                
                messages.success(request, 'Task created successfully!')
                
            return redirect('theme:tasks')
        else:
            print(f"Form is invalid. Errors: {form.errors}")
            messages.error(request, 'Please correct the errors in the form.')
    else:
        form = TaskForm()
    
    # Group tasks by date categories
    today_tasks = tasks.filter(due_date=today, completed=False)
    upcoming_week_tasks = tasks.filter(due_date__gt=today, due_date__lte=one_week, completed=False)
    future_tasks = tasks.filter(Q(due_date__gt=one_week) | Q(due_date=None), completed=False)
    completed_tasks = tasks.filter(completed=True)
    
    # Get all labels for the user
    user_labels = Labels.objects.filter(user=request.user)
    
    context = {
        'form': form,
        'today_tasks': today_tasks,
        'upcoming_week_tasks': upcoming_week_tasks,
        'future_tasks': future_tasks,
        'completed_tasks': completed_tasks,
        'user_labels': user_labels,
        'today': today,
        'one_week': one_week
    }
    
    return render(request, 'home/listAll.html', context)

@login_required(login_url='/login/')
def toggle_task_complete(request, task_id):
    """Toggle task completion status"""
    if request.method == 'POST':
        try:
            # Parse JSON request data
            data = json.loads(request.body)
            completed = data.get('completed', False)
            
            # Get the task
            task = Tasks.objects.get(id=task_id, user=request.user)
            task.completed = completed
            task.save()
            
            return JsonResponse({'success': True, 'completed': task.completed})
        except Tasks.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Task not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
            
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

@login_required(login_url='/login/')
def delete_task(request, task_id):
    try:
        task = Tasks.objects.get(id=task_id, user=request.user)
        task.delete()
        messages.success(request, 'Task deleted successfully!')
    except Tasks.DoesNotExist:
        messages.error(request, 'Task not found.')
    
    return redirect('theme:tasks')

# LABELS
@login_required(login_url='/login/')
def labels(request):
    """Handle label CRUD operations"""
    from .models import Labels
    from .forms import LabelForm
    
    # Get all labels for the current user
    user_labels = Labels.objects.filter(user=request.user).order_by('-created_at')
    
    if request.method == 'POST':
        form = LabelForm(request.POST)
        
        if form.is_valid():
            # Check if this is a create or update operation
            label_id = request.POST.get('label_id')
            label_name = form.cleaned_data['name']
            
            if label_id:  # Update existing label
                label = get_object_or_404(Labels, id=label_id, user=request.user)
                label.name = label_name
                label.save()
                messages.success(request, f"Label '{label_name}' updated successfully")
            else:  # Create new label
                Labels.objects.create(
                    user=request.user,
                    name=label_name
                )
                messages.success(request, f"Label '{label_name}' created successfully")
            
            # Redirect to refresh the page
            return redirect('theme:labels')
        else:
            # If form validation failed, show error messages
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = LabelForm()
    
    return render(request, 'home/labels.html', {
        'user': request.user,
        'labels': user_labels,
        'form': form
    })

@login_required(login_url='/login/')
def delete_label(request, label_id):
    """Delete a label and remove it from all tasks"""
    from .models import Labels
    
    if request.method == 'POST':
        # Get the label
        label = get_object_or_404(Labels, id=label_id, user=request.user)
        label_name = label.name
        
        # Delete the label (it will automatically be removed from all tasks due to ManyToMany relationship)
        label.delete()
        
        messages.success(request, f"Label '{label_name}' deleted successfully")
    
    # Redirect back to the labels page
    return redirect('theme:labels')