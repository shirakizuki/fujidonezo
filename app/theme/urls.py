from django.urls import path
from . import view

app_name = 'theme'

urlpatterns = [
    # AUTHENTICATION URLS
    path('', view.login, name='login'),
    path('register/', view.register, name='register'),
    path('verify/<uuid:token>/', view.verify_email, name='verify_email'),
    path('verification-sent/', view.verification_sent, name='verification_sent'),
    path('resend-verification/', view.resend_verification, name='resend_verification'),
    # PASSWORD RESET URLS
    path('password-reset/', view.password_reset_request, name='password_reset_request'),
    path('password-reset-sent/', view.password_reset_sent, name='password_reset_sent'),
    path('password-reset/<uuid:token>/', view.password_reset_confirm, name='password_reset_confirm'),
    path('password-reset-complete/', view.password_reset_complete, name='password_reset_complete'),
    # LEGAL PAGES
    path('terms-of-service/', view.terms_of_service, name='terms-of-service'),
    path('privacy-policy/', view.privacy_policy, name='privacy-policy'),      # BASE APPS
    path('app/tasks/', view.all_tasks, name='tasks'),
    path('app/tasks', view.all_tasks, name='tasks'),  # Keep both patterns for backward compatibility
    path('app/tasks/delete/<int:task_id>/', view.delete_task, name='delete_task'),
    path('app/tasks/toggle-complete/<int:task_id>/', view.toggle_task_complete, name='toggle_task_complete'),
    path('app/labels', view.labels, name='labels'),
    path('app/labels/delete/<int:label_id>/', view.delete_label, name='delete_label'),
    path('app/calendar', view.calendar, name='calendar'),
    path('app/help', view.help, name='help'),
    path('app/account', view.account, name='account'),
]

