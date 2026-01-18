# RepoHealth Dashboard Generator

## Overview
Generate a single static HTML dashboard that monitors code health metrics across Python and JavaScript/TypeScript, specifically targeting AI-generated technical debt patterns: high cyclomatic complexity, verbosity, duplication, dead code, type safety issues, and test gaps. Includes trend tracking over time and type safety correlation analysis.

## Architecture

```
scripts/generate_dashboard.py
  ├── Collects metrics via shell commands (Python + JS/TS)
  ├── Parses outputs (radon, vulture, pylint, ty, tsc, coverage.xml)
  ├── Calculates derived metrics (verbosity, LOC, trends, type debt)
  ├── Reads/writes .repo_health_history.json
  └── Renders dashboard.html via Jinja2 template

backend/app/utils/metrics.py
  ├── run_radon_complexity() -> dict
  ├── run_radon_maintainability() -> dict
  ├── run_vulture_analysis() -> dict
  ├── find_duplicates() -> dict (uses pylint)
  ├── run_ty_check() -> dict (Python type checking, robust error handling)
  ├── run_tsc_check() -> dict (TypeScript type checking)
  ├── parse_coverage_xml() -> dict (backend coverage)
  ├── parse_frontend_coverage() -> dict (frontend coverage, NEW)
  ├── merge_coverage() -> dict (weighted average, NEW)
  ├── calculate_loc_stats() -> dict (polyglot)
  ├── find_large_files() -> list (polyglot)
  ├── correlate_type_errors_complexity() -> dict (AI Hallucination Index, tuned)
  └── load_trend_history() / save_trend_history() -> dict
```

## Implementation Steps

### Phase 1: Dependencies & Setup

**File: `backend/pyproject.toml`**
- Add to `[dependency-groups.dev]`:
  - `radon>=6.0.0` (complexity analysis)
  - `lxml>=5.0.0` (XML parsing for coverage)
  - `vulture>=2.9.0` (dead code detection)
  - `pylint>=3.0.0` (duplication detection)
- Note: `ty>=0.0.12` is already in dev dependencies

**File: `frontends/*/package.json`**
- Ensure `typescript` is in `devDependencies` (add if missing)
- Add `type-check` script: `"type-check": "tsc --noEmit"` (if not present)

**File: `.gitignore`**
- Add `.repo_health_history.json` to ignore trend tracking file

**File: `Makefile`**
- Add `dashboard` target that:
  1. Runs `pytest --cov` to generate `coverage.xml` (backend)
  2. Runs `npm run test:coverage` in each frontend project to generate frontend coverage
     - For each project in `frontends/`: `cd frontends/<project> && npm run test:coverage`
  3. Executes `python scripts/generate_dashboard.py`
  4. Opens `dashboard.html` in default browser

### Phase 2: Metrics Collection Module

**File: `backend/app/utils/metrics.py` (NEW)**

**Functions to implement:**

1. **`run_radon_complexity(path: str) -> dict`**
   - Execute: `radon cc --json <path>`
   - Parse JSON output
   - Return: `{"functions": [{"name": str, "complexity": int, "file": str}], "files": {file: max_complexity}}`
   - Filter functions with complexity > 10

2. **`run_radon_maintainability(path: str) -> dict`**
   - Execute: `radon mi --json <path>`
   - Parse JSON output
   - Return: `{"files": {file: {"rank": str, "score": float}}}`
   - Calculate average maintainability index

3. **`run_vulture_analysis(path: str = "backend/app") -> dict`**
   - Execute: `vulture <path> --min-confidence 80 --format json`
   - Parse JSON output
   - Return: `{"unused_functions": [{"name": str, "file": str, "line": int, "confidence": float}], "unused_classes": [{"name": str, "file": str, "line": int, "confidence": float}]}`
   - Group by file for dashboard display
   - Sort by confidence descending

