"""Data access service for querying and filtering test data."""

from typing import Optional
from app.db import tests_collection, values_collection
from app.uuid_maps import resolve_channel_from_child_id


def _build_filter(
    customer: Optional[str] = None,
    material: Optional[str] = None,
    test_type: Optional[str] = None,
    machine: Optional[str] = None,
    tester: Optional[str] = None,
    standard: Optional[str] = None,
    test_program: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> dict:
    """Build a MongoDB filter from human-readable parameters."""
    import re
    query = {}

    def _exact_regex(value: str) -> dict:
        """Create a regex that matches the full field value, not a substring."""
        escaped = re.escape(value)
        return {"$regex": f"^{escaped}$", "$options": "i"}

    if customer:
        query["TestParametersFlat.CUSTOMER"] = _exact_regex(customer)
    if material:
        query["TestParametersFlat.MATERIAL"] = {"$regex": material, "$options": "i"}
    if test_type:
        query["TestParametersFlat.TYPE_OF_TESTING_STR"] = _exact_regex(test_type)
    if machine:
        query["TestParametersFlat.MACHINE_DATA"] = {"$regex": machine, "$options": "i"}
    if tester:
        query["TestParametersFlat.TESTER"] = _exact_regex(tester)
    if standard:
        query["TestParametersFlat.STANDARD"] = {"$regex": standard, "$options": "i"}
    if test_program:
        query["testProgramId"] = {"$regex": test_program, "$options": "i"}

    # Date filtering — DB stores dates as "DD.MM.YYYY" or "DD/MM/YYYY"
    # Support: "12/2023" (month/year), "2023" (year), "07.12.2023" (exact day)
    if date_from:
        query["TestParametersFlat.Date"] = {"$regex": date_from.replace("/", "[./]"), "$options": "i"}

    return query


# Key parameters to always include in summaries
SUMMARY_FIELDS = [
    "CUSTOMER", "MATERIAL", "TYPE_OF_TESTING_STR", "MACHINE_DATA",
    "TESTER", "STANDARD", "Date", "SPECIMEN_THICKNESS", "SPECIMEN_WIDTH",
    "TEST_SPEED", "TYPE_OF_TEST", "Specimen ID",
]


def _extract_params(test: dict) -> dict:
    """Extract all TestParametersFlat as a clean dict."""
    return test.get("TestParametersFlat", {})


def _extract_summary_params(test: dict) -> dict:
    """Extract key parameters for summary display."""
    params = test.get("TestParametersFlat", {})
    return {k: params.get(k) for k in SUMMARY_FIELDS if params.get(k) is not None}


async def query_tests(
    customer: Optional[str] = None,
    material: Optional[str] = None,
    test_type: Optional[str] = None,
    machine: Optional[str] = None,
    tester: Optional[str] = None,
    standard: Optional[str] = None,
    test_program: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
) -> dict:
    """Query tests with human-readable filters."""
    query = _build_filter(
        customer=customer, material=material, test_type=test_type,
        machine=machine, tester=tester, standard=standard,
        test_program=test_program, date_from=date_from, date_to=date_to,
    )

    total = await tests_collection.count_documents(query)
    cursor = tests_collection.find(query).skip(skip).limit(limit)
    tests = await cursor.to_list(limit)

    resolved_tests = []
    for test in tests:
        resolved_tests.append({
            "id": str(test.get("_id", "")),
            "name": test.get("name", ""),
            "state": test.get("state", ""),
            "test_program": test.get("testProgramId", ""),
            "parameters": _extract_params(test),
            "value_column_count": len(test.get("valueColumns", [])),
        })

    return {
        "total": total,
        "tests": resolved_tests,
    }


async def get_test_by_name(specimen_name: str) -> Optional[dict]:
    """Get a test by its specimen name (the 'name' field)."""
    test = await tests_collection.find_one({"name": specimen_name})
    if not test:
        # Try partial match
        test = await tests_collection.find_one({"name": {"$regex": specimen_name, "$options": "i"}})
    if not test:
        return None

    return {
        "id": str(test["_id"]),
        "name": test.get("name", ""),
        "state": test.get("state", ""),
        "test_program": test.get("testProgramId", ""),
        "parameters": _extract_params(test),
    }


async def get_test_by_id(test_id: str) -> Optional[dict]:
    """Get a single test by ID with all parameters."""
    test = await tests_collection.find_one({"_id": test_id})
    if not test:
        return None

    return {
        "id": str(test["_id"]),
        "name": test.get("name", ""),
        "state": test.get("state", ""),
        "test_program": test.get("testProgramId", ""),
        "parameters": _extract_params(test),
        "value_columns": [
            {
                "id": vc.get("_id", ""),
                "name": vc.get("name", ""),
                "unit_table": vc.get("unitTableId", ""),
            }
            for vc in test.get("valueColumns", [])
            if not vc.get("_id", "").endswith("_Key")
        ],
    }


async def get_values_for_test(test_id: str, channel_name: Optional[str] = None) -> list[dict]:
    """Fetch value columns for a given test. Optionally filter by channel name."""
    query = {"metadata.refId": test_id}
    cursor = values_collection.find(query)
    values = await cursor.to_list(None)

    results = []
    for val in values:
        meta = val.get("metadata", {})
        child_id = meta.get("childId", "")

        # Skip _Key entries
        if "_Key" in child_id:
            continue

        # Parse channel name from filename
        filename = val.get("filename", "")

        results.append({
            "child_id": child_id,
            "filename": filename,
            "values_count": val.get("valuesCount", len(val.get("values", []))),
            "values": val.get("values", []),
            "upload_date": str(val.get("uploadDate", "")),
        })

    return results


async def get_summary_table(
    customer: Optional[str] = None,
    material: Optional[str] = None,
    test_type: Optional[str] = None,
    machine: Optional[str] = None,
    tester: Optional[str] = None,
    standard: Optional[str] = None,
    date_from: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """Get a summary table of tests for data preview. Returns {total, rows}."""
    query = _build_filter(
        customer=customer, material=material, test_type=test_type,
        machine=machine, tester=tester, standard=standard,
        date_from=date_from,
    )

    total = await tests_collection.count_documents(query)
    cursor = tests_collection.find(query).limit(limit)
    tests = await cursor.to_list(limit)

    rows = []
    for test in tests:
        params = test.get("TestParametersFlat", {})
        rows.append({
            "id": str(test.get("_id", "")),
            "name": test.get("name", ""),
            "date": params.get("Date", ""),
            "customer": params.get("CUSTOMER", ""),
            "material": params.get("MATERIAL", ""),
            "test_type": params.get("TYPE_OF_TESTING_STR", ""),
            "machine": str(params.get("MACHINE_DATA", ""))[:50],
            "tester": params.get("TESTER", ""),
            "specimen_id": params.get("Specimen ID", ""),
            "standard": params.get("STANDARD", ""),
            "state": test.get("state", ""),
            "test_program": test.get("testProgramId", ""),
        })

    return {"total": total, "rows": rows}


async def get_available_metrics(test_ids: list[str]) -> dict:
    """Check what metrics/channels are available for a set of tests.
    Only returns metrics that have ACTUAL data in valuecolumns_migrated."""

    # Single batch query: find all distinct refIds that exist in valuecolumns_migrated
    pipeline = [
        {"$match": {"metadata.refId": {"$in": test_ids}}},
        {"$group": {"_id": "$metadata.refId"}},
    ]
    existing_refs = set()
    async for doc in values_collection.aggregate(pipeline):
        existing_refs.add(doc["_id"])

    tests_with_data = [tid for tid in test_ids if tid in existing_refs]
    tests_without_data = [tid for tid in test_ids if tid not in existing_refs]

    # Collect numeric parameters from TestParametersFlat (always available)
    numeric_params = {}
    all_param_values = {}  # key -> list of values across tests
    for test_id in test_ids[:20]:
        test = await tests_collection.find_one({"_id": test_id})
        if not test:
            continue
        params = test.get("TestParametersFlat", {})
        for key in ["SPECIMEN_WIDTH", "SPECIMEN_THICKNESS", "TEST_SPEED",
                     "Upper force limit", "Maximum extension", "Force shutdown threshold",
                     "Grip to grip separation at the start position",
                     "Marked initial gage length", "Cross-section input"]:
            val = params.get(key)
            if val is not None:
                try:
                    fval = float(val)
                    numeric_params[key] = fval
                    all_param_values.setdefault(key, []).append(fval)
                except (ValueError, TypeError):
                    pass

    # Only list named results if tests actually have value data
    named_results = set()
    if tests_with_data:
        for test_id in tests_with_data[:10]:
            test = await tests_collection.find_one({"_id": test_id})
            if not test:
                continue
            for vc in test.get("valueColumns", []):
                name = vc.get("name")
                vid = vc.get("_id", "")
                unit = vc.get("unitTableId", "")
                if name and not vid.endswith("_Key") and "_Value" in vid:
                    named_results.add(f"{name} ({unit.replace('Zwick.Unittable.', '')})")

    has_value_data = len(tests_with_data) > 0

    return {
        "tests_checked": len(test_ids),
        "tests_with_value_data": len(tests_with_data),
        "tests_without_value_data": len(tests_without_data),
        "has_value_data": has_value_data,
        "named_results": sorted(named_results) if has_value_data else [],
        "numeric_parameters": numeric_params,
        "parameter_values": {k: v for k, v in all_param_values.items() if len(v) > 1},
        "available_analysis": _suggest_analysis(has_value_data, named_results, numeric_params),
    }


def _suggest_analysis(has_time_series: bool, named_results: set, numeric_params: dict) -> list[str]:
    """Suggest what analysis is possible given the available data."""
    suggestions = []

    if numeric_params:
        suggestions.append("Parameter statistics (specimen dimensions, test speed, etc.)")

    # Check for specific named results
    result_names_lower = {r.lower() for r in named_results}
    has_force = any("force" in r for r in result_names_lower)
    has_stress = any("stress" in r or "yield" in r or "modulus" in r for r in result_names_lower)
    has_strain = any("strain" in r for r in result_names_lower)
    has_work = any("work" in r or "energy" in r for r in result_names_lower)

    if has_force:
        suggestions.append("Force analysis (maximum force, force at break)")
    if has_stress:
        suggestions.append("Stress analysis (tensile strength, yield point, Young's modulus)")
    if has_strain:
        suggestions.append("Strain analysis (strain at break, strain at max force)")
    if has_work:
        suggestions.append("Energy analysis (work up to break, work up to max force)")

    if has_time_series:
        suggestions.append("Time-series plots (stress-strain curves, force-displacement)")
    else:
        suggestions.append("WARNING: These tests have NO measurement data in valuecolumns_migrated. Only test parameters (SPECIMEN_WIDTH, SPECIMEN_THICKNESS, TEST_SPEED, etc.) can be analyzed. Suggest trying tests from a different customer/material that has data.")

    return suggestions


METRIC_ALIASES = {
    "tensile strength": "Maximum force",
    "ultimate tensile strength": "Maximum force",
    "uts": "Maximum force",
    "max force": "Maximum force",
    "yield strength": "Upper yield point",
    "yield point": "Upper yield point",
    "elongation at break": "Strain at break",
    "elongation": "Strain at break",
    "breaking force": "Result Force at break",
    "force at break": "Result Force at break",
    "stiffness": "Young's modulus",
    "elastic modulus": "Young's modulus",
    "e-modulus": "Young's modulus",
    "modulus of elasticity": "Young's modulus",
    "work to break": "Work up to break",
    "energy to break": "Work up to break",
    "duration": "Test duration",
}


async def get_result_values_for_tests(test_ids: list[str], result_name: str, unit_filter: str = "Stress") -> dict:
    """Extract a specific named result value across multiple tests.

    Looks in the valuecolumns_migrated collection for single-value results
    matching the given name and unit type.
    """
    if not result_name:
        return {"error": "result_name is required", "results": []}

    result_name = str(result_name)
    # Resolve common aliases to actual DB field names
    resolved = METRIC_ALIASES.get(result_name.lower())
    if resolved:
        result_name = resolved
    unit_filter = str(unit_filter) if unit_filter else "Force"

    results = []
    tests_without_data = 0

    for test_id in test_ids:
        test = await tests_collection.find_one({"_id": test_id})
        if not test:
            continue

        params = test.get("TestParametersFlat", {})
        found = False

        # Find matching value column IDs
        for vc in test.get("valueColumns", []):
            name = vc.get("name") or ""
            vid = vc.get("_id") or ""
            unit = vc.get("unitTableId") or ""

            # Exact match: "Young's modulus" should match "Young's modulus" but NOT "Young's modulus, begin"
            name_matches = (name.lower() == result_name.lower()
                           or (result_name.lower() in name.lower()
                               and len(name) - len(result_name) < 3))

            if (name_matches
                    and unit_filter.lower() in unit.lower()
                    and not vid.endswith("_Key")
                    and "_Value" in vid):

                # Extract the UUID part from the _id for regex matching
                # vid format: "{UUID}-Zwick.Unittable.Force_Value"
                uuid_part = vid.split("-Zwick")[0].strip("{}")

                # Look up the actual value in valuecolumns_migrated
                val_doc = await values_collection.find_one({
                    "metadata.refId": test_id,
                    "metadata.childId": {"$regex": uuid_part + ".*" + unit_filter}
                })

                if val_doc and val_doc.get("values"):
                    value = val_doc["values"][0] if len(val_doc["values"]) == 1 else val_doc["values"]
                    results.append({
                        "test_id": test_id,
                        "test_name": test.get("name", ""),
                        "result_name": name,
                        "unit": unit.replace("Zwick.Unittable.", ""),
                        "value": value,
                        "date": params.get("Date", ""),
                        "material": params.get("MATERIAL", ""),
                        "customer": params.get("CUSTOMER", ""),
                    })
                    found = True
                    break

        if not found:
            tests_without_data += 1

    return {
        "results": results,
        "found": len(results),
        "not_found": tests_without_data,
        "message": (
            f"Found {result_name} ({unit_filter}) for {len(results)}/{len(test_ids)} tests."
            + (f" {tests_without_data} tests have no value data in the database." if tests_without_data else "")
        ),
    }
