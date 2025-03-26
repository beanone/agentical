# Security Rules

## 1. Authentication & Authorization

- Implement strong authentication mechanisms
- Use multi-factor authentication for sensitive systems
- Enforce principle of least privilege
- Implement role-based access control
- Regularly audit user permissions and access rights
- **NEVER** store passwords in plaintext

## 2. Data Protection

- Encrypt sensitive data at rest and in transit
- Implement proper key management
- Sanitize data before storing or processing
- Implement data retention and deletion policies
- Classify data by sensitivity and apply appropriate controls
- Consider data residency and sovereignty requirements

## 3. Input Validation

- Validate all user input on the server side
- Use parameterized queries to prevent SQL injection
- Implement content security policies
- Sanitize output to prevent XSS attacks
- Validate file uploads (type, size, content)

## 4. API Security

- Use API keys or tokens for authentication
- Implement rate limiting to prevent abuse
- Validate request parameters and payloads
- Use HTTPS for all API endpoints
- Document security requirements for API consumers

## 5. Dependency Management

- Regularly scan for vulnerabilities in dependencies
- Keep dependencies updated
- Remove unused dependencies
- Verify the integrity of dependencies
- Maintain an inventory of third-party components

## 6. Secure Configuration

- Remove default credentials
- Disable unnecessary features and services
- Use secure default settings
- Implement proper error handling that doesn't leak sensitive information
- Regularly review and update security configurations

## 7. Logging & Monitoring

- Log security-relevant events
- Protect log data from unauthorized access
- Implement real-time monitoring for security events
- Set up alerts for suspicious activities
- Ensure logs contain sufficient context without sensitive data

## 8. Secure Development Practices

- Conduct security code reviews
- Include security testing in CI/CD pipelines
- Perform regular penetration testing
- Train developers on secure coding practices
- Implement a security incident response plan

## 9. Container & Cloud Security

- Scan container images for vulnerabilities
- Use minimal base images
- Implement network segmentation in cloud environments
- Apply the principle of least privilege to cloud resources
- Encrypt data in cloud storage

## 10. Defense in Depth

- Implement multiple layers of security controls
- Don't rely on a single security measure
- Consider insider threat scenarios
- Plan for security control failures
- Regularly test security controls

## Security Best Practices

- Stay informed about security vulnerabilities and trends
- Cultivate a security-focused culture in the team
- Document security decisions and trade-offs
- Conduct regular security assessments
- Consider security from the beginning of the project, not as an afterthought
- Balance security controls with usability 