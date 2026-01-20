"""Metrics collection module for RepoHealth Dashboard."""
import json
import subprocess
import re
import sys
from pathlib import Path
try:
    from lxml import etree  # type: ignore[import-untyped]
except ImportError:
    etree = None


def _find_executable(name: str) -> str:
    """Find executable in venv or system PATH."""
    try:
        python_dir = Path(sys.executable).parent
        venv_exe = python_dir / name
        if venv_exe.exists():
            return str(venv_exe)
    except Exception:
        pass
    return name


def run_radon_complexity(path: str) -> dict:
    """Run radon complexity analysis."""
    try:
        radon_exe = _find_executable("radon")
        result = subprocess.run(
            [radon_exe, "cc", "--json", path],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode != 0 and not result.stdout:
            return {"functions": [], "files": {}}
        
        data = json.loads(result.stdout)
        functions = []
        files = {}
        
        for filename, file_functions in data.items():
            max_complexity = 0
            for func in file_functions:
                complexity = func.get("complexity", 0)
                if complexity > 10:
                    functions.append({
                        "name": func.get("name", ""),
                        "complexity": complexity,
                        "file": filename
                    })
                max_complexity = max(max_complexity, complexity)
            if max_complexity > 0:
                files[filename] = max_complexity
        
        functions.sort(key=lambda x: x["complexity"], reverse=True)
        return {"functions": functions, "files": files}
    except Exception:
        return {"functions": [], "files": {}}


def run_radon_maintainability(path: str) -> dict:
    """Run radon maintainability index analysis."""
    try:
        radon_exe = _find_executable("radon")
        result = subprocess.run(
            [radon_exe, "mi", "--json", path],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode != 0 and not result.stdout:
            return {"files": {}}
        
        data = json.loads(result.stdout)
        files = {}
        
        if isinstance(data, dict):
            for file_path, metrics in data.items():
                rank = metrics.get("rank", "F")
                score = metrics.get("mi", 0.0)
                files[file_path] = {"rank": rank, "score": score}
        elif isinstance(data, list):
            for item in data:
                file_path = item.get("filename", "")
                rank = item.get("rank", "F")
                score = item.get("mi", 0.0)
                files[file_path] = {"rank": rank, "score": score}
        
        return {"files": files}
    except Exception:
        return {"files": {}}


def run_vulture_analysis(path: str = "backend/app") -> dict:
    """Run vulture dead code analysis."""
    try:
        vulture_exe = _find_executable("vulture")
        result = subprocess.run(
            [vulture_exe, path, "--min-confidence", "60"],
            capture_output=True,
            text=True,
            timeout=120
        )
        unused_functions = []
        unused_classes = []
        
        pattern = re.compile(r"^(.+?):(\d+): unused (function|variable|class|method|import|attribute|property) '([^']+)' \((\d+)% confidence\)")
        
        for line in result.stdout.split("\n"):
            match = pattern.match(line)
            if match:
                file_path, line_num, item_type, name, confidence = match.groups()
                item = {
                    "name": name,
                    "file": file_path,
                    "line": int(line_num),
                    "confidence": int(confidence) / 100.0
                }
                if item_type in ("function", "method"):
                    unused_functions.append(item)
                elif item_type == "class":
                    unused_classes.append(item)
        
        unused_functions.sort(key=lambda x: x["confidence"], reverse=True)
        unused_classes.sort(key=lambda x: x["confidence"], reverse=True)
        
        return {"unused_functions": unused_functions, "unused_classes": unused_classes}
    except Exception:
        return {"unused_functions": [], "unused_classes": []}


def find_duplicates(path: str = "backend/app") -> dict:
    """Find duplicate code using pylint."""
    try:
        pylint_exe = _find_executable("pylint")
        result = subprocess.run(
            [pylint_exe, "--disable=all", "--enable=duplicate-code", "--output-format=json", path],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        duplicate_blocks = []
        total_duplicated_lines = 0
        
        if result.returncode == 0 or result.stdout:
            try:
                data = json.loads(result.stdout)
                for message in data:
                    if message.get("message-id") == "R0801":
                        file_path = message.get("path", "")
                        line = message.get("line", 0)
                        msg = message.get("message", "")
                        
                        lines_match = re.search(r"Lines?\s+(\d+)[-:](\d+)", msg)
                        if lines_match:
                            start = int(lines_match.group(1))
                            end = int(lines_match.group(2))
                            total_duplicated_lines += (end - start + 1)
                        
                        duplicate_blocks.append({
                            "file": file_path,
                            "lines": f"{line}",
                            "message": msg
                        })
            except (json.JSONDecodeError, KeyError):
                pass
        
        return {
            "total_duplicated_lines": total_duplicated_lines,
            "duplicate_blocks": duplicate_blocks[:5]
        }
    except Exception:
        return {"total_duplicated_lines": 0, "duplicate_blocks": []}


def run_ty_check(path: str = "backend/app") -> dict:
    """Run ty type checker with robust error handling."""
    try:
        ty_exe = _find_executable("ty")
        result = subprocess.run(
            [ty_exe, "check", path],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        output = result.stdout + result.stderr
        error_matches = re.findall(r"error[:\[]", output, re.IGNORECASE)
        error_count = len(error_matches)
        
        errors_by_file = {}
        file_pattern = re.compile(r"-->\s*([^\s:]+\.py):\d+:\d+")
        for match in file_pattern.finditer(output):
            file_path = match.group(1)
            errors_by_file[file_path] = errors_by_file.get(file_path, 0) + 1
        
        return {
            "total_errors": error_count,
            "errors_by_file": errors_by_file,
            "errors": []
        }
    except Exception:
        return {"total_errors": -1, "errors_by_file": {}, "errors": []}


def run_tsc_check(frontend_path: str = "frontends") -> dict:
    """Run TypeScript type checker for all frontend projects."""
    frontend_base = Path(frontend_path)
    if not frontend_base.exists():
        return {"total_errors": 0, "errors_by_file": {}, "errors": [], "projects": {}}
    
    all_errors = []
    errors_by_file = {}
    projects = {}
    
    for project_dir in frontend_base.iterdir():
        if not project_dir.is_dir():
            continue
        
        package_json = project_dir / "package.json"
        if not package_json.exists():
            continue
        
        try:
            with open(package_json) as f:
                pkg_data = json.load(f)
                scripts = pkg_data.get("scripts", {})
                if "type-check" not in scripts:
                    continue
        except Exception:
            continue
        
        try:
            result = subprocess.run(
                ["npm", "run", "type-check"],
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                timeout=120
            )
            
            output = result.stderr + result.stdout
            error_matches = re.findall(r"error TS\d+:", output)
            error_count = len(error_matches)
            
            file_errors = re.findall(r"([^\s]+)\((\d+),\d+\): error TS\d+:", output)
            for file_path, line_str in file_errors:
                rel_path = str(Path(project_dir) / file_path)
                errors_by_file[rel_path] = errors_by_file.get(rel_path, 0) + 1
                all_errors.append({
                    "file": rel_path,
                    "line": int(line_str),
                    "message": "TypeScript error"
                })
            
            projects[project_dir.name] = error_count
        except Exception:
            projects[project_dir.name] = 0
    
    return {
        "total_errors": sum(projects.values()),
        "errors_by_file": errors_by_file,
        "errors": all_errors,
        "projects": projects
    }


def parse_coverage_xml(path: str = "htmlcov/coverage.xml") -> dict:
    """Parse backend coverage XML (coverage.py format)."""
    coverage_path = Path(path)
    if not coverage_path.exists():
        return {"total_lines": 0, "covered_lines": 0, "coverage_percent": 0.0, "files": {}}
    
    try:
        if etree is None:
            return {"total_lines": 0, "covered_lines": 0, "coverage_percent": 0.0, "files": {}}
        tree = etree.parse(str(coverage_path))
        root = tree.getroot()
        
        total_lines = int(root.get("lines-valid", 0))
        covered_lines = int(root.get("lines-covered", 0))
        line_rate = float(root.get("line-rate", 0.0))
        
        if line_rate > 0:
            coverage_percent = line_rate * 100
        elif total_lines > 0:
            coverage_percent = (covered_lines / total_lines * 100)
        else:
            coverage_percent = 0.0
        
        files = {}
        for class_elem in root.findall(".//class"):
            file_path = class_elem.get("filename", "")
            file_line_rate = float(class_elem.get("line-rate", 0.0))
            if file_line_rate > 0:
                files[file_path] = file_line_rate * 100
        
        return {
            "total_lines": total_lines,
            "covered_lines": covered_lines,
            "coverage_percent": coverage_percent,
            "files": files
        }
    except Exception:
        return {"total_lines": 0, "covered_lines": 0, "coverage_percent": 0.0, "files": {}}


def parse_frontend_coverage(frontend_path: str = "frontends") -> dict:
    """Parse frontend coverage from clover.xml or lcov.info."""
    frontend_base = Path(frontend_path)
    if not frontend_base.exists():
        return {"total_lines": 0, "covered_lines": 0, "coverage_percent": 0.0, "files": {}, "projects": {}}
    
    total_lines = 0
    total_covered = 0
    all_files = {}
    projects = {}
    
    for project_dir in frontend_base.iterdir():
        if not project_dir.is_dir():
            continue
        
        clover_path = project_dir / "coverage" / "clover.xml"
        lcov_path = project_dir / "coverage" / "lcov.info"
        
        project_lines = 0
        project_covered = 0
        
        if clover_path.exists():
            try:
                if etree is None:
                    continue
                tree = etree.parse(str(clover_path))
                root = tree.getroot()
                
                for file_elem in root.findall(".//file"):
                    file_path = file_elem.get("name", "")
                    metrics = file_elem.find("metrics")
                    if metrics is not None:
                        file_lines = int(metrics.get("statements", 0))
                        file_covered = int(metrics.get("coveredstatements", 0))
                        project_lines += file_lines
                        project_covered += file_covered
                        if file_lines > 0:
                            all_files[file_path] = (file_covered / file_lines * 100)
            except Exception:
                pass
        
        elif lcov_path.exists():
            try:
                with open(lcov_path) as f:
                    current_file = None
                    file_lines = 0
                    for line in f:
                        if line.startswith("SF:"):
                            current_file = line[3:].strip()
                            file_lines = 0
                        elif line.startswith("LF:"):
                            file_lines = int(line[3:].strip())
                            project_lines += file_lines
                        elif line.startswith("LH:"):
                            file_covered = int(line[3:].strip())
                            project_covered += file_covered
                            if current_file and file_lines > 0:
                                all_files[current_file] = (file_covered / file_lines * 100)
            except Exception:
                pass
        
        if project_lines > 0:
            projects[project_dir.name] = (project_covered / project_lines * 100)
            total_lines += project_lines
            total_covered += project_covered
    
    coverage_percent = (total_covered / total_lines * 100) if total_lines > 0 else 0.0
    
    return {
        "total_lines": total_lines,
        "covered_lines": total_covered,
        "coverage_percent": coverage_percent,
        "files": all_files,
        "projects": projects
    }


def merge_coverage(backend_coverage: dict, frontend_coverage: dict, loc_data: dict) -> dict:
    """Merge backend and frontend coverage with weighted average."""
    backend_loc = sum(
        f.get("loc", 0) for f in loc_data.get("files", {}).values()
        if f.get("type") == "python"
    )
    frontend_loc = sum(
        f.get("loc", 0) for f in loc_data.get("files", {}).values()
        if f.get("type") in ["javascript", "typescript"]
    )
    total_loc = backend_loc + frontend_loc
    
    if total_loc == 0:
        return {
            "overall_coverage": 0.0,
            "backend_coverage": backend_coverage.get("coverage_percent", 0.0),
            "frontend_coverage": frontend_coverage.get("coverage_percent", 0.0),
            "backend_weight": 0.0,
            "frontend_weight": 0.0
        }
    
    backend_weight = backend_loc / total_loc
    frontend_weight = frontend_loc / total_loc
    
    backend_cov = backend_coverage.get("coverage_percent", 0.0)
    frontend_cov = frontend_coverage.get("coverage_percent", 0.0)
    
    overall = (backend_cov * backend_weight) + (frontend_cov * frontend_weight)
    
    return {
        "overall_coverage": overall,
        "backend_coverage": backend_cov,
        "frontend_coverage": frontend_cov,
        "backend_weight": backend_weight,
        "frontend_weight": frontend_weight
    }


def calculate_loc_stats(backend_path: str = "backend/app", frontend_path: str = "frontends") -> dict:
    """Calculate LOC statistics for Python and JS/TS files."""
    backend_base = Path(backend_path)
    frontend_base = Path(frontend_path)
    
    files = {}
    total_loc = 0
    total_comments = 0
    
    if backend_base.exists():
        for py_file in backend_base.rglob("*.py"):
            if "tests" in str(py_file) or "__pycache__" in str(py_file):
                continue
            
            result = _process_python_file(py_file)
            if result:
                 files[result["rel_path"]] = result["data"]
                 total_loc += result["data"]["loc"]
                 total_comments += result["data"]["comments"]
    
    if frontend_base.exists():
        for js_file in frontend_base.rglob("*"):
             if not js_file.is_file():
                continue
             if js_file.suffix not in [".js", ".jsx", ".ts", ".tsx"]:
                continue
             if "node_modules" in str(js_file) or "dist" in str(js_file):
                continue
             
             result = _process_js_file(js_file)
             if result:
                 files[result["rel_path"]] = result["data"]
                 total_loc += result["data"]["loc"]
                 total_comments += result["data"]["comments"]
    
    return {
        "total_loc": total_loc,
        "total_comments": total_comments,
        "ratio": total_comments / total_loc if total_loc > 0 else 0.0,
        "files": files
    }

def _process_python_file(file_path: Path) -> dict | None:
    try:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        
        loc, comments = _count_python_lines(lines)
        
        if loc > 0:
             return {
                 "rel_path": _get_relative_path(file_path),
                 "data": {
                     "loc": loc,
                     "comments": comments,
                     "ratio": comments / loc if loc > 0 else 0.0,
                     "type": "python"
                 }
             }
    except Exception:
        pass
    return None

def _count_python_lines(lines: list[str]) -> tuple[int, int]:
    loc = 0
    comments = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#") and not stripped.startswith("#!"):
            comments += 1
        else:
            loc += 1
    return loc, comments

def _process_js_file(file_path: Path) -> dict | None:
    try:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
             content = f.read()
        
        lines = content.split("\n")
        loc, comments = _count_js_lines(lines)

        if loc > 0:
            file_type = "typescript" if file_path.suffix in [".ts", ".tsx"] else "javascript"
            return {
                "rel_path": _get_relative_path(file_path),
                "data": {
                    "loc": loc,
                    "comments": comments,
                    "ratio": comments / loc if loc > 0 else 0.0,
                    "type": file_type
                }
            }
    except Exception:
        pass
    return None

def _count_js_lines(lines: list[str]) -> tuple[int, int]:
    loc = 0
    comments = 0
    in_multiline = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if "/*" in stripped:
            in_multiline = True
        if "*/" in stripped:
            in_multiline = False
            comments += 1
            continue
        if in_multiline:
            comments += 1
            continue

        if stripped.startswith("//"):
            comments += 1
        else:
            loc += 1
    return loc, comments

def _get_relative_path(file_path: Path) -> str:
    abs_file = file_path.resolve()
    abs_cwd = Path.cwd().resolve()
    try:
        return str(abs_file.relative_to(abs_cwd))
    except ValueError:
        return str(file_path)


def find_large_files(backend_path: str = "backend/app", frontend_path: str = "frontends", threshold: int = 300) -> list:
    """Find files exceeding LOC threshold."""
    loc_data = calculate_loc_stats(backend_path, frontend_path)
    large_files = []
    
    for file_path, file_data in loc_data.get("files", {}).items():
        loc = file_data.get("loc", 0)
        if loc > threshold:
            large_files.append({
                "file": file_path,
                "loc": loc,
                "type": file_data.get("type", "unknown")
            })
    
    large_files.sort(key=lambda x: x["loc"], reverse=True)
    return large_files


def categorize_files() -> dict:
    """Categorize files by type."""
    backend_count = 0
    frontend_count = 0
    test_count = 0
    
    backend_base = Path("backend/app")
    if     backend_base.exists():
        for py_file in backend_base.rglob("*.py"):
            if "tests" not in str(py_file) and "__pycache__" not in str(py_file):
                backend_count += 1
    
    frontend_base = Path("frontends")
    if frontend_base.exists():
        for js_file in frontend_base.rglob("*"):
            if js_file.is_file() and js_file.suffix in [".js", ".jsx", ".ts", ".tsx"]:
                if "node_modules" not in str(js_file) and "dist" not in str(js_file):
                    frontend_count += 1
    
    for test_file in Path(".").rglob("*"):
        if test_file.is_file():
            name = test_file.name.lower()
            if name.startswith("test") and test_file.suffix in [".py", ".js", ".ts", ".jsx", ".tsx"]:
                test_count += 1
    
    return {
        "backend": backend_count,
        "frontend": frontend_count,
        "tests": test_count
    }


def correlate_type_errors_complexity(ty_data: dict, tsc_data: dict, complexity_data: dict) -> dict:
    """Correlate type errors with complexity for AI Hallucination Index."""
    hallucination_files = []
    complexity_by_file = complexity_data.get("files", {})
    all_type_errors = {}
    
    for file_path, error_count in ty_data.get("errors_by_file", {}).items():
        all_type_errors[file_path] = error_count
    
    for file_path, error_count in tsc_data.get("errors_by_file", {}).items():
        all_type_errors[file_path] = all_type_errors.get(file_path, 0) + error_count
    
    for file_path, type_errors in all_type_errors.items():
        complexity = complexity_by_file.get(file_path, 0)
        
        if complexity > 10 and type_errors > 0:
            score = min((complexity / 20) * (type_errors / 10), 1.0)
            hallucination_files.append({
                "file": file_path,
                "complexity": complexity,
                "type_errors": type_errors,
                "hallucination_score": score,
                "pattern": "complex_wrong"
            })
        elif complexity < 5 and type_errors > 3:
            score = min((type_errors / 10) * 1.2, 1.0)
            hallucination_files.append({
                "file": file_path,
                "complexity": complexity,
                "type_errors": type_errors,
                "hallucination_score": score,
                "pattern": "confidently_wrong"
            })
    
    hallucination_files.sort(key=lambda x: x["hallucination_score"], reverse=True)
    
    return {
        "hallucination_files": hallucination_files,
        "total_hallucination_files": len(hallucination_files)
    }


def load_trend_history() -> list:
    """Load trend history from JSON file."""
    history_path = Path(".repo_health_history.json")
    if not history_path.exists():
        return []
    
    try:
        with open(history_path) as f:
            return json.load(f)
    except Exception:
        return []


def save_trend_history(data: dict) -> None:
    """Save trend history to JSON file (keep last 30 entries)."""
    history = load_trend_history()
    
    history.append({
        "timestamp": data.get("timestamp", ""),
        "global_score": data.get("global_score", "F"),
        "total_complexity": data.get("total_complexity", 0),
        "coverage_pct": data.get("coverage_pct", 0.0)
    })
    
    history = history[-30:]
    
    history_path = Path(".repo_health_history.json")
    try:
        with open(history_path, "w") as f:
            json.dump(history, f, indent=2)
    except Exception:
        pass
