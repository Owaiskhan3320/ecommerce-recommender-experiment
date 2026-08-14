from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_SCRIPTS = [
    "run_sql_pipeline.py",
    "run_product_analysis.py",
    "run_recommender_evaluation.py",
    "run_experiment_planning.py",
    "run_synthetic_experiment_analysis.py",
]


def main() -> None:
    for script_name in PIPELINE_SCRIPTS:
        script_path = PROJECT_ROOT / "src" / script_name
        print(f"\nRunning {script_name}...")
        subprocess.run(
            [sys.executable, str(script_path)],
            check=True,
            cwd=PROJECT_ROOT,
        )

    print("\nProject pipeline complete. Outputs are available in reports/.")


if __name__ == "__main__":
    main()
