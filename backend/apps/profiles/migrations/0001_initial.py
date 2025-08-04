from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('linkedin_url', models.URLField(unique=True)),
                ('linkedin_username', models.CharField(blank=True, max_length=100, unique=True)),
                ('resume_file', models.FileField(upload_to='resumes/')),
                ('resume_text', models.TextField(blank=True)),
                ('ai_analysis_cache', models.JSONField(blank=True, null=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='users.customuser')),
            ],
        ),
    ]
