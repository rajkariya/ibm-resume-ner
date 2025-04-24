from django.urls import path
from . import views

urlpatterns = [
    path('get_application_results/<str:application_id>/', views.get_application_results, name='get_application_results'),
] 