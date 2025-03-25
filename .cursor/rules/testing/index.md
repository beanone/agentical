# Testing Rules

This section contains rules for testing practices within the Agentic Framework project.

## Categories

1. Unit Testing
   - [TEST-001: Test Coverage](unit/coverage.md)
   - [TEST-002: Test Structure](unit/structure.md)
   - [TEST-003: Test Naming](unit/naming.md)

2. Integration Testing
   - [TEST-101: API Testing](integration/api.md)
   - [TEST-102: Tool Testing](integration/tools.md)
   - [TEST-103: System Testing](integration/system.md)

3. Performance Testing
   - [TEST-201: Load Tests](performance/load.md)
   - [TEST-202: Benchmarks](performance/benchmarks.md)
   - [TEST-203: Profiling](performance/profiling.md)

4. Test Infrastructure
   - [TEST-301: CI Integration](infrastructure/ci.md)
   - [TEST-302: Test Data](infrastructure/data.md)
   - [TEST-303: Test Environment](infrastructure/environment.md)

## Rule Format

Each rule in this section follows the standard format:

```markdown
# Rule TEST-[Number]: [Title]

## Description
What testing practices must be followed

## Rationale
Why this testing standard is important

## Examples
Good and bad test examples

## Related Rules
Links to related test rules
```

## Implementation

These rules are enforced through:
1. pytest configuration
2. Coverage requirements
3. CI/CD pipelines
4. Code review checklist
5. Test templates and fixtures 