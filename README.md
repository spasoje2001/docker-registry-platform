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

## Local Setup

*To be added.*

## Project Structure
```
docker-registry-platform/
├── .github/
│   ├── workflows/          # CI/CD pipeline definitions
│   └── ISSUE_TEMPLATE/     # Issue templates
├── app/                    # Django application
├── nginx/                  # NGINX configuration
├── docs/                   # Documentation and diagrams
├── docker-compose.yml
├── .gitignore
└── README.md
```

*To be updated during development.*

## API Documentation

*To be added.*

## Deployment

*To be added.*
