# Design Phase Rules

## 1. Contract Preservation

- **NEVER** break existing contracts (APIs, interfaces, function signatures, config formats) without explicit approval
- A contract is any interface that other code depends on - changing it breaks dependent code
- Honor semantic contracts too: maintain identical behavior even when implementation changes
- When contract changes are unavoidable, version the interface or provide adapter layers

## 2. Dependency Chain Awareness

- Identify all code that depends on refactored components
- Update all dependent code when making interface changes
- Consider the ripple effects of changes through the application
- Test the entire dependency chain, not just the refactored component

## 3. Separation of Concerns

- Keep business logic separate from infrastructure code
- Decouple components to minimize interdependencies
- Use appropriate design patterns to manage complex interactions
- Ensure each component has a single, well-defined responsibility
- Isolate side effects into clearly marked functions/modules

## 4. Critical Thinking

- Never be a "yes-person" who blindly implements requested changes
- Question assumptions and requirements that may lead to problematic design
- Propose better alternatives when the requested approach has clear drawbacks
- Consider long-term maintenance implications, not just immediate solutions
- Respectfully push back on requests that would violate good engineering practices
- Think through edge cases and potential failure modes before implementing

## 5. Configuration Management

- Centralize configuration rather than scattering it throughout the code
- Use environment variables for deployment-specific values
- Make configuration changes backward compatible
- Provide clear documentation for all configuration options
- Supply sensible defaults to minimize required configuration

## Design Phase Focus Tips

- Document architectural decisions and their rationale (use ADRs)
- Create clear interface definitions before implementation details
- Focus on system boundaries and component interactions
- Consider extensibility and long-term maintainability
- Establish error handling and logging strategy early
- Define security requirements and controls at the architecture level 