from django.contrib import admin
from .models import UserProfile, Labels, Tasks, EmailVerificationToken, PasswordResetToken

# Register your models here
admin.site.register(UserProfile)
admin.site.register(Labels)
admin.site.register(Tasks)
admin.site.register(EmailVerificationToken)
admin.site.register(PasswordResetToken)