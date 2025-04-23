from datetime import datetime , timedelta
import traceback
import uuid
from arrow import now
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
# import pyrebase4 as pyrebase
import pyrebase
# from pyrebase4 import pyrebase
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
import google.generativeai as genai
from django.views.decorators.csrf import csrf_exempt
import json

config={
"apiKey": "AIzaSyCAofwa3iucIIYBau6w5L8nTe_S1haS3cw",
  "authDomain": "resume-ner-bdd15.firebaseapp.com",
  "projectId": "resume-ner-bdd15",
  "storageBucket": "resume-ner-bdd15.firebasestorage.app",
  "messagingSenderId": "108689243009",
  "appId": "1:108689243009:web:70d246313b1c20a62cc680",
  "databaseURL":"https://resume-ner-bdd15-default-rtdb.asia-southeast1.firebasedatabase.app/"
}

firebase=pyrebase.initialize_app(config)
authe = firebase.auth()
storage=firebase.storage()
db=firebase.database()

logger = logging.getLogger(__name__)

# Initialize Gemini API
try:
    # You'll need to set this in your Django settings
    genai.configure(api_key=settings.GOOGLE_API_KEY)
except Exception as e:
    logger.error(f"Failed to configure Gemini API: {str(e)}")

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
            title = request.POST.get("title")
            experience = request.POST.get("experience")
            salary_range = request.POST.get("salary_range")
            interview_rounds = request.POST.get("interview_rounds")
            location = request.POST.get("location")
            description = request.POST.get("description")
            
            if not all([title, experience, salary_range, interview_rounds, location, description]):
                return JsonResponse({"error": "Missing required fields"}, status=400)

            job_id = str(uuid.uuid4())
            job_url = f"http://localhost:3000/job/{job_id}"
            user_email = request.session.get("email", "unknown")

            job_data = {
                "_id": job_id,
                "title": title,
                "experience": experience,
                "salary_range": salary_range,
                "interview_rounds": interview_rounds,
                "location": location,
                "description": description,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                "job_url": job_url,
                "applications": 0,
                "user": user_email,
                "job_id": job_id,
                "is_active": True
            }

            settings.MCLIENT['resume_ner']['job_listings'].insert_one(job_data)

            db.child("jobs").child(job_id).set(job_data)

            return JsonResponse({"success": True, "job_url": job_url})
        except Exception as e:
            logger.error(f"Error creating job: {str(e)}\n{traceback.format_exc()}")
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=400)


@login_required_firebase
def fetch_jobs(request):
   try:
        user_email = request.session.get('email')
        if not user_email:
            return JsonResponse({"error": "User not authenticated"}, status=401)

        mongo_jobs = list(settings.MCLIENT['resume_ner']['job_listings'].find({"user": user_email}))
        logger.info(f"Found {len(mongo_jobs)} jobs in MongoDB for user {user_email}")
        
        firebase_jobs = []
        jobs_ref = db.child("jobs").get()
        if jobs_ref.val():
            for job_id, job_data in jobs_ref.val().items():
                if job_data.get('user') == user_email:
                    firebase_jobs.append({
                        "_id": job_id,
                        "title": job_data.get('title', ''),
                        "description": job_data.get('description', ''),
                        "created_at": job_data.get('created_at', ''),
                        "expires_at": job_data.get('expires_at', ''),
                        "applications": job_data.get('applications', 0),
                        "user": job_data.get('user', ''),
                        "is_active": job_data.get('is_active', True),
                        "job_url": job_data.get('job_url', ''),
                        "job_id": job_data.get('job_id', ''),
                        "location": job_data.get('location', ''),
                        "experience": job_data.get('experience', ''),
                        "salary_range": job_data.get('salary_range', ''),
                        "interview_rounds": job_data.get('interview_rounds', ''),
                    })
        logger.info(f"Found {len(firebase_jobs)} jobs in Firebase for user {user_email}")

        all_jobs = []
        seen_ids = set()

        for job in mongo_jobs:
            job_id = job.get('_id')
            if job_id and job_id not in seen_ids:
                all_jobs.append({
                    "_id": job_id,
                    "title": job.get('title', ''),
                    "description": job.get('description', ''),
                    "created_at": job.get('created_at', ''),
                    "expires_at": job.get('expires_at', ''),
                    "applications": job.get('applications', 0),
                    "user": job.get('user', ''),
                    "is_active": job.get('is_active', True),
                    "job_url": job.get('job_url', ''),
                    "job_id": job.get('job_id', ''),
                    "location": job.get('location', ''),
  
                })
                seen_ids.add(job_id)

        for job in firebase_jobs:
            job_id = job.get('_id')
            if job_id and job_id not in seen_ids:
                all_jobs.append(job)
                seen_ids.add(job_id)

        all_jobs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        logger.info(f"Total unique jobs found: {len(all_jobs)}")

        return JsonResponse({
            "success": True,
            "data": all_jobs
        }, status=200)
   except Exception as e:
        logger.error(f"Error fetching jobs: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            "success": False,
            "error": "Failed to fetch jobs",
            "details": str(e)
        }, status=500)
   
