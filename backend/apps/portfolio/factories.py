import factory
from factory.django import DjangoModelFactory
from apps.profiles.factories import ProfileFactory
from .models import Portfolio

class PortfolioFactory(DjangoModelFactory):
    """Factory for creating test portfolios"""
    
    class Meta:
        model = Portfolio
    
    profile = factory.SubFactory(ProfileFactory)
    slug = factory.Sequence(lambda n: f'user{n}')
    professional_summary = factory.Faker('text', max_nb_chars=200)
    skills = factory.LazyFunction(lambda: ['Python', 'Django', 'React', 'JavaScript'])
    work_experience = factory.LazyFunction(lambda: [
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
    ])
    education = factory.LazyFunction(lambda: [
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
    ])
    template_choice = 'default'

class PortfolioWithMinimalDataFactory(DjangoModelFactory):
    """Factory for creating test portfolios with minimal data"""
    
    class Meta:
        model = Portfolio
    
    profile = factory.SubFactory(ProfileFactory)
    slug = factory.Sequence(lambda n: f'minimal{n}')
    professional_summary = ''
    skills = factory.LazyFunction(lambda: [])
    work_experience = factory.LazyFunction(lambda: [])
    education = factory.LazyFunction(lambda: [])
    template_choice = 'default'

class PortfolioWithExtensiveDataFactory(DjangoModelFactory):
    """Factory for creating test portfolios with extensive data"""
    
    class Meta:
        model = Portfolio
    
    profile = factory.SubFactory(ProfileFactory)
    slug = factory.Sequence(lambda n: f'extensive{n}')
    professional_summary = factory.Faker('text', max_nb_chars=500)
    skills = factory.LazyFunction(lambda: [
        'Python', 'Django', 'React', 'JavaScript', 'TypeScript',
        'Node.js', 'PostgreSQL', 'MongoDB', 'Docker', 'Kubernetes',
        'AWS', 'Git', 'CI/CD', 'REST APIs', 'GraphQL'
    ])
    work_experience = factory.LazyFunction(lambda: [
        {
            'title': 'Senior Software Engineer',
            'company': 'Tech Corp',
            'dates': '2020-2023',
            'description': 'Led development team of 8 engineers and built scalable microservices architecture'
        },
        {
            'title': 'Full Stack Developer',
            'company': 'Startup Inc',
            'dates': '2018-2020',
            'description': 'Built and maintained multiple web applications using React and Django'
        },
        {
            'title': 'Junior Developer',
            'company': 'Web Solutions',
            'dates': '2016-2018',
            'description': 'Developed responsive web applications and implemented REST APIs'
        }
    ])
    education = factory.LazyFunction(lambda: [
        {
            'institution': 'University of Technology',
            'degree': 'Master of Computer Science',
            'dates': '2016-2018',
            'description': 'Specialized in Software Engineering and Machine Learning'
        },
        {
            'institution': 'State University',
            'degree': 'Bachelor of Computer Science',
            'dates': '2012-2016',
            'description': 'Graduated with honors, minor in Mathematics'
        }
    ])
    template_choice = 'modern'

class PortfolioWithCustomTemplateFactory(DjangoModelFactory):
    """Factory for creating test portfolios with custom template"""
    
    class Meta:
        model = Portfolio
    
    profile = factory.SubFactory(ProfileFactory)
    slug = factory.Sequence(lambda n: f'custom{n}')
    professional_summary = factory.Faker('text', max_nb_chars=300)
    skills = factory.LazyFunction(lambda: ['Python', 'Django', 'React'])
    work_experience = factory.LazyFunction(lambda: [
        {
            'title': 'Developer',
            'company': 'Tech Corp',
            'dates': '2020-2023',
            'description': 'Built applications'
        }
    ])
    education = factory.LazyFunction(lambda: [
        {
            'institution': 'University',
            'degree': 'Computer Science',
            'dates': '2016-2020'
        }
    ])
    template_choice = 'custom' 