from django.urls import path
from . import views

urlpatterns = [
    # ... existing URLs ...
    path('update_application_status/', views.update_application_status, name='update_application_status'),
    # ... existing URLs ...
] 