@login_required_firebase
def job_application(request, job_id):
    job = get_object_or_404(JobPosting, id=job_id)

    if now() > job.expires_at:
        return render(request, "expired.html")  

    if request.method == "POST":
        form = JobApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                resume = request.FILES["resume"]
                file_extension = resume.name.split('.')[-1]
                unique_filename = f"{uuid.uuid4()}.{file_extension}"
                
                # Create organized path structure in Firebase Storage
                storage_path = f"jobs/{job_id}/resumes/{unique_filename}"
                
                # Upload file to Firebase Storage
                storage.child(storage_path).put(resume)
                resume_url = storage.child(storage_path).get_url(None)

                # Save application to Django database
                application = form.save(commit=False)
                application.job = job
                application.resume_url = resume_url
                application.save()

                # Store application data in Firebase Realtime Database
                application_data = {
                    "job_id": str(job.id),
                    "application_id": str(uuid.uuid4()),
                    "first_name": application.first_name,
                    "last_name": application.last_name,
                    "email": application.email,
                    "phone": application.phone,
                    "resume_url": resume_url,
                    "resume_filename": unique_filename,
                    "applied_at": datetime.now().isoformat(),
                    "status": "new"  # Track application status
                }

                # Store in Firebase under organized structure
                db.child("applications").child(job_id).child(application_data["application_id"]).set(application_data)

                # Update application count in job listing
                job_ref = db.child("jobs").child(job_id)
                current_job = job_ref.get()
                if current_job.val():
                    current_count = current_job.val().get("applications", 0)
                    job_ref.update({"applications": current_count + 1})
                messages.success(request, "Application submitted successfully!")
                return redirect("success_page")
            except Exception as e:
                logger.error(f"Error in job application: {str(e)}")
                messages.error(request, "An error occurred while submitting your application. Please try again.")
                return render(request, "apply_job.html", {"form": form, "job": job})
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
        # Get Firebase auth instance
        auth = firebase.auth()
        
        # Get the current user's ID token
        user = request.session.get('user')
        if user and 'idToken' in user:
            try:
                # Revoke the refresh token
                auth.revoke_refresh_tokens(user['idToken'])
            except Exception as e:
                logger.warning(f"Could not revoke refresh token: {e}")
        
        request.session.flush()
        
        storage = messages.get_messages(request)
        for message in storage:
            pass  
        # This will clear all messages
        
        # Add success message
        messages.success(request, "You have been successfully logged out.")
        
        logger.info("User logged out successfully.")
        return redirect("landing")
    except Exception as e:
        logger.error(f"Error in logout_view: {e}\n{traceback.format_exc()}")
        messages.error(request, "An error occurred during logout.")
        return redirect("landing")


