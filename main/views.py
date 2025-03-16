import traceback
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
import pyrebase
from .decorators import login_required_firebase 

config={
"apiKey": "AIzaSyCAofwa3iucIIYBau6w5L8nTe_S1haS3cw",
  "authDomain": "resume-ner-bdd15.firebaseapp.com",
  "projectId": "resume-ner-bdd15",
  "storageBucket": "resume-ner-bdd15.firebasestorage.app",
  "messagingSenderId": "108689243009",
  "appId": "1:108689243009:web:70d246313b1c20a62cc680",
  "databaseURL":""
}
# Initialising database,auth and firebase for further use 
firebase=pyrebase.initialize_app(config)
authe = firebase.auth()
import logging
import traceback
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages

logger = logging.getLogger(__name__)

def landing(request):
    try:
        return render(request, "landing.html")
    except Exception as e:
        logger.error(f"Error rendering landing page: {e}\n{traceback.format_exc()}")
        messages.error(request, "An unexpected error occurred.")
        return redirect("login")

def tnc(request):
    try:
        return render(request, "tnc.html")
    except Exception as e:
        logger.error(f"Error rendering T&C page: {e}\n{traceback.format_exc()}")
        messages.error(request, "An unexpected error occurred.")
        return redirect("landing")

def login_view(request):
    try:
        if request.method == "POST":
            email = request.POST.get("email")
            password = request.POST.get("password")
            try:
                user = authe.sign_in_with_email_and_password(email, password)
                request.session['uid'] = user['idToken']
                logger.info(f"User {email} logged in successfully.")
                return redirect("dashboard")
            except:
                messages.error(request, "Invalid email or password")
                logger.warning(f"Failed login attempt for email: {email}")
        return render(request, "login.html")
    except Exception as e:
        logger.error(f"Error in login_view: {e}\n{traceback.format_exc()}")
        messages.error(request, "An unexpected error occurred.")
        return redirect("login")

def signup_view(request):
    try:
        if request.method == "POST":
            email = request.POST.get("email")
            password = request.POST.get("password")
            try:
                user = authe.create_user_with_email_and_password(email, password)
                messages.success(request, "Signup successful! Please login.")
                logger.info(f"User {email} signed up successfully.")
                return redirect("login")
            except:
                messages.error(request, "Failed to sign up. Email may already exist.")
                logger.warning(f"Signup attempt failed for email: {email}")
        return render(request, "signup.html")
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error in signup_view: {e}\n{traceback.format_exc()}")
        messages.error(request, "An unexpected error occurred.")
        return redirect("signup")

def logout_view(request):
    try:
        request.session.flush()
        logger.info("User logged out.")
        return redirect("login")
    except Exception as e:
        logger.error(f"Error in logout_view: {e}\n{traceback.format_exc()}")
        messages.error(request, "An unexpected error occurred.")
        return redirect("landing")

def dashboard(request):
    try:
        if 'uid' in request.session:
            return render(request, "dashboard.html")
        else:
            messages.error(request, "You need to log in first.")
            return redirect("login")
    except Exception as e:
        logger.error(f"Error in dashboard view: {e}\n{traceback.format_exc()}")
        messages.error(request, "An unexpected error occurred.")
        return redirect("login")
    
@login_required_firebase
def dashboard(request):
    return render(request, "dashboard.html")

@login_required_firebase
def manage_candidates(request):
    return render(request, "manage_candidates.html")

@login_required_firebase
def create_job(request):
    return render(request, "create_job.html")

def logout_view(request):
    request.session.flush()
    return redirect("login")