4. **`find_duplicates(path: str = "backend/app") -> dict`**
   - Execute: `pylint --disable=all --enable=duplicate-code --output-format=json <path>`
   - Parse JSON output for duplicate-code messages
   - Extract line counts from messages (e.g., "Lines 10-15")
   - Calculate total duplicated lines
   - Return: `{"total_duplicated_lines": int, "duplicate_blocks": [{"file": str, "lines": str, "message": str}]}`

5. **`run_ty_check(path: str = "backend/app") -> dict`**
   - **Robust Error Handling**: Wrap entire function in broad `try/except Exception`
   - Execute: `ty check --output-format=json <path>` (or parse stdout if JSON unavailable)
   - **Fallback Strategy**: If JSON parsing fails or command fails:
     - Try parsing stdout/stderr for error count
     - If that fails, return `{"total_errors": -1, "errors_by_file": {}, "errors": []}` to indicate "unknown" status
   - Parse output to count type errors
   - Group errors by file
   - Return: `{"total_errors": int, "errors_by_file": {file: error_count}, "errors": [{"file": str, "line": int, "message": str}]}`
   - Handle cases where `ty` is not installed gracefully (return `{"total_errors": -1}` for unknown)
   - **Note**: `ty` is version 0.0.12, JSON schema may change - be defensive

6. **`run_tsc_check(frontend_path: str = "frontends") -> dict`**
   - For each frontend project in `frontends/`:
     - Change directory to project root
     - Execute: `npm run type-check` (which runs `tsc --noEmit`)
     - Parse stderr/stdout to count "error TS" occurrences
     - Extract error messages and file locations
   - Aggregate across all frontend projects
   - Return: `{"total_errors": int, "errors_by_file": {file: error_count}, "errors": [{"file": str, "line": int, "message": str}], "projects": {project_name: error_count}}`
   - Handle cases where TypeScript is not installed or no `type-check` script exists (return 0 errors)

7. **`parse_coverage_xml(path: str = "htmlcov/coverage.xml") -> dict`**
   - Parse XML using `lxml.etree`
   - Extract: `{"total_lines": int, "covered_lines": int, "coverage_percent": float, "files": {file: coverage%}}`
   - Handle missing file gracefully (return 0% coverage)

8. **`parse_frontend_coverage(frontend_path: str = "frontends") -> dict`**
   - For each frontend project in `frontends/`:
     - Check for coverage files: `coverage/clover.xml` (Vitest) or `coverage/lcov.info` (Jest/Vitest)
     - Parse XML (clover.xml) or LCOV format (lcov.info)
     - Extract: `{"total_lines": int, "covered_lines": int, "coverage_percent": float, "files": {file: coverage%}}`
   - Aggregate across all frontend projects (weighted by LOC)
   - Return: `{"total_lines": int, "covered_lines": int, "coverage_percent": float, "files": {file: coverage%}, "projects": {project_name: coverage%}}`
   - Handle missing coverage files gracefully (return 0% coverage for that project)
   - Note: Vitest typically generates `coverage/clover.xml` when using `@vitest/coverage-v8`

9. **`calculate_loc_stats(backend_path: str = "backend/app", frontend_path: str = "frontends") -> dict`**
   - **Python files:** `find <backend_path> -name "*.py" -not -path "*/tests/*"`
   - **JavaScript/TypeScript files:** `find <frontend_path> -name "*.js" -o -name "*.jsx" -o -name "*.ts" -o -name "*.tsx" -not -path "*/node_modules/*" -not -path "*/dist/*"`
   - For each file:
     - Count total lines (excluding empty lines)
     - Count comment lines:
       - Python: Lines starting with `#` (excluding shebang)
       - JS/TS: Single-line `//` and multi-line `/* */` blocks
     - Calculate comment-to-code ratio
   - Return: `{"total_loc": int, "total_comments": int, "ratio": float, "files": {file: {"loc": int, "comments": int, "ratio": float, "type": "python"|"javascript"|"typescript"}}}`