@login_required_firebase
def get_applications(request, job_id):
    try:
        # Get applications from MongoDB
        applications = list(settings.MCLIENT['resume_ner']['applications'].find(
            {"job_id": job_id},
            {"_id": 1, "name": 1, "email": 1, "phone": 1, "resume_url": 1, "applied_at": 1, "status": 1}
        ).sort("applied_at", -1))
        
        if not applications:
            return JsonResponse({
                "success": True,
                "data": []
            })
        
        # Get job details
        job = settings.MCLIENT['resume_ner']['job_listings'].find_one(
            {"_id": job_id},
            {"title": 1}
        )
        
        # Format applications data
        formatted_applications = []
        for app in applications:
            formatted_applications.append({
                "_id": str(app["_id"]),
                "name": app.get("name", ""),
                "email": app.get("email", ""),
                "phone": app.get("phone", ""),
                "resume_url": app.get("resume_url", ""),
                "applied_at": app.get("applied_at", ""),
                "status": app.get("status", "pending")
            })
        
        return JsonResponse({
            "success": True,
            "data": formatted_applications
        })
    except Exception as e:
        logger.error(f"Error fetching applications: {str(e)}")
        return JsonResponse({
            "success": False,
            "error": "Failed to fetch applications",
            "details": str(e)
        }, status=500)

@login_required_firebase
def dashboard(request):
    try:
        user_email = request.session.get("email")
        if not user_email:
            messages.error(request, "User not authenticated")
            return redirect("login")

        # Get jobs from MongoDB
        mongo_jobs = list(settings.MCLIENT['resume_ner']['job_listings'].find({"user": user_email}))
        
        # Get applications from MongoDB
        applications = list(settings.MCLIENT['resume_ner']['applications'].find({
            "job_id": {"$in": [job["_id"] for job in mongo_jobs]}
        }))

        # Calculate overview data
        total_jobs = len(mongo_jobs)
        active_applications = len(applications)
        pending_reviews = len([app for app in applications if app.get("status") == "pending"])
        shortlisted_candidates = len([app for app in applications if app.get("status") == "shortlisted"])

        # Get status distribution
        status_counts = {}
        for app in applications:
            status = app.get("status", "pending")
            status_counts[status] = status_counts.get(status, 0) + 1

        total_apps = len(applications)
        status_distribution = {
            "labels": list(status_counts.keys()),
            "values": [round((count / total_apps) * 100) if total_apps > 0 else 0 for count in status_counts.values()]
        }

        # Get applications over time (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        daily_counts = {}
        
        for app in applications:
            app_date = datetime.fromisoformat(app.get("applied_at"))
            if app_date.tzinfo is None:
                app_date = app_date.replace(tzinfo=timezone.utc)
            if app_date >= thirty_days_ago:
                date_str = app_date.strftime("%Y-%m-%d")
                daily_counts[date_str] = daily_counts.get(date_str, 0) + 1

        # Fill in missing dates with 0
        for i in range(30):
            date = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
            if date not in daily_counts:
                daily_counts[date] = 0

        applications_over_time = {
            "dates": sorted(daily_counts.keys()),
            "values": [daily_counts[date] for date in sorted(daily_counts.keys())]
        }

        # Get recent activity
        recent_activity = []
        for app in sorted(applications, key=lambda x: x.get("applied_at"), reverse=True)[:5]:
            recent_activity.append({
                "type": "application",
                "title": "New Application",
                "description": f"New application from {app.get('name')}",
                "timestamp": app.get("applied_at")
            })

        # Get top jobs
        job_applications = {}
        for app in applications:
            job_id = app.get("job_id")
            job_applications[job_id] = job_applications.get(job_id, 0) + 1

        top_jobs = []
        for job in mongo_jobs:
            job_id = job.get("_id")
            count = job_applications.get(job_id, 0)
            top_jobs.append({
                "title": job.get("title"),
                "applications": count,
                "status": "active" if job.get("is_active", True) else "inactive"
            })
        top_jobs.sort(key=lambda x: x["applications"], reverse=True)
        top_jobs = top_jobs[:5]

        # Add skill distribution data (sample data for now)
        skill_distribution = {
            "labels": ["Python", "JavaScript", "Java", "SQL", "React", "AWS"],
            "values": [35, 25, 20, 15, 30, 18]
        }

        # Add application sources data (sample data for now)
        application_sources = {
            "labels": ["LinkedIn", "Company Website", "Referral", "Job Boards"],
            "values": [40, 25, 20, 15]
        }

        context = {
            "overview": {
                "total_jobs": total_jobs,
                "active_applications": active_applications,
                "pending_reviews": pending_reviews,
                "shortlisted_candidates": shortlisted_candidates
            },
            "status_distribution": status_distribution,
            "applications_over_time": applications_over_time,
            "recent_activity": recent_activity,
            "top_jobs": top_jobs,
            "skill_distribution": skill_distribution,
            "application_sources": application_sources
        }

        return render(request, "dashboard.html", context)

    except Exception as e:
        logger.error(f"Error in dashboard view: {str(e)}\n{traceback.format_exc()}")
        messages.error(request, "An error occurred while loading the dashboard.")
        return redirect("login")

