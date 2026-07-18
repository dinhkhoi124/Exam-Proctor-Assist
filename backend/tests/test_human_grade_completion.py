from dataset_benchmark.scripts.evaluate import _completed_human_grades


def test_blank_annotation_rows_are_not_counted_as_completed_grades():
    rubrics = ("correctness", "task_success")
    grades = {
        ("A", 101, "baseline"): {
            "correctness": None,
            "task_success": None,
        },
        ("A", 101, "proposed"): {
            "correctness": 4,
            "task_success": None,
        },
    }

    completed = _completed_human_grades(grades, rubrics)
    assert list(completed) == [("A", 101, "proposed")]
