---
description: "Step-by-step guide to scaffolding a new feature in the SastaSpace Rails monolith."
globs: []
---

# Setup New Feature

Follow this workflow to build a robust, Apple-quality feature.

## Phase 1: Domain & Model
1.  **Design**: Define the data structure.
2.  **Migration**: `rails g migration Create<Resource> ...`
3.  **Model**: Create `app/models/<resource>.rb`.
    *   Add associations.
    *   Add validations.
4.  **Test (Model)**: Create `test/models/<resource>_test.rb`.
    *   Test validations.
    *   Test happy/sad paths.

## Phase 2: Core Logic (Services)
*If the logic is complex (e.g., AI processing, complex calculations), do not put it in the Controller.*
1.  **Service**: Create `app/services/<resource>_service.rb`.
2.  **Test (Service)**: Unit test the service logic.

## Phase 3: Interface (Controller & Views)
1.  **Routes**: Add entry in `config/routes.rb`.
2.  **Controller**: `app/controllers/api/v1/<resources>_controller.rb` (or standard controller if server-rendered).
3.  **Views**:
    *   Use **Hotwire** (Turbo Frames) for interactivity.
    *   Style with **Tailwind CSS** (Apple Design Guidelines).
4.  **Test (Controller/Integration)**:
    *   `rails test:controllers` or `rails test:integration`.

## Phase 4: Polish
1.  **UI/UX**: Check spacing, typography, and animations.
2.  **Lint**: Run `rubocop` on new files.
3.  **Review**: Run `git diff` and check against `code-review-checklist`.