@login_required_firebase
def manage_candidates(request):
    return render(request, "manage_applications.html")

@login_required_firebase
@login_required_firebase
def create_job_page(request):
    try:
        user_email = request.session.get("email")
        if not user_email:
            messages.error(request, "User not authenticated")
            return redirect("login")

        mongo_jobs = list(settings.MCLIENT['resume_ner']['job_listings'].find({"user": user_email}))
        jobs = []
        for job in mongo_jobs:
            job_data = {
                "id": str(job.get("_id")),
                "title": job.get("title", ""),
                "department": job.get("department", ""),
                "location": job.get("location", ""),
                "applications": job.get("applications", 0),
                "is_active": job.get("is_active", True),
                "job_url": job.get("job_url", "")
            }
            
            created_at = job.get("created_at", {})
            if isinstance(created_at, dict) and "$date" in created_at:
                created_at = created_at["$date"]
            if created_at:
                job_data["created_at"] = datetime.fromisoformat(created_at.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
            
            expires_at = job.get("expires_at", "")
            if expires_at:
                job_data["expires_at"] = datetime.fromisoformat(expires_at).strftime("%Y-%m-%d %H:%M:%S")
            
            jobs.append(job_data)

        return render(request, "create_job.html", {"jobs": jobs})

    except Exception as e:
        logger.error(f"Error in create_job_page: {str(e)}\n{traceback.format_exc()}")
        messages.error(request, "An error occurred while loading the page.")
        return redirect("dashboard")
def job_page(request, job_id):
    try:
        job = settings.MCLIENT['resume_ner']['job_listings'].find_one({"_id": job_id})
        
        if not job:
            return HttpResponse("Job not found.", status=404)

        company = settings.MCLIENT['resume_ner']['company_details'].find_one({"user": job.get("user")})
        
        if not company:
            company = {
                "company_name": "Company Name",
                "industry": "Industry",
                "company_size": "Company Size",
                "founded": "Year Founded",
                "website": "#",
                "description": "Company Description",
                "mission": "Company Mission",
                "vision": "Company Vision",
                "values": "Company Values"
            }

        job_data = {
            "title": job.get("title", ""),
            "experience": job.get("experience", ""),
            "salary_range": job.get("salary_range", ""),
            "location": job.get("location", ""),
            "description": job.get("description", ""),
            "created_at": job.get("created_at", ""),
            "expires_at": job.get("expires_at", ""),
            "is_active": job.get("is_active", True),
            "job_id": job_id,
            "company_name": company.get("company_name", ""),
            "industry": company.get("industry", ""),
            "company_size": company.get("size", ""),
            "founded": company.get("founded", ""),
            "website": company.get("website", ""),
            "company_description": company.get("description", ""),
            "mission": company.get("mission", ""),
            "vision": company.get("vision", ""),
            "values": company.get("values", "")
        }

        try:
            expires_at = parser.isoparse(job_data["expires_at"])
            if expires_at < datetime.now(timezone.utc):
                job_data["is_active"] = False
        except (ValueError, KeyError):
            job_data["is_active"] = False

        return render(request, "job_detail.html", {"job": job_data})

    except Exception as e:
        logger.error(f"Error in job_page view: {str(e)}\n{traceback.format_exc()}")
        return HttpResponse("An error occurred while loading the job page.", status=500)


def upload_resume(file, job_id, filename):
    """Upload resume to Firebase Storage with proper path structure"""
    try:
        # Create organized path structure
        storage_path = f"jobs/{job_id}/resumes/{filename}"
        
        # Upload to Firebase Storage
        # First, read the file content and reset the file pointer
        file_content = file.read()
        file.seek(0)  # Reset file pointer for potential future reads
        
        # Upload the file content
        storage.child(storage_path).put(file_content)
        
        # Get the public URL
        resume_url = storage.child(storage_path).get_url(None)
        return resume_url
    except Exception as e:
        logger.error(f"Error uploading resume: {str(e)}")
        raise

@login_required_firebase
def submit_application(request):
    if request.method == "POST":
        try:
            job_id = request.POST.get("job_id")
            name = request.POST.get("name")
            email = request.POST.get("email")
            phone = request.POST.get("phone")
            resume_file = request.FILES.get("resume")
            
            if not all([job_id, name, email, phone, resume_file]):
                return JsonResponse({"error": "Missing required fields"}, status=400)
            
            # Generate unique filename
            file_extension = resume_file.name.split('.')[-1]
            unique_filename = f"{uuid.uuid4()}.{file_extension}"
            
            # Upload resume to Firebase Storage
            storage_path = f"jobs/{job_id}/resumes/{unique_filename}"
            storage.child(storage_path).put(resume_file)
            resume_url = storage.child(storage_path).get_url(None)
            
            # Create application data
            application_data = {
                "_id": str(uuid.uuid4()),
                "name": name,
                "email": email,
                "phone": phone,
                "resume_url": resume_url,
                "resume_filename": unique_filename,
                "job_id": job_id,
                "applied_at": datetime.now().isoformat(),
                "status": "pending",
                "updated_at": datetime.now().isoformat()
            }
            
            # Store in MongoDB
            settings.MCLIENT['resume_ner']['applications'].insert_one(application_data)
            
            # Update application count in job listing
            settings.MCLIENT['resume_ner']['job_listings'].update_one(
                {"_id": job_id},
                {"$inc": {"applications": 1}}
            )
            
            return JsonResponse({
                "success": True,
                "message": "Application submitted successfully!",
                "application_id": application_data["_id"]
            })
            
        except Exception as e:
            logger.error(f"Error in submit_application: {str(e)}")
            return JsonResponse({
                "error": "Failed to submit application",
                "details": str(e)
            }, status=500)
    
    return JsonResponse({"error": "Invalid request method"}, status=400)

@login_required_firebase
def update_application_status(request, application_id):
    try:
        if request.method == "POST":
            new_status = request.POST.get("status")
            
            if not new_status:
                return JsonResponse({"error": "Missing status field"}, status=400)
            
            # Update status in MongoDB
            result = settings.MCLIENT['resume_ner']['applications'].update_one(
                {"_id": application_id},
                {
                    "$set": {
                        "status": new_status,
                        "updated_at": datetime.now().isoformat()
                    }
                }
            )
            
            if result.modified_count > 0:
                return JsonResponse({
                    "success": True,
                    "message": "Status updated successfully"
                })
            else:
                return JsonResponse({
                    "success": False,
                    "error": "Application not found"
                }, status=404)
            
    except Exception as e:
        logger.error(f"Error updating application status: {str(e)}")
        return JsonResponse({
            "success": False,
            "error": "Failed to update status",
            "details": str(e)
        }, status=500)

@login_required_firebase
def manage_applications(request):
    try:
        return render(request, "manage_applications.html")
    except Exception as e:
        logger.error(f"Error in manage_applications view: {str(e)}\n{traceback.format_exc()}")
        messages.error(request, "An error occurred while loading the page.")
        return redirect("dashboard")

@login_required_firebase
def get_dashboard_data(request):
    try:
        user_email = request.session.get("email")
        if not user_email:
            return JsonResponse({"success": False, "error": "User not authenticated"}, status=401)

        logger.info(f"Fetching dashboard data for user: {user_email}")

        # Get jobs from MongoDB
        mongo_jobs = list(settings.MCLIENT['resume_ner']['job_listings'].find({"user": user_email}))
        logger.info(f"Found {len(mongo_jobs)} jobs in MongoDB")

        # Get applications from MongoDB
        applications = list(settings.MCLIENT['resume_ner']['applications'].find({
            "job_id": {"$in": [job["_id"] for job in mongo_jobs]}
        }))
        logger.info(f"Found {len(applications)} applications")

        # Calculate overview data
        total_jobs = len(mongo_jobs)
        active_applications = len(applications)
        pending_reviews = len([app for app in applications if app.get("status") == "pending"])
        shortlisted_candidates = len([app for app in applications if app.get("status") == "shortlisted"])

        # Get status distribution
        status_counts = {}
        for app in applications:
            status = app.get("status", "pending")
            status_counts[status] = status_counts.get(status, 0) + 1

        total_apps = len(applications)
        status_distribution = {
            "labels": list(status_counts.keys()),
            "values": [round((count / total_apps) * 100) if total_apps > 0 else 0 for count in status_counts.values()]
        }

        # Get applications over time (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        daily_counts = {}
        
        for app in applications:
            app_date = datetime.fromisoformat(app.get("applied_at"))
            if app_date.tzinfo is None:
                app_date = app_date.replace(tzinfo=timezone.utc)
            if app_date >= thirty_days_ago:
                date_str = app_date.strftime("%Y-%m-%d")
                daily_counts[date_str] = daily_counts.get(date_str, 0) + 1

        # Fill in missing dates with 0
        for i in range(30):
            date = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
            if date not in daily_counts:
                daily_counts[date] = 0

        applications_over_time = {
            "dates": sorted(daily_counts.keys()),
            "values": [daily_counts[date] for date in sorted(daily_counts.keys())]
        }

        # Get recent activity
        recent_activity = []
        for app in sorted(applications, key=lambda x: x.get("applied_at"), reverse=True)[:5]:
            recent_activity.append({
                "type": "application",
                "title": "New Application",
                "description": f"New application from {app.get('name')}",
                "timestamp": app.get("applied_at")
            })

        # Get top jobs
        job_applications = {}
        for app in applications:
            job_id = app.get("job_id")
            job_applications[job_id] = job_applications.get(job_id, 0) + 1

        top_jobs = []
        for job in mongo_jobs:
            job_id = job.get("_id")
            count = job_applications.get(job_id, 0)
            top_jobs.append({
                "title": job.get("title"),
                "applications": count,
                "status": "active" if job.get("is_active", True) else "inactive"
            })
        top_jobs.sort(key=lambda x: x["applications"], reverse=True)
        top_jobs = top_jobs[:5]

        # Add skill distribution data (sample data for now)
        skill_distribution = {
            "labels": ["Python", "JavaScript", "Java", "SQL", "React", "AWS"],
            "values": [35, 25, 20, 15, 30, 18]
        }

        # Add application sources data (sample data for now)
        application_sources = {
            "labels": ["LinkedIn", "Company Website", "Referral", "Job Boards"],
            "values": [40, 25, 20, 15]
        }

        response_data = {
            "success": True,
            "data": {
                "overview": {
                    "total_jobs": total_jobs,
                    "active_applications": active_applications,
                    "pending_reviews": pending_reviews,
                    "shortlisted_candidates": shortlisted_candidates
                },
                "status_distribution": status_distribution,
                "applications_over_time": applications_over_time,
                "recent_activity": recent_activity,
                "top_jobs": top_jobs,
                "skill_distribution": skill_distribution,
                "application_sources": application_sources
            }
        }

        logger.info(f"Dashboard data prepared successfully: {response_data}")
        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"Error in get_dashboard_data: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            "success": False,
            "error": "Failed to fetch dashboard data",
            "details": str(e)
        }, status=500)

