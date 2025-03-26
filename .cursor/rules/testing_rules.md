# Testing Rules

## 1. Test Coverage

- Aim for high test coverage of code, but focus on coverage of functionality
- Test edge cases and boundary conditions
- Include negative testing (invalid inputs, error conditions)
- Test both happy paths and failure scenarios
- Ensure all critical paths have thorough test coverage

## 2. Test Organization

- Structure tests logically to match application organization
- Use descriptive test names that indicate what is being tested
- Group related tests together
- Separate unit tests from integration and system tests
- Follow a consistent naming convention for test files and functions

## 3. Test Independence

- Each test should be independent and self-contained
- Tests should not depend on the order of execution
- Avoid test interdependencies
- Reset the test state between test runs
- Mock external dependencies to ensure test isolation

## 4. Test Quality

- Tests should be deterministic (same result every time)
- Avoid flaky tests that pass/fail inconsistently
- Keep tests simple and readable
- Tests should run quickly to enable frequent execution
- One assertion per test is ideal (or testing one logical concept)

## 5. Test Maintenance

- Treat test code with the same care as production code
- Refactor tests when they become difficult to maintain
- Avoid duplicated test code using appropriate abstractions
- Keep test fixtures and helpers up to date
- Delete tests that no longer serve a purpose

## 6. Regression Testing

- Automate regression tests wherever possible
- Create tests for all reported bugs to prevent recurrence
- Run regression tests before each release
- Prioritize tests based on risk and importance
- Include visual regression tests for UI components

## 7. Non-Functional Testing

- Test performance under expected and peak loads
- Test security aspects including authentication and authorization
- Validate accessibility compliance
- Test internationalization and localization
- Test compatibility with supported browsers/devices/platforms

## 8. Bottom-Up Testing Approach

- **ALWAYS** test components from the bottom of the dependency hierarchy upward
- Start with components that have the least dependencies on other parts of the system
- Only test a component after its dependencies have been tested
- Benefits of this approach:
  - Easier to isolate and fix issues at their source
  - Builds confidence in foundational components first
  - Reduces debugging complexity when tests fail
  - Makes mocking more straightforward as dependencies are already tested
  - Follows the natural dependency flow of the system

### Example Dependency Order:
```
Layer 3 (Integration Tests)
└── Layer 2 (Providers Factory)
    └── Layer 1 (Individual Providers)
        └── Layer 0 (Core Types/Utils)
```

### Implementation Steps:
1. Identify the dependency hierarchy in your system
2. Start testing at the lowest level (Layer 0)
3. Only move up to testing a component when all its dependencies are tested
4. Use already-tested components as trusted building blocks

### Benefits in Practice:
- When a test fails, you can trust the underlying components
- Mocks can be based on tested behavior of dependencies
- Easier to maintain as changes to lower layers highlight needed updates in higher layers

## Testing Phase Focus Tips

- Write tests before or alongside code (TDD/BDD) when appropriate
- Automate tests within CI/CD pipelines
- Use appropriate testing frameworks for different test types
- Review test reports and address failures promptly
- Consider mutation testing to validate test effectiveness
- Document the test strategy and approach for the project 