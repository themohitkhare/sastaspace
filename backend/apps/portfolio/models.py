from djongo import models
from apps.profiles.models import Profile

class Portfolio(models.Model):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE)
    slug = models.SlugField(unique=True, max_length=150)
    professional_summary = models.TextField()
    skills = models.JSONField()
    work_experience = models.JSONField()
    education = models.JSONField()
    template_choice = models.CharField(max_length=20, default='default')

    def __str__(self):
        return f"Portfolio for {self.slug}"
