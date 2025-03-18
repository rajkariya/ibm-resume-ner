from datetime import datetime , timedelta
import json
import traceback
import uuid
from arrow import now
from django.conf import settings
from django.http import HttpResponse, JsonResponse
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
from pymongo import UpdateOne
from dateutil import parser 
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
                request.session['email'] = email
                request.session['login_time'] = datetime.now().isoformat()
                request.session.set_expiry(6 * 60 * 60)
                logger.info(f"User {email} logged in successfully.")
                settings.MCLIENT['resume_ner']['user_logs_history'].insert_one({"email":email, "login_time":datetime.now()})
                return redirect("dashboard")
            except:
                traceback.print_exc()
                messages.error(request, "Invalid email or password")
                logger.warning(f"Failed login attempt for email: {email}")
        return render(request, "login.html")
    except Exception as e:
        logger.error(f"Error in login_view: {e}\n{traceback.format_exc()}")
        messages.error(request, "An unexpected error occurred.")
        return redirect("login")




@login_required_firebase
def create_job(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            job_id = str(uuid.uuid4())
            job_url = f"http://localhost:3000/job/{job_id}"

            job_data = {
                "_id": job_id,
                "title": data["title"],
                "experience": data["experience"],
                "salary_range": data["salary_range"],
                "interview_rounds": data["interview_rounds"],
                "location": data["location"],
                "description": data["description"],
                "created_at":datetime.now(timezone.utc).isoformat(),
                "expires_at":(datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                "job_url": job_url,
                "applications": 0,
                "user": request.session.get("email", "unknown"),
                "job_id":job_id
            }

            # Store in MongoDB
            settings.MCLIENT['resume_ner']['job_listings'].insert_one(job_data)

            # Store in Firebase
            db.child("jobs").child(job_id).set(job_data)

            return JsonResponse({"success": True, "job_url": job_url})
        except Exception as e:
            traceback.print_exc()
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)


# Fetch the respective job listings.
@login_required_firebase
def fetch_jobs(request):
   try:
        # jobs_ref = db.child("jobs").get()
        # print(jobs_ref)
        # print(jobs_ref.val())
        res=list(settings.MCLIENT['resume_ner']['job_listings'].find({"user":request.session['email']}))
        return JsonResponse({"data":res},status=200)
   except:
       traceback.print_exc()
       return JsonResponse({"msg":"Something went wrong"},status=401)
   
@login_required_firebase
def job_application(request, job_id):
    job = get_object_or_404(JobPosting, id=job_id)

    if now() > job.expires_at:
        return render(request, "expired.html")  

    if request.method == "POST":
        form = JobApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            resume = request.FILES["resume"]
            bucket = firebase.storage.bucket()
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
                settings.MCLIENT['resume_ner']['users'].insert_one({"email":email,"password":password})
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


def job_page(request, job_id):
    job = settings.MCLIENT['resume_ner']['job_listings'].find_one({"_id": job_id})

    if not job:
        return HttpResponse("Job not found.", status=404)

    try:
        # Convert the ISO 8601 string to a datetime object (with timezone awareness)
        expires_at = parser.isoparse(job["expires_at"])
    except ValueError:
        return HttpResponse("Invalid date format in database.", status=500)

    # Compare with current time (ensure timezone consistency)
    if expires_at < datetime.utcnow().replace(tzinfo=expires_at.tzinfo):
        return HttpResponse("This job posting has expired.", status=410)

    return render(request, "job_detail.html", {"job": job})


def upload_resume(file, filename):
    """Upload resume to Firebase Storage"""
    bucket = firebase.storage.bucket()
    blob = bucket.blob(f"resumes/{filename}")
    blob.upload_from_file(file)
    return blob.public_url

def submit_application(request):
    if request.method == "POST":
        name = request.POST["name"]
        email = request.POST["email"]
        resume_file = request.FILES["resume"]
        
        # Upload resume to Firebase
        resume_url = upload_resume(resume_file, f"{uuid.uuid4()}.pdf")
        
        # Store in MongoDB
        db.applications.insert_one({
            "name": name,
            "email": email,
            "resume_url": resume_url,
            "job_id": request.POST["job_id"],
            "submitted_at": now(),
        })

        return JsonResponse({"message": "Application submitted!"})
