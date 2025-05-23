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
from datetime import timedelta
from django.db.models import Q
from django.http import JsonResponse
import json
import random

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
            calendar_tasks[date_str].append({
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'completed': task.completed,
                'due_time': task.due_time.strftime('%H:%M') if task.due_time else None
            })
    
    return render(request, 'home/calendar.html', {
        'user': request.user,
        'calendar_tasks': json.dumps(calendar_tasks, default=str),
        'today': today.strftime("%Y-%m-%d"),
        'current_month': current_month,
        'current_year': current_year,
        'tasks': tasks
    })

@login_required(login_url='/login/')
def help(request):
    return render(request, 'home/help.html', {'user': request.user})

@login_required(login_url='/login/')
def account(request):
    """Handle user account settings"""
    if request.method == 'POST':
        # Handle personal information update
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        has_changes = request.POST.get('has_changes') == 'true'
        
        # Update user information if there are changes
        if has_changes and (first_name != request.user.first_name or last_name != request.user.last_name):
            user = request.user
            user.first_name = first_name
            user.last_name = last_name
            user.save()
            # Redirect with a success parameter to show the popup
            return redirect(f'{reverse("theme:account")}?success=true')
        
    return render(request, 'home/settings/account.html', {'user': request.user})
    
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

@login_required(login_url='/login/')
def login_details(request):
    """Display the login details page"""
    return render(request, 'home/settings/login_details.html', {'user': request.user})

@login_required(login_url='/login/')
def change_email(request):
    """Handle email change requests with verification"""
    if request.method == 'POST':
        new_email = request.POST.get('new_email', '').strip().lower()
        current_password = request.POST.get('current_password', '')
        
        # Validate inputs
        if not new_email or not current_password:
            messages.error(request, "Please fill in all fields.")
            return redirect('theme:login_details')
            
        # Verify current password
        user = authenticate(request, username=request.user.username, password=current_password)
        if not user:
            messages.error(request, "Current password is incorrect.")
            return redirect('theme:login_details')
            
        # Check if email is already in use
        if User.objects.filter(email=new_email).exclude(pk=request.user.pk).exists():
            messages.error(request, "This email address is already in use.")
            return redirect('theme:login_details')
            
        # If email is unchanged, redirect back
        if new_email == request.user.email:
            messages.warning(request, "The new email is the same as your current email.")
            return redirect('theme:login_details')
            
        # Send OTP for verification
        send_otp_email(request, request.user, 'email_change', new_email)
        
        # Store action details in session
        request.session['pending_action'] = {
            'type': 'email_change',
            'new_email': new_email
        }
        
        messages.success(request, "A verification code has been sent to your new email address. Please verify to complete the change.")
        return redirect('theme:verify_login_otp')
        
    # If not POST, redirect to login details page
    return redirect('theme:login_details')

def send_email_change_verification(request, user, new_email):
    """Send verification email for email change"""
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
    
    # Generate verification URL with additional parameter for email change
    verification_url = f"{settings.SITE_URL}{reverse('theme:verify_email_change', kwargs={'token': token.token})}"
    
    # Prepare email context
    context = {
        'user': user,
        'verification_url': verification_url,
        'expiry_time': token.expires_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
        'new_email': new_email
    }
    
    # Render the HTML email
    html_message = render_to_string('emails/email_change_verification.html', context)
    plain_message = strip_tags(html_message)
    
    # Send email
    send_mail(
        subject='Verify Your New Email Address - Donezo',
        message=plain_message,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[new_email],
        html_message=html_message,
        fail_silently=False
    )
    
    return token

@login_required(login_url='/login/')
def verify_email_change(request, token):
    """Handle email change verification"""
    try:
        # Find the token
        verification_token = get_object_or_404(EmailVerificationToken, token=token)
        
        # Check if token is still valid and belongs to logged in user
        if verification_token.is_valid and verification_token.user == request.user:
            # Get new email from session
            new_email = request.session.get('new_email')
            
            if not new_email:
                messages.error(request, "Email change session expired. Please try again.")
                return redirect('theme:login_details')
                
            # Update user email
            user = request.user
            user.email = new_email
            user.username = new_email  # Since username is used as email in this project
            user.save()
            
            # Mark token as used
            verification_token.mark_used()
            
            # Clear session data
            if 'new_email' in request.session:
                del request.session['new_email']
                
            messages.success(request, "Your email has been successfully updated.")
            return redirect('theme:account')
        else:
            error_message = "Verification link has expired. Please request the email change again."
            messages.error(request, error_message)
            return redirect('theme:login_details')
            
    except Exception as e:
        error_message = "Invalid verification link. Please request the email change again."
        messages.error(request, error_message)
        return redirect('theme:login_details')

@login_required(login_url='/login/')
def change_password(request):
    """Handle password change requests"""
    if request.method == 'POST':
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        # Validate inputs
        if not current_password or not new_password or not confirm_password:
            messages.error(request, "Please fill in all fields.")
            return redirect('theme:login_details')
            
        # Verify current password
        user = authenticate(request, username=request.user.username, password=current_password)
        if not user:
            messages.error(request, "Current password is incorrect.")
            return redirect('theme:login_details')
            
        # Check if passwords match
        if new_password != confirm_password:
            messages.error(request, "New passwords don't match.")
            return redirect('theme:login_details')
            
        # Check password strength (optional - you could implement more checks)
        if len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return redirect('theme:login_details')
            
        # Send OTP for verification
        send_otp_email(request, request.user, 'password_change')
        
        # Store password data securely in session
        request.session['pending_action'] = {
            'type': 'password_change',
            'new_password': new_password
        }
        
        messages.success(request, "A verification code has been sent to your email. Please verify to complete the password change.")
        return redirect('theme:verify_login_otp')
        
    # If not POST, redirect to login details page
    return redirect('theme:login_details')  

