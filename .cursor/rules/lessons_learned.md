# Lessons Learned from Past Mistakes

This document serves as a living record of mistakes made and lessons learned. By documenting these experiences, we create a valuable resource for avoiding similar issues in the future. This file should be reviewed periodically and used to update our development rules when necessary.

## Data Preservation

**Mistake:** Accidentally deleted an entire project without confirmation or backup verification.

**Impact:** Caused significant loss of work that required restoration from backup, disrupting development timelines and potentially losing recent changes.

**Lessons Learned:**
- Never delete or significantly modify files without explicit user confirmation
- Follow a staged approach for destructive operations (describe → confirm → execute)
- Verify backup existence before performing potentially destructive operations
- Use clear, explicit questions when confirming user intent for dangerous operations
- Never assume destructive intent from ambiguous instructions
- Consider non-destructive alternatives before suggesting file deletion or overwriting

## Interface Changes

**Mistake:** Changed environment variable names (`DEEPSEEK_API_KEY` to `DS_API_KEY`) during adapter refactoring.

**Impact:** Broke compatibility with existing configurations and deployments.

**Lessons Learned:**
- Never change interface elements (including environment variable names) without explicit approval
- Consider all consumers of an interface before making changes
- Provide backwards compatibility mechanisms when interfaces must change

## Cleanup Discipline

**Mistake:** Failed to properly clean up temporary changes and ensure the codebase was left in a clean state.

**Impact:** Left the codebase with potential technical debt, confusion for other developers, and possible runtime issues.

**Lessons Learned:**
- Always verify that all temporary changes are removed
- Check that the final state works properly with all test/debug code removed
- Review changes holistically before considering work complete
- Create a cleanup checklist for complex changes

## Dependency Management

**Mistake:** During refactoring, broke implicit dependencies between modules by changing how adapters were loaded.

**Impact:** System failed to start due to missing dependencies.

**Lessons Learned:**
- Map out all dependencies (both explicit and implicit) before refactoring
- Test after each significant change, not just at the end
- Consider how modules interact as a whole, not just in isolation
- Implement proper error handling for dependencies that might not be available

## Scope Control

**Mistake:** Expanded the scope of a refactoring task beyond the original requirements.

**Impact:** Introduced unnecessary risks and complications to what should have been a focused change.

**Lessons Learned:**
- Clearly define and stick to the scope of a task
- Make minimal changes required to meet the objective
- Separate refactoring from feature changes
- Get approval for scope expansion when necessary

## Meta-Learning: Rules Management

**Mistake:** Creating overly specific rules tied directly to concrete incidents rather than abstracting to broadly applicable principles, and adding new rules without refining existing ones.

**Impact:** 
- Reduced the value of lessons learned, as they only help prevent exact recurrences rather than addressing entire classes of similar issues
- Rule bloat leading to confusion, redundancy, and decreased adherence
- Contradictions between rules developed at different times

**Lessons Learned:**
- Abstract specific incidents into general principles
- Focus on the underlying pattern rather than the specific manifestation
- Ask "what category of mistake is this?" rather than just "what specific mistake was made?"
- Test the abstraction by seeing if it would prevent similar but different mistakes
- Ensure rules are broad enough to be widely applicable but specific enough to provide clear guidance
- Consolidate related rules rather than creating numerous similar ones
- Update existing rules instead of adding new ones when they address the same concern
- Periodically review all rules for relevance, clarity, and consistency
- Remove or archive outdated rules that no longer apply
- Maintain a reasonable number of rules to prevent cognitive overload

---

*This document should be periodically reviewed and updated with new lessons. When patterns emerge, consider updating the corresponding rules files with new or modified rules.* 