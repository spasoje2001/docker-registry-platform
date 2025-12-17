# Docker Registry Platform

Web application for sharing Docker images, developed as a project for the Software Configuration Management (UKS) course at Faculty of Technical Sciences, Novi Sad.

## Team

- [Spasoje Brborić](https://github.com/spasoje2001)
- [Luka Zelović](https://github.com/Zela11)
- [Milica Đumić](https://github.com/dumitka)
- [Luka Milanko](https://github.com/Lukaa01)

## About

This application is a simplified version of the DockerHub platform. It allows users to register, create and manage Docker image repositories, search public repositories, and provides administrators with system monitoring capabilities through log analysis.

Key features:
- User registration and authentication with role-based access control
- Repository management (create, update, delete, visibility settings)
- Public repository search with relevance-based sorting
- Tag management for Docker images
- Admin panel for user and official repository management
- System analytics powered by Elasticsearch

## Tech Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Backend Framework | Django | 5.x |
| Database | PostgreSQL | 15 |
| Cache | Redis | 7 |
| Reverse Proxy | NGINX | alpine |
| Search Engine | Elasticsearch | 8.11 |
| Container Registry | Distribution | 2 |
| CI/CD | GitHub Actions | - |
| Containerization | Docker + Docker Compose | - |

## Prerequisites

Before you begin, ensure you have the following installed:

- [Git](https://git-scm.com/downloads)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
- [Python 3.12+](https://www.python.org/downloads/) (for local development without Docker)

## Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/spasoje2001/docker-registry-platform.git
cd docker-registry-platform
```

### 2. Configure Environment Variables
Create your local environment file from the template:
```bash
# Copy the template
cp .env.example .env
```

### 3. Start the Application
```bash
docker-compose up --build
```

First run will take 5-10 minutes to download all images.

### 4. Initialize the Database
Run migrations to create database tables:
```bash
docker-compose exec web python manage.py migrate
```

### 5. Create Super Administrator
Create the super admin account (run this ONLY ONCE):
```bash
docker-compose exec web python manage.py setup_admin
```

View the generated credentials:
```bash
cat admin_password.txt
```

**Important:** This command is idempotent (safe to run multiple times). Super admin will be forced to change password on first login.

### 6. Verify Everything is Running

Open in browser:
- Application: http://localhost
- Elasticsearch: http://localhost:9200 (should return JSON)
- Registry: http://localhost:5000/v2/ (should return `{}`)

Login at http://localhost/admin with credentials from `admin_password.txt`.

### 7. Stop the Application

Press `Ctrl+C` in the terminal, then:
```bash
docker-compose down
```

## Development Guide

### Docker Commands Reference

| Command | Description |
|---------|-------------|
| `docker-compose up` | Start all services |
| `docker-compose up --build` | Start and rebuild images (use after changing Dockerfile or requirements.txt) |
| `docker-compose up -d` | Start in background (detached mode) |
| `docker-compose down` | Stop and remove containers (data persists) |
| `docker-compose down -v` | Stop and remove containers AND volumes (deletes database!) |
| `docker-compose logs web` | View Django logs |
| `docker-compose logs -f` | Follow all logs in real-time |
| `docker-compose restart web` | Restart only Django service |
| `docker-compose exec web bash` | Open shell inside Django container |

### When to Rebuild

| Change | Command Needed |
|--------|----------------|
| Python code changes | Nothing (auto-reload) |
| requirements.txt changes | `docker-compose up --build` |
| Dockerfile changes | `docker-compose up --build` |
| docker-compose.yml changes | `docker-compose down` then `docker-compose up` |
| nginx.conf changes | `docker-compose restart nginx` |

### Database Access
```bash
# PostgreSQL CLI
docker-compose exec db psql -U postgres -d dockerhub

# Useful psql commands:
# \dt          - list tables
# \d tablename - describe table
# \q           - quit
```
### Registry configuration

### 1. Create htpasswd file

Create htpasswd file locally using Docker htpasswd image.

```docker run --rm httpd:2.4-alpine htpasswd -Bbn admin Admin123 > auth/htpasswd```

Do not edit file manually. Encode it to UTF-8 LF.

### 2. Test login

```docker login localhost:5000```

Enter the credentials:
Username: admin
Password: Admin123

Then, in command prompt, to get all repositories:

```curl -i -u admin:Admin123 http://localhost:5000/v2/_catalog```

or in Powershell:

```(Invoke-WebRequest -Uri "http://localhost:5000/v2/_catalog" -Headers @{Authorization = "Basic $([Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes('admin:Admin123')))"}).Content```

### Running Tests Locally

**Option A: Inside Docker (recommended)**
```bash
docker-compose exec web python manage.py test
```

**Option B: Local virtual environment**
```bash
cd app
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python manage.py test
```

### Running Linter Locally

Run linter before committing to avoid CI failures:

**Option A: Inside Docker**
```bash
docker-compose exec web flake8 .
```

**Option B: Local virtual environment**
```bash
cd app
venv\Scripts\activate
flake8 .
```

**Linter rules:**
- Max line length: 127 characters
- Max complexity: 10

### Running Migrations
```bash
# Create new migrations after model changes
docker-compose exec web python manage.py makemigrations

# Apply migrations
docker-compose exec web python manage.py migrate
```

### Creating a Superuser (for Django Admin)
```bash
docker-compose exec web python manage.py createsuperuser
```

Then access Django Admin at: http://localhost/admin

## Git Workflow

This project follows the [GitFlow](https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow) branching model.

### Branches

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready releases only |
| `develop` | Active development, integration branch |
| `feature-*` | New features (e.g., `feature-user-authentication`) |
| `bugfix-*` | Bug fixes (e.g., `bugfix-login-redirect`) |

### Rules

- All code changes must go through Pull Requests
- PRs require at least one approval before merging
- CI checks must pass before merging
- Feature and bugfix branches are created from `develop`
- Only `develop` is merged into `main` during releases

## Conventions

### Commit Messages

Format: `<type>: <description>`

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation changes |
| `test` | Adding or updating tests |
| `refactor` | Code refactoring |
| `chore` | Maintenance tasks |
| `style` | Code style changes (formatting, no logic change) |

### Branch Naming

- Features: `feature-<short-description>`
- Bug fixes: `bugfix-<short-description>`

Use lowercase letters and hyphens, no spaces.

## Project Structure
```
docker-registry-platform/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml              # CI pipeline (runs on PR)
│   │   └── deploy.yml          # Deploy pipeline (runs on release)
│   ├── ISSUE_TEMPLATE/
│   │   ├── feature.md
│   │   └── bug.md
│   └── pull_request_template.md
├── app/
│   ├── accounts/               # User management app
│   ├── analytics/              # Elasticsearch logs app
│   ├── config/                 # Django project settings
│   ├── explore/                # Search functionality app
│   ├── repositories/           # Repository management app
│   ├── templates/              # HTML templates
│   ├── Dockerfile
│   ├── manage.py
│   ├── pytest.ini
│   └── requirements.txt
├── docs/                       # Documentation and diagrams
├── nginx/
│   └── nginx.conf
├── auth/
│   └── htpasswd
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

## API Documentation

*To be added.*

## Troubleshooting

### Port already in use

If you get an error about port 80 being in use:
```bash
# Find process using port 80
netstat -ano | findstr :80

# Kill the process (replace PID with actual number)
taskkill /PID  /F
```

Or change the port in `docker-compose.yml`:
```yaml
nginx:
  ports:
    - "8080:80"  # Access via localhost:8080
```

### Database connection issues
```bash
# Reset everything
docker-compose down -v
docker-compose up --build
```

### Elasticsearch not starting

Elasticsearch needs at least 4GB of RAM. If you have less:

1. Reduce memory in `docker-compose.yml`:
```yaml
   elasticsearch:
     environment:
       - "ES_JAVA_OPTS=-Xms256m -Xmx256m"
```

2. Or disable Elasticsearch temporarily by commenting it out in `docker-compose.yml`
