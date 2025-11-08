# Contributing to Promote Autonomy
Thank you for your interest in contributing! This document explains how to contribute effectively and safely to the Promote Autonomy codebase.

---

## Code of Conduct
All contributors must follow a respectful and collaborative communication style.

---

## How to Contribute
### 1. Fork the repository
```bash
git clone https://github.com/your-org/promote-autonomy.git
```

### 2. Create a feature branch
```bash
git checkout -b feature/my-change
```

### 3. Make your changes
- Follow existing directory structure
- Keep changes minimal and atomic
- Write clear and expressive code
- Update documentation when necessary

### 4. Run local tests (if applicable)
TBD: Testing suite will be added as project matures.

### 5. Submit a Pull Request
Your PR should include:
- A clear description of the change
- Screenshots or logs (if UI or behavior changes)
- References to related issues

A maintainer will review and provide feedback.

---

## Coding Standards
### Python (Strategy & Creative Agents)
- Use `ruff` for linting and `black` for formatting
- Follow Pydantic models for structured data
- Keep functions pure when possible

### TypeScript (Frontend)
- Follow strict TypeScript rules
- Use React hooks properly
- Keep UI components small and stateless when possible

### Cloud Architecture
- No business logic in Cloud Functions (if used)
- Each Cloud Run service must remain single-responsibility
- Avoid circular dependencies across services

---

## Commit Message Guidelines
Follow conventional commits:
```
feat: add approval button
fix: correct Firestore state transition
docs: update README
```

---

## Pull Request Review Process
1. Initial automated checks (formatting, linting)
2. Human review focusing on:
   - Correctness
   - System boundaries
   - Security (auth, Firestore rules, identity)
   - Performance considerations
3. Merge when approved

---

## Feature Requests & Issues
Use GitHub Issues for:
- Bugs
- Feature proposals
- Architecture discussions

Tag appropriately:
- `bug`
- `enhancement`
- `architecture`
- `good first issue`
