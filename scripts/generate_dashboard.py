#!/usr/bin/env python3
"""Generate RepoHealth Dashboard."""
import sys
import os
import json
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from jinja2 import Environment, FileSystemLoader

# Ensure we are at project root
root_dir = Path(__file__).resolve().parent.parent
os.chdir(root_dir)

# Add backend to path
backend_path = root_dir / "backend"
sys.path.insert(0, str(backend_path))

from app.utils import metrics


def calculate_global_score(maintainability_data: dict) -> str:
    """Calculate global score from maintainability ranks."""
    files = maintainability_data.get("files", {})
    if not files:
        return "F"
    
    ranks = {"A": 4, "B": 3, "C": 2, "D": 1, "E": 0, "F": 0}
    total_score = sum(ranks.get(f.get("rank", "F"), 0) for f in files.values())
    avg_score = total_score / len(files)
    
    if avg_score >= 3.5:
        return "A"
    elif avg_score >= 2.5:
        return "B"
    elif avg_score >= 1.5:
        return "C"
    elif avg_score >= 0.5:
        return "D"
    return "F"


def get_top_complex(complexity_data: dict, limit: int = 5) -> list:
    """Get top N complex functions."""
    functions = complexity_data.get("functions", [])
    return functions[:limit]


def get_low_coverage(backend_coverage: dict, frontend_coverage: dict, threshold: float = 80.0) -> list:
    """Get files with coverage below threshold."""
    backend_files = backend_coverage.get("files", {})
    frontend_files = frontend_coverage.get("files", {})
    
    low_coverage = [
        {"file": file_path, "coverage": coverage}
        for file_path, coverage in {**backend_files, **frontend_files}.items()
        if coverage < threshold
    ]
    
    low_coverage.sort(key=lambda x: x["coverage"])
    return low_coverage


def get_top_zombie(vulture_data: dict, limit: int = 10) -> dict:
    """Get top N zombie code items."""
    return {
        "unused_functions": vulture_data.get("unused_functions", [])[:limit],
        "unused_classes": vulture_data.get("unused_classes", [])[:limit]
    }


def get_verbose_files(loc_data: dict, threshold: float = 0.3) -> list:
    """Get files with high comment-to-code ratio."""
    verbose = []
    for file_path, file_data in loc_data.get("files", {}).items():
        ratio = file_data.get("ratio", 0.0)
        if ratio > threshold:
            verbose.append({
                "file": file_path,
                "type": file_data.get("type", "unknown"),
                "loc": file_data.get("loc", 0),
                "comments": file_data.get("comments", 0),
                "ratio": ratio
            })
    
    verbose.sort(key=lambda x: x["ratio"], reverse=True)
    return verbose


def prepare_scatter_data(complexity_data: dict, backend_coverage: dict, frontend_coverage: dict, maintainability_data: dict) -> list:
    """Prepare scatter plot data."""
    scatter_data = []
    complexity_files = complexity_data.get("files", {})
    backend_files = backend_coverage.get("files", {})
    frontend_files = frontend_coverage.get("files", {})
    all_coverage = {**backend_files, **frontend_files}
    maintainability_files = maintainability_data.get("files", {})
    
    for file_path, complexity in complexity_files.items():
        coverage = all_coverage.get(file_path, 0.0)
        rank = maintainability_files.get(file_path, {}).get("rank", "F")
        scatter_data.append({
            "x": complexity,
            "y": coverage,
            "rank": rank
        })
    
    return scatter_data