10. **`find_large_files(backend_path: str = "backend/app", frontend_path: str = "frontends", threshold: int = 300) -> list`**
   - Scan both Python and JS/TS files (exclude tests, node_modules, dist)
   - Find files exceeding threshold LOC
   - Return: `[{"file": str, "loc": int, "type": "python"|"javascript"|"typescript"}]`
   - Sort by LOC descending

11. **`categorize_files() -> dict`**
   - Group files by category:
     - `backend`: `backend/app/**/*.py` (exclude tests)
     - `frontend`: `frontends/**/*.{js,jsx,ts,tsx}` (exclude node_modules, dist)
     - `tests`: `**/test*.py`, `**/*.test.{js,jsx}`, `**/*.spec.{js,ts}`
   - Return counts for pie chart: `{"backend": int, "frontend": int, "tests": int}`

12. **`correlate_type_errors_complexity(ty_data: dict, tsc_data: dict, complexity_data: dict) -> dict`**
    - Cross-reference files with type errors against files with complexity data
    - Calculate "AI Hallucination Index" with two patterns:
      - **Pattern 1: Complex & Wrong**: High complexity (>10) AND type errors
        - Score: `(complexity / 20) * (type_errors / 10)` (normalized, capped at 1.0)
      - **Pattern 2: Confidently Wrong**: Low complexity (<5) BUT high type errors (>3)
        - Score: `(type_errors / 10) * 1.2` (penalty multiplier for overconfidence)
        - Flag as "Confidently Wrong" (common AI trait: simple code with wrong types)
    - Return: `{"hallucination_files": [{"file": str, "complexity": int, "type_errors": int, "hallucination_score": float, "pattern": "complex_wrong"|"confidently_wrong"}], "total_hallucination_files": int}`
    - Sort by hallucination_score descending
    - Combine both patterns in the same list

13. **`merge_coverage(backend_coverage: dict, frontend_coverage: dict, loc_data: dict) -> dict`**
    - Calculate weighted average coverage based on LOC
    - Backend weight: `backend_loc / total_loc`
    - Frontend weight: `frontend_loc / total_loc`
    - Overall coverage: `(backend_coverage * backend_weight) + (frontend_coverage * frontend_weight)`
    - Return: `{"overall_coverage": float, "backend_coverage": float, "frontend_coverage": float, "backend_weight": float, "frontend_weight": float}`
    - Handle cases where one coverage is missing (use available one, or 0% if both missing)

14. **`load_trend_history() -> list`**
   - Read `.repo_health_history.json` from project root
   - Return: `[{"timestamp": str, "global_score": str, "total_complexity": int, "coverage_pct": float}, ...]`
   - Return empty list if file doesn't exist
   - Handle JSON decode errors gracefully

15. **`save_trend_history(data: dict) -> None`**
    - Load existing history via `load_trend_history()`
    - Append new entry: `{"timestamp": datetime.now().isoformat(), "global_score": data["global_score"], "total_complexity": data["total_complexity"], "coverage_pct": data["coverage_pct"]}`
    - Keep last 30 entries (rolling window)
    - Write to `.repo_health_history.json` in project root
    - Create file if it doesn't exist

### Phase 3: Dashboard Template

**File: `scripts/templates/dashboard.html.j2` (NEW)**

**Structure:**
- Use Tailwind CSS via CDN
- Use Chart.js via CDN for visualizations (including gauge chart plugin)
- Dark mode theme (matching sastaspace aesthetic: sasta-black, sasta-accent colors)
- **Accessibility**: Add "Skip to Content" link at the very top
  - `<a href="#main-content" class="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-blue-600 focus:text-white focus:rounded">Skip to Content</a>`
- Main container: `<main id="main-content" class="container mx-auto px-4 py-8">`

**Sections:**

