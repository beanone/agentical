# RESTful API Design Guidelines

## Overview

These guidelines provide best practices for designing RESTful APIs that are intuitive, consistent, and follow industry standards. A well-designed API improves developer experience, increases adoption, and reduces integration issues.

## Resource Design

### Resource Naming

1. **Resources**
   - **ALWAYS** use plural nouns for collection resources (e.g., `/users`, `/orders`)
   - **ALWAYS** use concrete, domain-specific names rather than generic terms
   - **ALWAYS** use lowercase letters and hyphens for multi-word resources (`order-items` not `orderItems` or `order_items`)
   - **NEVER** use verbs in resource names for standard CRUD operations

2. **Hierarchical Relationships**
   - **ALWAYS** use nested resources to represent hierarchical relationships (e.g., `/users/{id}/orders`)
   - **ALWAYS** limit nesting to one level deep to avoid overly complex URLs
   - **ALWAYS** provide direct access to nested resources when appropriate (e.g., `/orders/{id}` alongside `/users/{id}/orders/{id}`)
   - **NEVER** create deeply nested hierarchies (more than 2 levels)

3. **Non-Resource Operations**
   - **ALWAYS** use verbs for non-resource operations (e.g., `/users/{id}/reset-password`)
   - **ALWAYS** place these operations at the end of the resource path
   - **NEVER** use non-resource operations when a standard CRUD operation would suffice

## HTTP Methods

1. **Method Usage**
   - **ALWAYS** use `GET` for retrieving resources
   - **ALWAYS** use `POST` for creating resources
   - **ALWAYS** use `PUT` for full updates (replacing entire resources)
   - **ALWAYS** use `PATCH` for partial updates
   - **ALWAYS** use `DELETE` for removing resources
   - **NEVER** use `GET` for operations that change state

2. **Idempotency**
   - **ALWAYS** make `GET`, `PUT`, `DELETE`, and `HEAD` idempotent
   - **ALWAYS** make `POST` non-idempotent (each call creates a new resource)
   - **ALWAYS** make `PATCH` idempotent when possible
   - **NEVER** have side effects in idempotent operations

## Query Parameters

1. **Filtering, Sorting, and Pagination**
   - **ALWAYS** use query parameters for filtering (e.g., `/users?status=active`)
   - **ALWAYS** use query parameters for sorting (e.g., `/users?sort=name:asc,created:desc`)
   - **ALWAYS** use query parameters for pagination (e.g., `/users?page=2&page_size=10` or `/users?offset=20&limit=10`)
   - **NEVER** use query parameters to modify resource state

2. **Search**
   - **ALWAYS** use a dedicated `search` or `q` parameter for searching (e.g., `/users?search=john`)
   - **ALWAYS** document search capabilities including supported fields and operators
   - **NEVER** mix search with other filtering parameters when they have different semantics

3. **Field Selection**
   - **ALWAYS** support field selection to limit response size (e.g., `/users?fields=id,name,email`)
   - **ALWAYS** have a reasonable default field set when not specified
   - **NEVER** require clients to specify fields

## HTTP Status Codes

1. **Success Codes**
   - **ALWAYS** use `200 OK` for successful `GET`, `PATCH`, and `PUT` requests
   - **ALWAYS** use `201 Created` for successful `POST` requests that create resources
   - **ALWAYS** use `204 No Content` for successful `DELETE` requests and operations that return no content
   - **NEVER** use `200 OK` when a more specific success code is appropriate

2. **Client Error Codes**
   - **ALWAYS** use `400 Bad Request` for invalid input
   - **ALWAYS** use `401 Unauthorized` for missing or invalid authentication
   - **ALWAYS** use `403 Forbidden` for authorization failures
   - **ALWAYS** use `404 Not Found` for non-existent resources
   - **ALWAYS** use `422 Unprocessable Entity` for validation errors
   - **NEVER** return `200 OK` for client errors

3. **Server Error Codes**
   - **ALWAYS** use `500 Internal Server Error` for unhandled exceptions
   - **ALWAYS** use `503 Service Unavailable` when the service is temporarily unavailable
   - **NEVER** expose sensitive details in server error responses

