# Assistant Rules

This section contains rules governing AI assistant behavior and interactions within the Agentic Framework project.

## Categories

1. Communication Standards
   - [AST-001: Response Format](communication/format.md)
   - [AST-002: Error Handling](communication/errors.md)
   - [AST-003: Clarification Requests](communication/clarification.md)

2. Tool Usage
   - [AST-101: Tool Selection](tools/selection.md)
   - [AST-102: Tool Parameters](tools/parameters.md)
   - [AST-103: Tool Results](tools/results.md)

3. Code Interaction
   - [AST-201: Code Reading](code/reading.md)
   - [AST-202: Code Generation](code/generation.md)
   - [AST-203: Code Modification](code/modification.md)

4. Problem Solving
   - [AST-301: Problem Analysis](solving/analysis.md)
   - [AST-302: Solution Design](solving/design.md)
   - [AST-303: Implementation Strategy](solving/implementation.md)

## Rule Format

Each rule in this section follows the standard format:

```markdown
# Rule AST-[Number]: [Title]

## Description
What the assistant must do or avoid

## Rationale
Why this behavior is important

## Examples
Good and bad interaction examples

## Related Rules
Links to related assistant rules
```

## Implementation

These rules are implemented through:
1. System prompts
2. Custom instructions
3. Tool-specific guidelines
4. Response templates 