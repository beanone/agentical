# FastAPI Development Guidelines

## Overview

These guidelines provide best practices for developing FastAPI applications, focusing on code organization, performance, reliability, and security.

## Architecture

### Project Structure

```
project_root/
├── app/                  # Main application package
│   ├── __init__.py       # Package initializer
│   ├── main.py           # Application entry point
│   ├── api/              # API endpoints
│   │   ├── __init__.py
│   │   ├── dependencies.py  # Shared dependencies
│   │   ├── v1/           # API version 1
│   │   │   ├── __init__.py
│   │   │   ├── router.py # Main router for v1
│   │   │   └── endpoints/ # API endpoint modules
│   ├── core/             # Core application code
│   │   ├── __init__.py
│   │   ├── config.py     # Configuration
│   │   ├── security.py   # Security utilities
│   │   └── exceptions.py # Custom exceptions
│   ├── db/               # Database models and utilities
│   │   ├── __init__.py
│   │   ├── session.py    # Database session
│   │   └── models/       # Database models
│   ├── models/           # Pydantic models
│   │   ├── __init__.py
│   │   └── domain/       # Domain models
│   ├── schemas/          # Request/response schemas
│   │   └── __init__.py
│   ├── services/         # Business logic services
│   │   └── __init__.py
│   └── utils/            # Utility functions
│       └── __init__.py
├── tests/                # Test directory
│   ├── __init__.py
│   ├── conftest.py       # Test configuration
│   └── api/              # API tests
├── alembic/              # Database migrations
├── .env                  # Environment variables
├── .gitignore            # Git ignore file
├── requirements.txt      # Dependencies
├── README.md             # Project documentation
└── docker-compose.yml    # Docker configuration
```

### Component Organization

1. **ALWAYS** separate concerns: routers, models, services, and database operations
2. **ALWAYS** use dependency injection for services and database connections
3. **ALWAYS** version your API (e.g., /api/v1/...)
4. **NEVER** mix business logic with route definitions

## Development

### API Design Patterns

1. **Route Organization**
   - **ALWAYS** use APIRouter to organize routes by feature/resource
   - **ALWAYS** prefix routers with appropriate path segments
   - **ALWAYS** tag routes for clean OpenAPI documentation
   - **NEVER** create routes outside of dedicated router modules

2. **Path Operations**
   - **ALWAYS** use appropriate HTTP methods (GET, POST, PUT, DELETE, etc.)
   - **ALWAYS** use plural nouns for collection resources (e.g., /users, /items)
   - **ALWAYS** include status codes in responses using status_code parameter
   - **NEVER** use verbs in path segments for standard CRUD operations

3. **Query Parameters**
   - **ALWAYS** provide default values when appropriate
   - **ALWAYS** document parameters with description
   - **ALWAYS** validate query parameters with appropriate types and constraints
   - **NEVER** use query parameters for sensitive data

### Data Validation and Models

1. **Pydantic Models**
   - **ALWAYS** create separate models for requests and responses
   - **ALWAYS** use nested models for complex data structures
   - **ALWAYS** add proper field descriptions and examples in model definitions
   - **NEVER** expose internal models directly to API consumers

2. **Validation Rules**
   - **ALWAYS** use Pydantic validators for complex validation rules
   - **ALWAYS** use appropriate field constraints (min_length, regex, etc.)
   - **ALWAYS** provide helpful error messages in validators
   - **NEVER** trust client input without validation

### Dependency Injection

1. **Best Practices**
   - **ALWAYS** use FastAPI's Depends for dependency injection
   - **ALWAYS** create reusable dependencies for common operations
   - **ALWAYS** use yield dependencies for resources that need cleanup
   - **NEVER** use global variables instead of dependencies

2. **Common Dependencies**
   - **ALWAYS** create database session dependencies
   - **ALWAYS** create current user dependencies for authentication
   - **ALWAYS** use dependencies for permission checking
   - **NEVER** duplicate dependency logic across route functions

### Security

1. **Authentication**
   - **ALWAYS** use OAuth2 with secure password hashing
   - **ALWAYS** implement proper token validation
   - **ALWAYS** use HTTPS in production
   - **NEVER** store secrets in code

2. **Authorization**
   - **ALWAYS** implement permission checking for protected resources
   - **ALWAYS** use scopes for granular access control
   - **ALWAYS** verify ownership/access rights before operations
   - **NEVER** rely solely on hiding endpoints for security

3. **Data Protection**
   - **ALWAYS** protect against SQL injection using ORM
   - **ALWAYS** protect against XSS by validating and sanitizing inputs
   - **ALWAYS** implement rate limiting for public endpoints
   - **NEVER** return sensitive information in responses

## Performance Optimization

1. **Database Operations**
   - **ALWAYS** use async database operations with proper connection pooling
   - **ALWAYS** select only needed fields from database
   - **ALWAYS** use pagination for list endpoints
   - **NEVER** perform N+1 queries (use joins or .options(selectinload()))

2. **Caching**
   - **ALWAYS** implement caching for expensive operations
   - **ALWAYS** use appropriate cache TTL based on data volatility
   - **ALWAYS** implement cache invalidation when data changes
   - **NEVER** cache sensitive user-specific data

3. **Async Operations**
   - **ALWAYS** use async/await for I/O operations
   - **ALWAYS** use BackgroundTasks for non-critical operations
   - **ALWAYS** handle long-running tasks with background workers
   - **NEVER** block the event loop with CPU-intensive operations

## Testing

1. **Test Organization**
   - **ALWAYS** organize tests by endpoints/features
   - **ALWAYS** separate unit, integration, and end-to-end tests
   - **ALWAYS** use pytest fixtures for test dependencies
   - **NEVER** test third-party functionality

2. **Test Client**
   - **ALWAYS** use FastAPI's TestClient for API testing
   - **ALWAYS** test both success and error cases
   - **ALWAYS** test with different parameters and edge cases
   - **NEVER** use production databases for testing

3. **Mocking**
   - **ALWAYS** mock external services in unit tests
   - **ALWAYS** use dependency overrides for testing
   - **ALWAYS** create test utilities for common test operations
   - **NEVER** depend on external services in unit tests

## Deployment

1. **Configuration**
   - **ALWAYS** use Pydantic's BaseSettings for configuration
   - **ALWAYS** load configuration from environment variables
   - **ALWAYS** provide default values for development
   - **NEVER** hardcode environment-specific values

2. **Docker Deployment**
   - **ALWAYS** use multi-stage builds for smaller images
   - **ALWAYS** use a non-root user in containers
   - **ALWAYS** set appropriate health checks
   - **NEVER** include development dependencies in production image

3. **Monitoring**
   - **ALWAYS** implement logging with proper log levels
   - **ALWAYS** add request ID to logs for traceability
   - **ALWAYS** use structured logging (JSON)
   - **NEVER** log sensitive information

## Common Anti-patterns to Avoid

1. **NEVER** put too much logic in path operation functions
2. **NEVER** use global variables for stateful operations
3. **NEVER** ignore the advantages of async (use it correctly)
4. **NEVER** use raw SQL queries without proper escaping
5. **NEVER** expose exception details to clients in production

## Resources

- [FastAPI Official Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://pydantic-docs.helpmanual.io/)
- [Starlette Documentation](https://www.starlette.io/)