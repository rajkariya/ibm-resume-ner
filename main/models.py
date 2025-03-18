from django.db import models
from django.utils import timezone
import uuid

class JobPosting(models.Model):
    """Stores Job Descriptions with expiration and unique link"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_active(self):
        """Check if job posting is still active"""
        return timezone.now() < self.expires_at

class JobApplication(models.Model):
    """Stores job applications linked to a JobPosting"""
    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    resume_url = models.URLField()  # Stores Firebase URL
    applied_at = models.DateTimeField(auto_now_add=True)
