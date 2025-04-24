from django.urls import path
from . import views

urlpatterns = [
    # ... existing URLs ...
    path('update_application_status/', views.update_application_status, name='update_application_status'),
    path('toggle-job-status/', views.toggle_job_status, name='toggle_job_status'),
    path('process_resumes/', views.process_resumes, name='process_resumes'),
    path('get_application_results/<str:application_id>/', views.get_application_results, name='get_application_results'),
    # ... existing URLs ...
] 