1. **Header Section**
   - **Global Score Badge**: Large badge showing A/B/C/D based on average maintainability
     - Color coding: A=green, B=yellow, C=orange, D=red
   - **Total LOC Display**: Shows combined Python + JS/TS lines
   - **Overall Coverage %**: Progress bar with percentage (weighted average of backend + frontend)
     - Tooltip shows breakdown: "Backend: X% | Frontend: Y%"
   - **Type Safety Badge**: Shows total type errors (Python + TypeScript)
     - Color coding: 0 errors = green, 1-10 = yellow, 11-50 = orange, 50+ = red
     - Format: "0 Errors" or "42 Errors"
   - **Complexity Trend Sparkline**: Small Chart.js line chart (last 30 data points)
     - X-axis: Timestamp (formatted as date)
     - Y-axis: Total Complexity
     - Tooltip on hover shows full metrics

2. **Danger Zone (Red Flags)**
   - **Top 5 Most Complex Functions** table
     - Columns: Rank, Function, File, Complexity
     - Highlight rows if complexity > 15 (red background)
     - Sort by complexity descending
   - **Low Coverage Files** table
     - Columns: File, Coverage %, Status (Bad/Warning/Good)
     - Show files with < 80% coverage
     - Color-code: < 50% = red, 50-80% = yellow, >= 80% = green
   - **Zombie Code** table
     - Columns: Type (Function/Class), Name, File, Line, Confidence %
     - Show unused functions/classes from vulture
     - Limit to top 10 by confidence
     - Sort by confidence descending

3. **Visualizations Row**
   - **Scatter Plot (Chart.js)**
     - X: Average Complexity per file
     - Y: Coverage %
     - Color-code by maintainability rank (A=green, B=yellow, C=orange, D=red)
     - Annotate "Death Quadrant" (high complexity > 10, low coverage < 80%) with shaded region
     - Include both Python files (from radon) and JS/TS files (if complexity data available)
   - **Pie Chart (Chart.js)**
     - Slices: Backend / Frontend / Tests
     - Show LOC distribution
     - Tooltip shows exact counts
   - **The Strictness Meter (Gauge Chart - Chart.js)**
     - Use Chart.js gauge/doughnut chart styled as a gauge
     - Show Type Coverage percentage: `(1 - (total_type_errors / total_files)) * 100`
     - Color zones: Green (90-100%), Yellow (70-89%), Orange (50-69%), Red (<50%)
     - Display: "Type Coverage: X%"
     - Subtitle: "Python: X errors | TypeScript: Y errors"
   - **Type Debt Bar Chart (Chart.js)**
     - Compare Backend (Python) vs. Frontend (TypeScript) error counts
     - Two bars side-by-side: "Python (ty)" and "TypeScript (tsc)"
     - Y-axis: Error count
     - Color-code: Green (<5), Yellow (5-20), Orange (21-50), Red (50+)

4. **AI Audit Section**
   - **Verbosity Index Table** (Polyglot)
     - Files with comment-to-code ratio > 0.3
     - Columns: File, Type (Python/JS/TS), LOC, Comments, Ratio
     - Show both Python and JS/TS files
     - Sort by ratio descending
   - **Monolith Detector Table** (Polyglot)
     - Files > 300 LOC
     - Columns: File, Type, LOC, Recommendation (e.g., "Split into modules")
     - Show both Python and JS/TS files
     - Sort by LOC descending
   - **Duplication Summary**
     - Display: "Total Duplicated Lines: X" (large number)
     - Show top 5 duplicate blocks if available
     - Table: File, Lines, Message
   - **AI Hallucination Index Table** (NEW)
     - Two patterns detected:
       - **Complex & Wrong**: High complexity (>10) AND type errors
       - **Confidently Wrong**: Low complexity (<5) BUT high type errors (>3) - common AI trait
     - Columns: File, Type (Python/TS), Complexity, Type Errors, Pattern, Hallucination Score
     - Sort by hallucination_score descending
     - Highlight rows with score > 0.5 (red background)
     - Show top 10 files
     - Badge/icon for "Confidently Wrong" pattern to draw attention

