# Performance Optimization Rules

## 1. Measure First

- Always benchmark before optimizing to establish a baseline
- Identify actual bottlenecks through profiling, not assumptions
- Set clear performance goals and success criteria
- Use appropriate profiling tools for your language/platform
- Measure both average and worst-case performance

## 2. Dynamic Loading

- Keep imports inside methods when implementing dynamic loading pattern
- Only load dependencies when actually needed (lazy loading)
- Defer initialization of expensive resources until required
- Consider asynchronous loading for non-critical components
- Use caching for frequently accessed resources

## 3. Performance Preservation

- Benchmark critical paths before and after optimization
- Be conscious of memory usage changes
- Watch for increased I/O or network operations
- Make targeted improvements with measurable results
- Document performance trade-offs made during optimization
- Add performance regression tests

## 4. Algorithm Efficiency

- Choose appropriate algorithms and data structures for the task
- Consider time and space complexity for operations on large datasets
- Look for redundant computations that can be eliminated
- Use appropriate caching strategies for expensive operations
- Consider batch processing where applicable

## 5. Resource Management

- Minimize resource contention (locks, shared resources)
- Use connection pooling for database and network connections
- Release resources promptly when no longer needed
- Consider resource lifecycle management (open/close)
- Implement proper error handling to prevent resource leaks

## 6. Database Optimization

- Optimize database queries and schema for performance
- Use proper indexing strategies
- Consider query plan analysis
- Implement appropriate caching layers
- Use database-specific performance features appropriately

## 7. Code-Level Optimizations

- Optimize hot code paths identified through profiling
- Avoid premature micro-optimizations
- Consider language-specific optimizations where appropriate
- Remove unnecessary object creation in critical loops
- Use appropriate concurrency patterns for parallelizable work

## Performance Optimization Focus Tips

- Profile before optimizing to identify actual bottlenecks
- Optimize the slowest parts first - follow the 80/20 rule
- Document the before/after metrics for each optimization
- Maintain readability unless the performance gain is significant
- Consider the maintenance cost of complex optimizations
- Test thoroughly to ensure optimizations don't introduce bugs 