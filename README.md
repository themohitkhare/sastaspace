# 🚀 SASTASPACE - Portfolio Management Platform

A modern, scalable portfolio management platform built with Django, React, and Docker Swarm.

## ⚠️ SECURITY ALERT

**CRITICAL**: This application has significant security vulnerabilities. **DO NOT DEPLOY TO PRODUCTION** without addressing the security issues identified in the [Security Audit](./docs/SECURITY_AUDIT.md).

## 📋 PROJECT OVERVIEW

SastaSpace is a full-stack web application that helps users create and manage professional portfolios. The platform features:

- **User Authentication**: Secure email-based authentication
- **Profile Management**: Resume upload and LinkedIn integration
- **AI-Powered Analysis**: Automated portfolio generation using Google Gemini AI
- **Portfolio Templates**: Multiple customizable portfolio templates
- **Scalable Architecture**: Docker Swarm deployment with autoscaling

## 🏗️ ARCHITECTURE

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Database      │
│   (React)       │◄──►│   (Django)      │◄──►│   (MongoDB)     │
│   Port: 3000    │    │   Port: 8000    │    │   Port: 27017   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Nginx Proxy    │
                    │   Port: 80/443   │
                    └─────────────────┘
```

## 🚀 QUICK START

### Prerequisites
- Docker and Docker Compose
- Docker Swarm (for production deployment)
- Python 3.9+
- Node.js 18+

### Development Setup
```bash
# Clone the repository
git clone <repository-url>
cd sastaspace

# Set up environment variables
cp .env.example backend/.env
# Edit backend/.env with your actual values

# Start development environment
docker-compose up -d
```

### Production Deployment
```bash
# Initialize Docker Swarm
docker swarm init

# Deploy to production
docker stack deploy -c docker-compose.swarm.yml sastaspace
```

## 📚 DOCUMENTATION

All documentation is organized in the [`docs/`](./docs/) folder:

- **[Security Audit](./docs/SECURITY_AUDIT.md)** - 🔴 **CRITICAL**: Must review before deployment
- **[Autoscaling Guide](./docs/AUTOSCALING.md)** - Docker Swarm configuration
- **[Development Docs](./docs/README.md)** - Complete documentation index

## 🔒 SECURITY STATUS

| Component | Status | Issues |
|-----------|--------|--------|
| Environment Variables | 🔴 Critical | Hardcoded secrets |
| Django Configuration | 🔴 Critical | DEBUG mode enabled |
| File Uploads | 🟠 High | Missing validation |
| HTTPS | 🟡 Medium | Not configured |
| Dependencies | 🟡 Medium | Outdated Django |

**Immediate Actions Required:**
1. Generate secure environment variables
2. Disable DEBUG mode in production
3. Implement file upload validation
4. Configure HTTPS
5. Upgrade Django version

## 🛠️ DEVELOPMENT

### Backend (Django)
```bash
cd backend
python manage.py runserver
```

### Frontend (React)
```bash
cd frontend
npm install
npm run dev
```

### Testing
```bash
# Backend tests
cd backend
python manage.py test

# Frontend tests
cd frontend
npm test
```

## 📊 MONITORING

- **Health Check**: `http://localhost/health/`
- **API Documentation**: Available at `/api/`
- **Admin Interface**: Available at `/admin/`

## 🤝 CONTRIBUTING

1. Review the [Security Audit](./docs/SECURITY_AUDIT.md) first
2. Follow the development workflow in the docs
3. Ensure all tests pass before submitting PR
4. Address any security concerns immediately

## 📄 LICENSE

[Add your license information here]

---

**⚠️ IMPORTANT**: Before deploying to production, ensure all security issues identified in the [Security Audit](./docs/SECURITY_AUDIT.md) have been resolved.

**Last Updated**: August 4, 2025  
**Version**: 1.0.0 