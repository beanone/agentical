# React Development Guidelines

## Overview

These guidelines provide best practices for developing React applications, focusing on code quality, performance, and maintainability.

## Architecture

### Project Structure

```
src/
├── components/      # Reusable UI components
│   ├── common/      # Truly reusable across the entire application
│   ├── features/    # Components specific to features
│   └── layouts/     # Layout components like headers, footers, etc.
├── hooks/           # Custom React hooks
├── pages/           # Route components (for React Router)
├── services/        # API calls and external service interactions
├── store/           # State management (Redux, Zustand, etc.)
├── styles/          # Global styles and themes
├── types/           # TypeScript type definitions
└── utils/           # Utility functions
```

### Component Organization

1. **ALWAYS** organize components by feature or domain when possible
2. **ALWAYS** separate presentational components from container components
3. **ALWAYS** create small, focused components rather than large, monolithic ones
4. **NEVER** include business logic in presentational components

## Development

### Component Patterns

1. **Functional Components**
   - **ALWAYS** prefer functional components with hooks over class components
   - **ALWAYS** use named exports for components: `export const MyComponent = () => {...}`
   - **ALWAYS** destructure props: `const MyComponent = ({ title, children }) => {...}`

2. **Hooks Usage**
   - **ALWAYS** follow the Rules of Hooks (only call at top level, only call from React functions)
   - **ALWAYS** use custom hooks to reuse stateful logic
   - **ALWAYS** name custom hooks starting with "use": `useCustomHook`
   - **NEVER** use hooks conditionally without extracting to a separate component

3. **State Management**
   - **ALWAYS** use local state (useState) for component-specific state
   - **ALWAYS** use context (useContext) for state shared across nearby components
   - **ALWAYS** use a state management library (Redux, Zustand, etc.) for global application state
   - **NEVER** lift state higher than necessary (avoid prop drilling by using context instead)

### Performance Optimization

1. **Preventing Unnecessary Renders**
   - **ALWAYS** use React.memo for presentational components with expensive renders
   - **ALWAYS** use useCallback for event handlers passed as props
   - **ALWAYS** use useMemo for expensive calculations
   - **NEVER** use deep objects or arrays as dependencies without proper memoization

2. **Code Splitting**
   - **ALWAYS** use dynamic imports for route-based code splitting
   - **ALWAYS** use React.lazy and Suspense for component-based code splitting
   - **NEVER** load all features upfront if they're not needed on the initial render

### Styling

1. **CSS Organization**
   - **ALWAYS** use a consistent styling approach (CSS modules, styled-components, emotion, etc.)
   - **ALWAYS** keep styles colocated with components
   - **NEVER** use inline styles except for dynamically computed values

2. **When using CSS-in-JS**
   - **ALWAYS** define styled components outside of the render function
   - **ALWAYS** use theme tokens for consistent styling
   - **NEVER** hardcode colors, spacing, or other design values

### TypeScript Best Practices

1. **Type Definitions**
   - **ALWAYS** define prop types using interfaces
   - **ALWAYS** provide descriptive names for types and interfaces
   - **NEVER** use `any` type unless absolutely necessary
   - **ALWAYS** use discriminated unions for complex state

2. **Props Typing**
   - **ALWAYS** make props required by default, optional only when necessary
   - **ALWAYS** use children prop correctly: `{ children: React.ReactNode }`
   - **ALWAYS** provide default props for optional props

## Testing

1. **Component Testing**
   - **ALWAYS** test components in isolation using React Testing Library
   - **ALWAYS** test user interactions, not implementation details
   - **ALWAYS** use role-based selectors rather than test IDs when possible
   - **NEVER** test library code (e.g., Redux internals)

2. **Test Coverage**
   - **ALWAYS** test all user-visible functionality
   - **ALWAYS** test edge cases and error states
   - **ALWAYS** test all conditional rendering paths

## Deployment

1. **Build Optimization**
   - **ALWAYS** analyze bundle size before production deployment
   - **ALWAYS** use tree-shaking compatible import syntax
   - **NEVER** import entire libraries when only specific functions are needed

2. **Environment Configuration**
   - **ALWAYS** use environment variables for configuration
   - **NEVER** include sensitive information in client-side code
   - **ALWAYS** validate environment configuration at build time

## Common Anti-patterns to Avoid

1. **NEVER** use setState in useEffect without cleanup or dependencies
2. **NEVER** create functions inside the render that are passed down to children
3. **NEVER** use index as a key for lists when items can be reordered
4. **NEVER** use multiple state hooks when a single object would be clearer
5. **NEVER** mutate props or state directly

## Resources

- [React Official Documentation](https://reactjs.org/docs/getting-started.html)
- [React TypeScript Cheatsheet](https://react-typescript-cheatsheet.netlify.app/)
- [Kent C. Dodds Blog](https://kentcdodds.com/blog) - Excellent React patterns and testing practices