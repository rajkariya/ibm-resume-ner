"""
URL configuration for ner project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from main import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.landing, name="landing"),
    path('home',views.landing,name="landing"),
    
    path('login/', views.login_view, name="login"),
    path('signup/', views.signup_view, name="signup"),
    path('logout/', views.logout_view, name="logout"),
    path('tnc/', views.tnc, name="tnc"),
    path('dashboard/',views.dashboard,name="dashboard"),
    path("manage-candidates/", views.manage_candidates, name="manage_candidates"),
    path("manage-applications/", views.manage_applications, name="manage_applications"),
    path("create-job/", views.create_job_page, name="create_job_page"),
    path("create/", views.create_job, name="create_job"),
    path('apply/<uuid:job_id>/', views.job_application, name='job_application'),
    path("fetch_jobs/", views.fetch_jobs, name="fetch_jobs"),
    path("job/<str:job_id>/", views.job_page, name="job_page"),
    path("submit_application/", views.submit_application, name="submit_application"),
    path("update_application_status/<str:application_id>/", views.update_application_status, name="update_application_status"),
    path("get_applications/<str:job_id>/", views.get_applications, name="get_applications"),
    path("get_dashboard_data/", views.get_dashboard_data, name="get_dashboard_data"),
    path('fetch-jobs/', views.fetch_jobs, name='fetch_jobs'),
    path('toggle-job-status/', views.toggle_job_status, name='toggle_job_status'),
    path('company-details/', views.company_details, name='company_details'),
    path('chatbot/', views.chatbot, name="chatbot"),
    path('process_resumes/', views.process_resumes, name='process_resumes'),
    path('pricing/', views.pricing, name='pricing'),
    path('get_application_results/<str:application_id>/', views.get_application_results, name='get_application_results'),
]
