# Project: RC-PADDLEOCR-V2

## Core Philosophy
- Always prioritize **clarity, simplicity, and readability** in code.  
- Follow the **Zen of Python** and general engineering axioms (KISS, DRY, YAGNI).  
- Treat code as a communication medium for humans first, machines second.  

## General Software Engineering Principles
1. **KISS (Keep It Simple, Stupid)**  
   - Prefer straightforward solutions over complex abstractions.  
   - Avoid unnecessary cleverness.  

2. **DRY (Don’t Repeat Yourself)**  
   - Eliminate duplication by modularizing and reusing code.  
   - Centralize logic to reduce maintenance overhead.  

3. **YAGNI (You Aren’t Gonna Need It)**  
   - Do not implement speculative features.  
   - Build only what is required by current needs.  

4. **Separation of Concerns**  
   - Isolate responsibilities across modules, layers, and services.  
   - Ensure each component has a clear, singular purpose.  

5. **SOLID Principles (Object-Oriented Design)**  
   - *Single Responsibility*: One reason to change per class/module.  
   - *Open/Closed*: Extend without modifying existing code.  
   - *Liskov Substitution*: Subtypes must be substitutable for base types.  
   - *Interface Segregation*: Avoid bloated interfaces.  
   - *Dependency Inversion*: Depend on abstractions, not concrete implementations.  

6. **Principle of Least Astonishment**  
   - Code should behave in ways that are intuitive and unsurprising.  

7. **Law of Demeter (Least Knowledge)**  
   - Minimize deep dependency chains; interact only with immediate collaborators.  

8. **Avoid Premature Optimization**  
   - Prioritize correctness and clarity before performance tuning.  
   - Optimize only when bottlenecks are measured and proven.  

---

## Lifecycle & Process Principles
- **Requirements First**: Validate and clarify requirements before coding.  
- **Test Early, Test Often**: Integrate unit, integration, and automated tests.  
- **Maintainability**: Write self-documenting code with consistent style.  
- **Continuous Improvement**: Refactor regularly and adopt evolving best practices.  
- **Documentation & Communication**: Ensure code is supported by clear docstrings, comments, and design notes.  

---

## Enforcement Directives
- Reject code that violates readability, clarity, or maintainability.  
- Prefer idiomatic constructs and standard libraries over reinvented solutions.  
- Always explain design choices with reference to these principles.  
- When multiple solutions exist, select the one that is **simplest, most maintainable, and least surprising**.  

---