### Phase 4: Dashboard Generator

**File: `scripts/generate_dashboard.py` (NEW)**

**Main flow:**
1. Import metrics module, Jinja2, and `concurrent.futures`
2. Set paths: `backend/app`, `frontends/`
3. **Collect metrics in parallel** (Performance Optimization):
   ```python
   import concurrent.futures
   
   # Heavy, independent shell commands run in parallel
   with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
       # Submit all independent tasks
       future_complexity = executor.submit(run_radon_complexity, "backend/app")
       future_maintainability = executor.submit(run_radon_maintainability, "backend/app")
       future_vulture = executor.submit(run_vulture_analysis, "backend/app")
       future_duplication = executor.submit(find_duplicates, "backend/app")
       future_ty = executor.submit(run_ty_check, "backend/app")
       future_tsc = executor.submit(run_tsc_check, "frontends")
       
       # Wait for all results
       complexity_data = future_complexity.result()
       maintainability_data = future_maintainability.result()
       vulture_data = future_vulture.result()
       duplication_data = future_duplication.result()
       ty_data = future_ty.result()
       tsc_data = future_tsc.result()
   
   # Lightweight tasks run sequentially (file I/O, no heavy computation)
   backend_coverage = parse_coverage_xml("htmlcov/coverage.xml")
   frontend_coverage = parse_frontend_coverage("frontends")
   loc_data = calculate_loc_stats("backend/app", "frontends")
   large_files = find_large_files("backend/app", "frontends")
   file_categories = categorize_files()
   
   # Derived metrics (depend on collected data)
   hallucination_data = correlate_type_errors_complexity(ty_data, tsc_data, complexity_data)
   merged_coverage = merge_coverage(backend_coverage, frontend_coverage, loc_data)
   ```
4. Calculate derived metrics:
   - Global score from maintainability (average rank)
   - Top 5 complex functions (sorted by complexity)
   - Low coverage files (< 80%) - from merged coverage (backend + frontend)
   - Verbosity index (high comment ratio > 0.3) - polyglot
   - Total complexity sum for trend tracking
   - Total type errors (Python + TypeScript)
   - Type coverage percentage
   - **Overall Coverage**: Weighted average of backend and frontend coverage
5. Load trend history
6. Create current snapshot and append to history
7. Save updated trend history
8. Prepare template data:
   ```python
   # Handle unknown type errors (-1 indicates tool failure)
   python_type_errors = ty_data["total_errors"] if ty_data["total_errors"] >= 0 else 0
   typescript_type_errors = tsc_data["total_errors"] if tsc_data["total_errors"] >= 0 else 0
   total_type_errors = python_type_errors + typescript_type_errors
   total_files = len(complexity_data.get("files", {})) + len(tsc_data.get("errors_by_file", {}))
   type_coverage = (1 - (total_type_errors / max(total_files, 1))) * 100 if total_files > 0 else 100
   
   # Merge backend and frontend coverage
   overall_coverage = merged_coverage["overall_coverage"]
   
   template_data = {
       "global_score": calculate_global_score(maintainability_data),
       "total_loc": loc_data["total_loc"],
       "overall_coverage": overall_coverage,
       "backend_coverage": merged_coverage["backend_coverage"],
       "frontend_coverage": merged_coverage["frontend_coverage"],
       "total_duplicated_lines": duplication_data["total_duplicated_lines"],
       "total_type_errors": total_type_errors,
       "python_type_errors": python_type_errors,
       "typescript_type_errors": typescript_type_errors,
       "type_coverage": type_coverage,
       "top_complex_functions": get_top_complex(complexity_data, 5),
       "low_coverage_files": get_low_coverage(merged_coverage, threshold=80),  # Use merged coverage
       "zombie_code": get_top_zombie(vulture_data, 10),
       "hallucination_files": hallucination_data["hallucination_files"][:10],
       "complexity_scatter_data": prepare_scatter_data(complexity_data, merged_coverage),
       "file_distribution": file_categories,
       "verbose_files": get_verbose_files(loc_data, threshold=0.3),
       "large_files": large_files,
       "trend_history": trend_history,
   }
   ```