@login_required_firebase
def toggle_job_status(request):
    if request.method == 'POST':
        try:
            job_id = request.POST.get('job_id')
            user_email = request.session.get('email')
            print(job_id, user_email)
            if not job_id or not user_email:
                return JsonResponse({
                    'success': False,
                    'message': 'Missing required parameters'
                })
            
            # Get current job status from MongoDB
            job = settings.MCLIENT['resume_ner']['job_listings'].find_one({
                "_id": job_id,
                "user": user_email
            })
            
            if not job:
                return JsonResponse({
                    'success': False,
                    'message': 'Job not found'
                })
            
            # Check if job has expired
            expires_at = job.get('expires_at')
            if expires_at:
                expires_at = datetime.fromisoformat(expires_at)
                if expires_at < datetime.now(timezone.utc):
                    return JsonResponse({
                        'success': False,
                        'message': 'Cannot toggle status of expired job'
                    })
            
            # Toggle status
            current_status = job.get('is_active', True)
            new_status = not current_status
            
            # Update in MongoDB
            settings.MCLIENT['resume_ner']['job_listings'].update_one(
                {"_id": job_id},
                {"$set": {"is_active": new_status}}
            )
            
            # Update in Firebase
            db.child("jobs").child(job_id).update({"is_active": new_status})
            
            return JsonResponse({
                'success': True,
                'message': 'Job status updated successfully',
                'new_status': new_status
            })
            
        except Exception as e:
            logger.error(f"Error toggling job status: {str(e)}\n{traceback.format_exc()}")
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    })

