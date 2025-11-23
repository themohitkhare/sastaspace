---
description: "Conduct a security audit using Brakeman and manual review patterns."
globs: []
---

# Security Audit

Perform a security review of the codebase.

## 1. Automated Scan
Run Brakeman to find known vulnerabilities:
```bash
bundle exec brakeman
```
*   **Action**: Fix any high/medium confidence warnings immediately.

## 2. Manual Review Checklist

### Authentication & Authorization
- [ ] **Scopes**: Are we using `current_user.resources` instead of `Resource.find(params[:id])`?
- [ ] **Bypass**: Are there any `skip_before_action :authenticate_user!` that are too broad?

### Data Safety
- [ ] **Mass Assignment**: Check `permit` calls in controllers. Are we allowing sensitive fields (e.g., `admin`, `role`) to be updated?
- [ ] **SQL Injection**: Look for string interpolation in queries (e.g., `where("name = #{params[:name]}")`). usage of `?` or named placeholders is required.
- [ ] **XSS**: Look for `.html_safe` or `raw`. verify the content is truly safe.

### Privacy (SastaSpace Specific)
- [ ] **AI Data**: Ensure images sent to AI analysis are processed locally or securely.
- [ ] **Logs**: Check `config/initializers/filter_parameter_logging.rb`. Are passwords, tokens, and PII filtered?

## 3. Dependencies
Run an audit of gems:
```bash
bundle exec bundle-audit check --update
```
*   **Action**: Update vulnerable gems if found.

## 4. Report
Summarize findings and fixes applied.