def generate_otp():
    """Generate a 6-digit OTP"""
    return str(random.randint(100000, 999999))

def send_otp_email(request, user, action_type, new_email=None):
    """Send OTP email for verification of login detail changes
    
    Args:
        request: HTTP request object
        user: User object
        action_type: String indicating type of action ('email_change' or 'password_change')
        new_email: New email if action_type is 'email_change'
    """
    # Generate OTP
    otp = generate_otp()
    
    # Store OTP in session with expiry time (5 minutes from now)
    expiry_time = timezone.now() + timedelta(minutes=5)
    request.session['login_details_otp'] = {
        'otp': otp,
        'action_type': action_type,
        'expires_at': expiry_time.timestamp(),
        'new_email': new_email,  # Only used for email change
        'attempts': 0  # Track verification attempts
    }
    
    # Determine recipient email
    recipient = new_email if action_type == 'email_change' and new_email else user.email
    
    # Prepare email context
    context = {
        'user': user,
        'otp': otp,
        'expiry_time': expiry_time.strftime('%Y-%m-%d %H:%M:%S UTC'),
        'action_type': 'email change' if action_type == 'email_change' else 'password change',
        'new_email': new_email
    }
    
    # Render the HTML email
    html_message = render_to_string('emails/login_details_otp_email.html', context)
    plain_message = strip_tags(html_message)
    
    # Send email
    subject = 'Verification Code for Your Account Changes - Donezo'
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[recipient],
        html_message=html_message,
        fail_silently=False
    )
    
    return otp

@login_required(login_url='/login/')
def verify_login_otp(request):
    """Handle OTP verification for login detail changes"""
    # Check if there's a pending action
    pending_action = request.session.get('pending_action')
    otp_data = request.session.get('login_details_otp')
    
    if not pending_action or not otp_data:
        messages.error(request, "No pending changes to verify. Please try again.")
        return redirect('theme:login_details')
    
    # Check if OTP has expired
    current_time = timezone.now().timestamp()
    if current_time > otp_data.get('expires_at', 0):
        messages.error(request, "Verification code has expired. Please request a new code.")
        return redirect('theme:login_details')
    
    # Process OTP verification
    if request.method == 'POST':
        submitted_otp = request.POST.get('otp', '')
        
        # Track verification attempts to prevent brute force
        otp_data['attempts'] = otp_data.get('attempts', 0) + 1
        request.session['login_details_otp'] = otp_data
        
        # Limit to 3 attempts
        if otp_data['attempts'] >= 3:
            del request.session['login_details_otp']
            del request.session['pending_action']
            messages.error(request, "Too many incorrect attempts. Please try again.")
            return redirect('theme:login_details')
        
        # Verify OTP
        if submitted_otp == otp_data['otp']:
            # OTP is correct, process the pending action
            action_type = pending_action['type']
            
            if action_type == 'email_change':
                new_email = pending_action['new_email']
                
                # Update user email
                user = request.user
                user.email = new_email
                user.username = new_email  # Since username is used as email in this project
                user.save()
                
                # Clean up session
                del request.session['login_details_otp']
                del request.session['pending_action']
                
                messages.success(request, "Your email has been successfully updated.")
                return redirect('theme:account')
                
            elif action_type == 'password_change':
                new_password = pending_action['new_password']
                
                # Update password
                user = request.user
                user.set_password(new_password)
                user.save()
                
                # Clean up session
                del request.session['login_details_otp']
                del request.session['pending_action']
                
                # Re-authenticate the user to prevent logout
                user = authenticate(request, username=user.username, password=new_password)
                auth_login(request, user)
                
                messages.success(request, "Your password has been successfully updated.")
                return redirect('theme:account')
            
        else:
            messages.error(request, f"Invalid verification code. You have {3 - otp_data['attempts']} attempts remaining.")
    # Prepare context for the template
    context = {
        'user': request.user,
        'action_type': 'Email Change' if pending_action['type'] == 'email_change' else 'Password Change',
    }
    
    if pending_action['type'] == 'email_change':
        context['new_email'] = pending_action['new_email']
    
    # Add OTP to context if in debug mode
    if settings.DEBUG:
        context['debug_otp'] = otp_data['otp']
        context['debug_mode'] = True
        
    return render(request, 'home/settings/verify_login_otp.html', context)

@login_required(login_url='/login/')
def resend_login_otp(request):
    """Resend OTP for login detail verification"""
    # Check if there's a pending action
    pending_action = request.session.get('pending_action')
    
    if not pending_action:
        messages.error(request, "No pending changes to verify. Please try again.")
        return redirect('theme:login_details')
    
    # Check if we can resend (prevent spam)
    otp_data = request.session.get('login_details_otp', {})
    current_time = timezone.now().timestamp()
    last_sent = otp_data.get('expires_at', 0) - 300  # Default 5 min earlier
    
    if current_time < last_sent + 60:  # 60 seconds cooldown
        wait_time = int(last_sent + 60 - current_time)
        messages.warning(request, f"Please wait {wait_time} seconds before requesting a new verification code.")
        return redirect('theme:verify_login_otp')
    
    # Resend OTP
    action_type = pending_action['type']
    if action_type == 'email_change':
        new_email = pending_action['new_email']
        send_otp_email(request, request.user, 'email_change', new_email)
    else:
        send_otp_email(request, request.user, 'password_change')
    
    messages.success(request, "A new verification code has been sent to your email.")
    return redirect('theme:verify_login_otp')