@login_required_firebase
def company_details(request):
    try:
        user_email = request.session.get('email')
        if not user_email:
            return redirect('login')

        # Get company details from MongoDB
        company = settings.MCLIENT['resume_ner']['company_details'].find_one({"user": user_email})
        
        if request.method == 'POST':
            # Update company details
            company_data = {
                "user": user_email,
                "company_name": request.POST.get('company_name'),
                "website": request.POST.get('website'),
                "industry": request.POST.get('industry'),
                "size": request.POST.get('size'),
                "founded": request.POST.get('founded'),
                "description": request.POST.get('description'),
                "mission": request.POST.get('mission'),
                "vision": request.POST.get('vision'),
                "values": request.POST.get('values'),
                "benefits": request.POST.get('benefits'),
                "culture": request.POST.get('culture'),
                "address": {
                    "street": request.POST.get('street'),
                    "city": request.POST.get('city'),
                    "state": request.POST.get('state'),
                    "country": request.POST.get('country'),
                    "zip_code": request.POST.get('zip_code')
                },
                "contact": {
                    "email": request.POST.get('contact_email'),
                    "phone": request.POST.get('contact_phone'),
                    "linkedin": request.POST.get('linkedin'),
                    "twitter": request.POST.get('twitter')
                },
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            if company:
                # Update existing company details
                settings.MCLIENT['resume_ner']['company_details'].update_one(
                    {"user": user_email},
                    {"$set": company_data}
                )
            else:
                # Create new company details
                settings.MCLIENT['resume_ner']['company_details'].insert_one(company_data)
                company = company_data

            messages.success(request, 'Company details updated successfully!')
            return redirect('company_details')

        return render(request, 'company_details.html', {'company': company})

    except Exception as e:
        logger.error(f"Error in company_details view: {str(e)}\n{traceback.format_exc()}")
        messages.error(request, 'An error occurred while processing your request.')
        return redirect('dashboard')

@csrf_exempt
def chatbot(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '')
            
            if not user_message:
                return JsonResponse({
                    'success': False,
                    'error': 'Message cannot be empty'
                }, status=400)
            
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            context = """
            You are a helpful assistant for Ner Resume, a smart resume analysis platform. 
            Your role is to help users understand the platform's features and capabilities.
            You should only provide information about:
            1. Resume analysis features
            2. Job posting capabilities
            3. Application management
            4. Candidate screening
            5. Platform usage instructions
            
            If asked about anything outside these topics, politely inform the user that you can only discuss Ner Resume related topics.
            Keep your responses concise and to the point.
            """
            
            try:
                response = model.generate_content(f"{context}\nUser: {user_message}")
                
                if not response.text:
                    raise Exception("Empty response from Gemini API")
                
                return JsonResponse({
                    'success': True,
                    'response': response.text
                })
                
            except Exception as e:
                logger.error(f"Error generating response: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to generate response',
                    'details': str(e)
                }, status=500)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Unexpected error in chatbot view: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'An unexpected error occurred'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    }, status=400)