from concurrent.futures import as_completed


def run_futures_raising_failures_after_completion(futures):
    successes = []
    failures = []
    for future in as_completed(futures):
        try:
            future.result()
            successes.append(future)
        except Exception as e:
            failures.append(e)
    if failures:
        failures_message = "\n".join(str(failure) for failure in failures)
        raise Exception(f"Futures failures: {failures_message}")