def main():
    """Generate dashboard."""
    print("🔍 Collecting metrics...")
    
    backend_path = str(Path("backend/app").resolve())
    frontend_path = str(Path("frontends").resolve())
    
    with ThreadPoolExecutor(max_workers=6) as executor:
        print("  Running radon complexity...")
        future_complexity = executor.submit(metrics.run_radon_complexity, backend_path)
        
        print("  Running radon maintainability...")
        future_maintainability = executor.submit(metrics.run_radon_maintainability, backend_path)
        
        print("  Running vulture analysis...")
        future_vulture = executor.submit(metrics.run_vulture_analysis, backend_path)
        
        print("  Running pylint duplicate detection...")
        future_duplication = executor.submit(metrics.find_duplicates, backend_path)
        
        print("  Running ty type checker...")
        future_ty = executor.submit(metrics.run_ty_check, backend_path)
        
        print("  Running tsc type checker...")
        future_tsc = executor.submit(metrics.run_tsc_check, frontend_path)
        
        print("  Waiting for parallel tasks to complete...")
        complexity_data = future_complexity.result()
        maintainability_data = future_maintainability.result()
        vulture_data = future_vulture.result()
        duplication_data = future_duplication.result()
        ty_data = future_ty.result()
        tsc_data = future_tsc.result()
    
    print("  Parsing coverage data...")
    coverage_path = "backend/coverage.xml"
    if not Path(coverage_path).exists():
        coverage_path = "htmlcov/coverage.xml"
    backend_coverage = metrics.parse_coverage_xml(coverage_path)
    frontend_coverage = metrics.parse_frontend_coverage("frontends")
    
    print("  Calculating LOC statistics...")
    loc_data = metrics.calculate_loc_stats(backend_path, frontend_path)
    
    print("  Finding large files...")
    large_files = metrics.find_large_files(backend_path, frontend_path)
    
    print("  Categorizing files...")
    file_categories = metrics.categorize_files()
    
    # Merge coverage
    print("  Merging coverage data...")
    merged_coverage = metrics.merge_coverage(backend_coverage, frontend_coverage, loc_data)
    
    # Derived metrics
    print("  Calculating derived metrics...")
    global_score = calculate_global_score(maintainability_data)
    
    # Calculate total complexity for trend
    total_complexity = sum(complexity_data.get("files", {}).values())
    
    # Type errors
    python_type_errors = ty_data.get("total_errors", 0) if ty_data.get("total_errors", -1) >= 0 else 0
    typescript_type_errors = tsc_data.get("total_errors", 0)
    total_type_errors = python_type_errors + typescript_type_errors
    
    total_files = len(complexity_data.get("files", {})) + len(tsc_data.get("errors_by_file", {}))
    type_coverage = (1 - (total_type_errors / max(total_files, 1))) * 100 if total_files > 0 else 100
    hallucination_data = metrics.correlate_type_errors_complexity(ty_data, tsc_data, complexity_data)
    
    template_data = {
        "global_score": global_score,
        "total_loc": loc_data.get("total_loc", 0),
        "overall_coverage": merged_coverage.get("overall_coverage", 0.0),
        "backend_coverage": merged_coverage.get("backend_coverage", 0.0),
        "frontend_coverage": merged_coverage.get("frontend_coverage", 0.0),
        "total_duplicated_lines": duplication_data.get("total_duplicated_lines", 0),
        "duplicate_blocks": duplication_data.get("duplicate_blocks", []),
        "total_type_errors": total_type_errors,
        "python_type_errors": ty_data.get("total_errors", -1),
        "typescript_type_errors": typescript_type_errors,
        "type_coverage": type_coverage,
        "top_complex_functions": get_top_complex(complexity_data, 5),
        "low_coverage_files": get_low_coverage(backend_coverage, frontend_coverage, threshold=80),
        "zombie_code": get_top_zombie(vulture_data, 10),
        "hallucination_files": hallucination_data.get("hallucination_files", [])[:10],
        "complexity_scatter_data": prepare_scatter_data(complexity_data, backend_coverage, frontend_coverage, maintainability_data) if maintainability_data.get("files") else [],
        "file_distribution": file_categories,
        "verbose_files": get_verbose_files(loc_data, threshold=0.3),
        "large_files": large_files,
    }
    
    print("  Loading trend history...")
    trend_history = metrics.load_trend_history()
    template_data["trend_history"] = trend_history
    
    metrics.save_trend_history({
        "timestamp": datetime.now().isoformat(),
        "global_score": global_score,
        "total_complexity": total_complexity,
        "coverage_pct": merged_coverage.get("overall_coverage", 0.0)
    })
    
    # DEBUG: Save intermediate data to JSON
    print("  Saving debug data to dashboard_data.json...")
    debug_data_path = Path(__file__).parent.parent / "dashboard_data.json"
    with open(debug_data_path, "w") as f:
        # Use default=str to handle any non-serializable objects (like sets or datetimes not in strings)
        json.dump(template_data, f, indent=2, default=str)
    
    print("  Rendering dashboard template...")
    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("dashboard.html.j2")
    
    data_json = {
        "trend_history": trend_history,
        "complexity_scatter_data": template_data["complexity_scatter_data"],
        "file_distribution": file_categories,
        "type_coverage": type_coverage,
        "python_type_errors": python_type_errors,
        "typescript_type_errors": typescript_type_errors
    }
    template_data["data_json"] = json.dumps(data_json)
    
    html_content = template.render(**template_data)
    output_path = Path(__file__).parent.parent / "dashboard.html"
    with open(output_path, "w") as f:
        f.write(html_content)
    
    print(f"✅ Dashboard generated: {output_path}")
    print(f"   Global Score: {global_score}")
    print(f"   Overall Coverage: {merged_coverage.get('overall_coverage', 0.0):.1f}%")
    print(f"   Type Errors: {total_type_errors}")
    print(f"   Total LOC: {loc_data.get('total_loc', 0):,}")


if __name__ == "__main__":
    main()
