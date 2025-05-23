import re
from django import forms
from django.contrib.auth.models import User
class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-400'
            })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-400'
            })
    )

class RegistrationForm(forms.Form):
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-400'
            })
    )
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-400'
            })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-400'
            })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-400'
            })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-400'
            })
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        email = cleaned_data.get('email')

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords don't match")
        
        # Check if email already exists
        if User.objects.filter(email=email).exists() or User.objects.filter(username=email).exists():
            raise forms.ValidationError("Email already in use")
        
        # Validate password strength
        if password:
            # Check length
            if len(password) < 8:
                raise forms.ValidationError("Password must be at least 8 characters long")
            
            # Check for uppercase
            if not re.search(r'[A-Z]', password):
                raise forms.ValidationError("Password must contain at least one uppercase letter")
            
            # Check for lowercase
            if not re.search(r'[a-z]', password):
                raise forms.ValidationError("Password must contain at least one lowercase letter")
            
            # Check for digit
            if not re.search(r'\d', password):
                raise forms.ValidationError("Password must contain at least one number")
            
            # Check for special character
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                raise forms.ValidationError("Password must contain at least one special character")
        
        return cleaned_data
        
class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-400'
        })
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError("No account found with this email address.")
        return email
        
class SetNewPasswordForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-400'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-400'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords don't match")
        
        # Validate password strength
        if password:
            # Check length
            if len(password) < 8:
                raise forms.ValidationError("Password must be at least 8 characters long")
            
            # Check for uppercase
            if not re.search(r'[A-Z]', password):
                raise forms.ValidationError("Password must contain at least one uppercase letter")
            
            # Check for lowercase
            if not re.search(r'[a-z]', password):
                raise forms.ValidationError("Password must contain at least one lowercase letter")
            
            # Check for digit
            if not re.search(r'\d', password):
                raise forms.ValidationError("Password must contain at least one number")
            
            # Check for special character
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                raise forms.ValidationError("Password must contain at least one special character")

        return cleaned_data

class TaskForm(forms.Form):
    title = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full p-2 text-lg font-medium border-0 border-b border-transparent focus:border-orange-300 focus:ring-0',
            'placeholder': 'This is the title'
        })
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full p-2 text-gray-600 border-0 border-b border-transparent focus:border-orange-300 focus:ring-0 resize-none h-32',
            'placeholder': 'This is the description generated from the AI.',
            'rows': 6,
            'style': 'min-height: 150px;'
        })
    )
    completed = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'h-5 w-5 text-orange-500'
        })
    )
    due_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'w-full bg-transparent border-0 focus:ring-0 py-1',
            'type': 'date'
        })
    )
    due_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={
            'class': 'w-full bg-transparent border-0 focus:ring-0 py-1',        
            'type': 'time'
        })
    )
    def clean_due_date(self):
        """Validate that due date is not in the past"""
        from datetime import date
        
        due_date = self.cleaned_data.get('due_date')
        today = date.today()
        
        if due_date and due_date < today:
            raise forms.ValidationError("Date cannot be in the past")
            
        return due_date

class LabelForm(forms.Form):
    name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full p-2 text-lg font-medium border-0 border-b border-transparent focus:border-orange-300 focus:ring-0',
            'placeholder': 'Label'
        })
    )