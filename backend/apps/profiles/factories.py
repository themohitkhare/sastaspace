import factory
from factory.django import DjangoModelFactory
from apps.users.factories import UserFactory
from .models import Profile

class ProfileFactory(DjangoModelFactory):
    """Factory for creating test profiles"""
    
    class Meta:
        model = Profile
    
    user = factory.SubFactory(UserFactory)
    linkedin_url = factory.Sequence(lambda n: f'https://linkedin.com/in/user{n}/')
    linkedin_username = factory.Sequence(lambda n: f'user{n}')
    resume_text = factory.Faker('text', max_nb_chars=500)
    ai_analysis_cache = factory.LazyFunction(lambda: {
        'professional_summary': 'Experienced software engineer with expertise in Python and Django.',
        'skills': ['Python', 'Django', 'React', 'JavaScript'],
        'formatted_experience': [
            {
                'title': 'Senior Developer',
                'company': 'Tech Corp',
                'dates': '2020-2023',
                'description': 'Led development team and built scalable applications'
            }
        ],
        'formatted_education': [
            {
                'institution': 'University of Technology',
                'degree': 'Master of Computer Science',
                'dates': '2016-2018'
            }
        ],
        'actionable_feedback': [
            'Add more quantifiable achievements',
            'Include specific technologies used',
            'Highlight leadership experience'
        ]
    })

class ProfileWithResumeFactory(DjangoModelFactory):
    """Factory for creating test profiles with resume files"""
    
    class Meta:
        model = Profile
    
    user = factory.SubFactory(UserFactory)
    linkedin_url = factory.Sequence(lambda n: f'https://linkedin.com/in/user{n}/')
    linkedin_username = factory.Sequence(lambda n: f'user{n}')
    resume_text = factory.Faker('text', max_nb_chars=500)
    resume_file = factory.django.FileField(filename='test_resume.pdf')
    ai_analysis_cache = None

class ProfileWithAIAnalysisFactory(DjangoModelFactory):
    """Factory for creating test profiles with AI analysis cache"""
    
    class Meta:
        model = Profile
    
    user = factory.SubFactory(UserFactory)
    linkedin_url = factory.Sequence(lambda n: f'https://linkedin.com/in/user{n}/')
    linkedin_username = factory.Sequence(lambda n: f'user{n}')
    resume_text = factory.Faker('text', max_nb_chars=500)
    ai_analysis_cache = factory.LazyFunction(lambda: {
        'professional_summary': 'Experienced software engineer with expertise in Python and Django.',
        'skills': ['Python', 'Django', 'React', 'JavaScript'],
        'formatted_experience': [
            {
                'title': 'Senior Developer',
                'company': 'Tech Corp',
                'dates': '2020-2023',
                'description': 'Led development team and built scalable applications'
            },
            {
                'title': 'Junior Developer',
                'company': 'Startup Inc',
                'dates': '2018-2020',
                'description': 'Built web applications using modern technologies'
            }
        ],
        'formatted_education': [
            {
                'institution': 'University of Technology',
                'degree': 'Master of Computer Science',
                'dates': '2016-2018'
            },
            {
                'institution': 'State University',
                'degree': 'Bachelor of Computer Science',
                'dates': '2012-2016'
            }
        ],
        'actionable_feedback': [
            'Add more quantifiable achievements',
            'Include specific technologies used',
            'Highlight leadership experience',
            'Add certifications and training'
        ]
    }) 