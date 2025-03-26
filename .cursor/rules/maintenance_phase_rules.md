# Maintenance Phase Rules

## 1. Breaking Changes Management

- Document all breaking changes thoroughly in an upgrade guide
- Obtain explicit approval before implementing breaking changes
- Consider versioning for APIs and interfaces that might change
- Implement deprecation warnings before removing functionality
- Provide migration tools or scripts when possible

## 2. Incremental Refactoring

- Make small, focused changes rather than massive rewrites
- Commit changes frequently with descriptive messages
- Maintain a working state throughout the refactoring process
- Isolate refactoring changes from feature changes in separate commits
- Create a clear rollback path for each significant change
- Test after each atomic change

## 3. Performance Preservation

- Benchmark critical paths before and after changes
- Be conscious of memory usage changes
- Watch for increased I/O or network operations
- Don't sacrifice performance for minor readability gains in critical sections
- Profile the application to ensure no regressions in important operations
- Add performance regression tests

## 4. Contract Preservation

- **NEVER** break existing contracts (APIs, interfaces, function signatures, config formats) without explicit approval
- A contract is any interface that other code depends on - changing it breaks dependent code
- Honor semantic contracts too: maintain identical behavior even when implementation changes
- When contract changes are unavoidable, version the interface or provide adapter layers

## 5. Dependency Management

- Avoid introducing unnecessary dependencies
- Consider the impact of new dependencies on the deployment environment
- Document all required dependencies for each component
- Get approval for introducing new external dependencies
- Be cautious when updating dependency versions

## 6. Documentation Updates

- Keep documentation in sync with code changes
- Update READMEs, API docs, and other documentation
- Document known issues and their workarounds
- Maintain a changelog of significant changes
- Document configuration changes and their impacts

## Maintenance Phase Focus Tips

- Make minimal changes to fix issues
- Focus on backward compatibility
- Ensure thorough regression testing
- Document changes for other maintainers
- Be particularly careful with changes to shared/core components
- Avoid the temptation to rewrite "ugly" code that works correctly 