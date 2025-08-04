from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='Portfolio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(max_length=150, unique=True)),
                ('professional_summary', models.TextField()),
                ('skills', models.JSONField()),
                ('work_experience', models.JSONField()),
                ('education', models.JSONField()),
                ('template_choice', models.CharField(default='default', max_length=20)),
                ('profile', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='profiles.profile')),
            ],
        ),
    ]