9. Render template with Jinja2
10. Write to `dashboard.html` in project root

**Error Handling:**
- Wrap each metric collection in try/except
- Log warnings for failed metrics
- Continue with available data (graceful degradation)
- **Special handling for `ty`**: Return `{"total_errors": -1}` on any failure (tool version changes, JSON schema breaks)
- **Performance**: Parallel execution reduces total time from 30-60s to ~10-15s on moderate codebases

### Phase 5: Makefile Integration

**File: `Makefile`**
- Add target:
  ```makefile
  dashboard: ## Generate and open RepoHealth dashboard
  	@echo "Collecting backend coverage..."
  	cd backend && uv run pytest tests/ --cov=app --cov-report=xml --cov-report=html -q || true
  	@echo "Collecting frontend coverage..."
  	@for dir in frontends/*/; do \
  		if [ -f "$$dir/package.json" ] && grep -q "test:coverage" "$$dir/package.json"; then \
  			echo "Running coverage for $$dir..."; \
  			cd "$$dir" && npm run test:coverage || true; \
  			cd -; \
  		fi; \
  	done
  	@echo "Generating dashboard..."
  	python3 scripts/generate_dashboard.py
  	@echo "Dashboard generated: dashboard.html"
  	@python3 -c "import webbrowser; webbrowser.open('dashboard.html')" || open dashboard.html || xdg-open dashboard.html
  ```

## File Structure

```
backend/
  app/
    utils/
      __init__.py
      metrics.py          # NEW: Metrics collection (polyglot + dead code + duplication + trends)
  scripts/
    generate_dashboard.py # NEW: Main generator
    templates/
      dashboard.html.j2    # NEW: Jinja2 template
.repo_health_history.json # NEW: Trend tracking data (gitignored)
```

## Key Design Decisions

1. **Single HTML File**: All CSS/JS via CDN, embedded data as JSON in script tag
2. **On-the-fly Calculation**: No database, all metrics computed from current codebase
3. **Focus on Complexity**: Primary metric for detecting AI spaghetti code
4. **Death Quadrant**: Visual highlight of high-complexity, low-coverage files
5. **Graceful Degradation**: Handle missing coverage.xml, missing tools, etc.
6. **Polyglot Support**: Analyze both Python and JavaScript/TypeScript for comprehensive coverage
7. **Trend Tracking**: Store history in JSON file, visualize last 30 runs
8. **Dead Code Detection**: Use vulture with 80% confidence threshold to reduce false positives
9. **Duplication Detection**: Use pylint's duplicate-code checker for concrete metrics
10. **Type Safety Integration**: Use `ty` (Rust-based, fast) for Python and `tsc` for TypeScript
11. **AI Hallucination Index**: Correlate type errors with complexity to identify problematic AI-generated code
12. **Accessibility First**: Include "Skip to Content" link and semantic HTML structure
13. **Visual Type Debt**: Gauge chart and bar chart to make type errors immediately visible

## Dependencies

**Backend (Python):**
- `radon>=6.0.0` (complexity analysis)
- `lxml>=5.0.0` (XML parsing)
- `vulture>=2.9.0` (dead code detection)
- `pylint>=3.0.0` (duplication detection)
- `ty>=0.0.12` (Python type checking - already in dependencies)
- `jinja2>=3.1.0` (already in dependencies)

**Frontend (TypeScript):**
- `typescript` (must be in `frontends/*/package.json` devDependencies)
- `type-check` script in `package.json`: `"type-check": "tsc --noEmit"`

## Testing Considerations

