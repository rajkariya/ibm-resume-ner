import traceback
import uuid
from arrow import now
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
import pyrebase
from .decorators import login_required_firebase 
import logging
import traceback
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
# from firebase_admin import credentials, storage, firestore
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from .models import JobApplication, JobPosting
from .forms import JobApplicationForm

# from firebase_admin import credentials, storage, firestore
config={
"apiKey": "AIzaSyCAofwa3iucIIYBau6w5L8nTe_S1haS3cw",
  "authDomain": "resume-ner-bdd15.firebaseapp.com",
  "projectId": "resume-ner-bdd15",
  "storageBucket": "resume-ner-bdd15.firebasestorage.app",
  "messagingSenderId": "108689243009",
  "appId": "1:108689243009:web:70d246313b1c20a62cc680",
  "databaseURL":"https://resume-ner-bdd15-default-rtdb.asia-southeast1.firebasedatabase.app/"
}
# Initialising database,auth and firebase for further use 
firebase=pyrebase.initialize_app(config)
authe = firebase.auth()
db=firebase.database()

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
    

def create_job(request):
    if request.method == "POST":
        job_id = str(uuid.uuid4())  
        job_data = {
            "id": job_id,
            "title": request.POST["title"],
            "created_at": now().isoformat(),
            "expires_at": request.POST["expires_at"],  
            "applications": 0  
        }
        db.child("jobs").child(job_id).push(job_data)
        return JsonResponse({"success": True})  
    return JsonResponse({"error": "Invalid request"}, status=400)

def fetch_jobs(request):
   try:
        jobs_ref = db.child("jobs").get()
        print(jobs_ref)
        print(jobs_ref.val())
        # jobs = [{"id": job.id, **job.to_dict()} for job in jobs_ref]
        return JsonResponse(jobs_ref.val(), safe=False)
   except:
       traceback.print_exc()
       return JsonResponse({"msg":"Something went wrong"},status=401)
   
    
def job_application(request, job_id):
    job = get_object_or_404(JobPosting, id=job_id)

    if now() > job.expires_at:
        return render(request, "expired.html")  

    if request.method == "POST":
        form = JobApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            resume = request.FILES["resume"]
            bucket = storage.bucket()
            blob = bucket.blob(f"resumes/{job.id}/{resume.name}")
            blob.upload_from_file(resume)
            blob.make_public()
            resume_url = blob.public_url

            application = form.save(commit=False)
            application.job = job
            application.resume_url = resume_url
            application.save()

            db.CHIL("applications").add({
                "job_id": str(job.id),
                "first_name": application.first_name,
                "last_name": application.last_name,
                "email": application.email,
                "phone": application.phone,
                "resume_url": resume_url,
                "applied_at": now()
            })

            return redirect("success_page")
    else:
        form = JobApplicationForm()
    return render(request, "apply_job.html", {"form": form, "job": job})

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


def get_applications(request, job_id):
    job = JobPosting.objects.get(id=job_id)
    applications = JobApplication.objects.filter(job=job).values(
        "first_name", "last_name", "email", "phone", "resume_url"
    )
    return JsonResponse({"job_title": job.title, "applications": list(applications)})

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
def create_job_page(request):
    return render(request, "create_job.html")

def logout_view(request):
    request.session.flush()
    return redirect("login")