## Request and Response Bodies

1. **JSON Format**
   - **ALWAYS** use JSON as the primary data format
   - **ALWAYS** use camelCase for property names in JSON
   - **ALWAYS** use consistent property naming conventions
   - **NEVER** use different naming conventions in requests and responses for the same concepts

2. **Resource Representations**
   - **ALWAYS** include a unique identifier (`id`) for resources
   - **ALWAYS** use ISO 8601 format for dates and times (UTC) (`YYYY-MM-DDTHH:MM:SSZ`)
   - **ALWAYS** include hypermedia links (HATEOAS) when resources are related
   - **NEVER** include sensitive information in responses

3. **Error Responses**
   - **ALWAYS** provide a standardized error response format, including:
     - `error`: A short, descriptive error code
     - `message`: A human-readable error message
     - `details`: (Optional) Detailed error information
   - **ALWAYS** provide field-specific validation errors when applicable
   - **NEVER** include stack traces or implementation details in error responses

## Versioning

1. **API Versioning**
   - **ALWAYS** version your API from the beginning
   - **ALWAYS** use URL path versioning for major versions (e.g., `/api/v1/users`)
   - **ALWAYS** maintain backward compatibility within the same major version
   - **NEVER** change the meaning of existing endpoints in the same version

2. **Version Transitions**
   - **ALWAYS** support at least one previous version when releasing a new one
   - **ALWAYS** provide clear documentation for migrating between versions
   - **ALWAYS** set and communicate deprecation timelines
   - **NEVER** abruptly deprecate APIs without warning

## Security

1. **Authentication**
   - **ALWAYS** use OAuth 2.0 or JWT for authentication
   - **ALWAYS** transmit credentials via HTTPS
   - **ALWAYS** require HTTPS for all endpoints
   - **NEVER** accept credentials or sensitive data in URL parameters

2. **Authorization**
   - **ALWAYS** implement authorization checks for protected resources
   - **ALWAYS** follow the principle of least privilege
   - **ALWAYS** use fine-grained permissions when appropriate
   - **NEVER** rely on security through obscurity

3. **Rate Limiting**
   - **ALWAYS** implement rate limiting for APIs
   - **ALWAYS** include rate limit information in headers:
     - `X-RateLimit-Limit`: Total allowed requests
     - `X-RateLimit-Remaining`: Remaining requests
     - `X-RateLimit-Reset`: Time when the limit resets
   - **ALWAYS** return `429 Too Many Requests` when limits are exceeded
   - **NEVER** apply rate limits without informing the client

## Documentation

1. **API Documentation**
   - **ALWAYS** document all endpoints, parameters, and responses
   - **ALWAYS** provide examples for requests and responses
   - **ALWAYS** use OpenAPI (Swagger) or similar tools for API specifications
   - **ALWAYS** keep documentation synchronized with implementation
   - **NEVER** leave endpoints undocumented

2. **Changelog**
   - **ALWAYS** maintain a changelog for API changes
   - **ALWAYS** document breaking changes prominently
   - **ALWAYS** provide migration guides for significant changes
   - **NEVER** make breaking changes without documentation

## Common Anti-patterns to Avoid

1. **NEVER** use `GET` requests with request bodies
2. **NEVER** use generic resource names (`/entity`, `/resource`, `/item`)
3. **NEVER** use different naming conventions in different parts of your API
4. **NEVER** return different data structures for the same resource in different endpoints
5. **NEVER** implement RPC-style endpoints mixed with RESTful endpoints (e.g., `/api/getUserData`)
6. **NEVER** handle multiple unrelated resources in a single endpoint

## Resources

- [REST API Tutorial](https://restfulapi.net/)
- [Microsoft REST API Guidelines](https://github.com/microsoft/api-guidelines/blob/vNext/Guidelines.md)
- [Zalando RESTful API Guidelines](https://opensource.zalando.com/restful-api-guidelines/)
- [Google API Design Guide](https://cloud.google.com/apis/design)