- Test metrics collection with sample Python and JS/TS files
- Verify template renders correctly with mock data
- Ensure graceful handling of missing coverage.xml
- Test trend history file creation and updates (rolling window)
- Verify vulture and pylint output parsing
- Test polyglot LOC counting accuracy (comment detection for JS/TS)
- Test with empty codebase (no files)
- Test with missing tools (radon, vulture, pylint, ty, tsc not installed)
- Test `ty` output parsing (both JSON and stdout formats)
- Test `ty` error handling when tool fails or JSON schema changes (should return -1)
- Test `tsc` output parsing from stderr (error format)
- Test TypeScript checking across multiple frontend projects
- Test frontend coverage parsing (clover.xml and lcov.info formats)
- Test coverage merging with weighted averages
- Verify "Skip to Content" link functionality (keyboard navigation)
- Test AI Hallucination Index calculation with various complexity/error combinations
  - Test "Complex & Wrong" pattern (high complexity + errors)
  - Test "Confidently Wrong" pattern (low complexity but high errors)
- Verify gauge chart rendering with Chart.js
- Test parallel execution performance (should be significantly faster than sequential)
- Test graceful degradation when tools are missing

## Implementation Order

1. Add dependencies to pyproject.toml (radon, lxml, vulture, pylint)
2. Ensure TypeScript is in frontend package.json and add type-check script
3. Create metrics.py with basic functions (radon, backend coverage)
4. Add `parse_frontend_coverage()` function (CRITICAL: Missing metric)
5. Add `merge_coverage()` function to combine backend + frontend
6. Add vulture and pylint functions
7. Add `run_ty_check()` function with robust error handling
8. Add `run_tsc_check()` function
9. Add polyglot LOC counting
10. Add `correlate_type_errors_complexity()` function with both patterns
11. Add trend tracking functions
12. Create dashboard template with all sections (including accessibility, type safety badges, gauge chart, AI Hallucination Index)
13. Create generator script with **parallel execution** (CRITICAL: Performance optimization)
14. Update Makefile target to run frontend test coverage
15. Test end-to-end (verify parallel execution performance improvement)

## Critical Improvements (Veteran Engineer Review)

### ✅ 1. Frontend Test Coverage Integration
**Problem**: Plan only tracked backend coverage, creating false sense of security.

**Solution**:
- Added `parse_frontend_coverage()` to read `coverage/clover.xml` or `coverage/lcov.info`
- Added `merge_coverage()` to calculate weighted average (by LOC)
- Updated Makefile to run `npm run test:coverage` in each frontend project
- Dashboard now shows combined coverage with breakdown tooltip

### ✅ 2. Performance Optimization: Parallel Execution
**Problem**: Sequential execution of heavy commands (radon, vulture, pylint, ty, tsc) takes 30-60s.

**Solution**:
- Use `concurrent.futures.ThreadPoolExecutor` to run independent collectors in parallel
- Expected performance: 30-60s → 10-15s on moderate codebases
- Lightweight tasks (file I/O) remain sequential

### ✅ 3. Robust `ty` Error Handling
**Problem**: `ty` version 0.0.12 may have changing JSON schema, causing crashes.

**Solution**:
- Broad `try/except Exception` wrapper
- Fallback to stdout parsing if JSON fails
- Return `{"total_errors": -1}` on any failure (indicates "unknown" status)
- Dashboard handles -1 gracefully (shows as 0, but logs warning)

### ✅ 4. Enhanced AI Hallucination Index
**Problem**: Original formula only caught "Complex & Wrong" pattern.

**Solution**:
- **Pattern 1**: "Complex & Wrong" - High complexity (>10) + type errors
- **Pattern 2**: "Confidently Wrong" - Low complexity (<5) BUT high type errors (>3)
  - Common AI trait: simple code with wrong types
  - Score: `(type_errors / 10) * 1.2` (penalty multiplier)
- Dashboard highlights both patterns with badges

## Status: ✅ APPROVED WITH MODIFICATIONS

All critical gaps identified by veteran engineer review have been addressed. Plan is production-ready.
