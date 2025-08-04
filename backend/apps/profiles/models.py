from djongo import models
from django.conf import settings

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    linkedin_url = models.URLField(unique=True)
    linkedin_username = models.CharField(max_length=100, unique=True, blank=True)
    resume_file = models.FileField(upload_to='resumes/')
    resume_text = models.TextField(blank=True)
    ai_analysis_cache = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"Profile of {self.user.email}"
