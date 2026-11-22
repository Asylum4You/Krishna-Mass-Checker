"""CSV reporting for mock-only simulation results."""
import csv
import io


def build_simulation_report(results: list[dict[str, str]]) -> bytes:
    output = io.StringIO(newline="")
    fields = ["test_id", "scenario", "result", "detail", "mode"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows(results)
    return output.getvalue().encode("utf-8")
