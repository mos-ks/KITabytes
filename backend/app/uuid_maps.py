"""Metadata about the ZwickRoell test data schema.

In the txp_clean database, TestParametersFlat keys are already human-readable.
This module documents the known fields and provides channel name resolution.
"""

# All known TestParametersFlat keys (from actual database)
TEST_PARAMETER_KEYS = [
    "APPLICATION_ENGINEER", "Bar length", "Begin of Young's modulus determination",
    "COMMENT", "CUSTOMER", "CUSTOMER_NAME", "Clock time",
    "Cross-section after break", "Cross-section correction factor", "Cross-section input",
    "Cross-section of the rings", "Date", "Date/Clock time",
    "Density of the specimen material", "Designation of the sub-series",
    "Designation sub-series 1", "Designation sub-series 2", "Designation sub-series 3",
    "Details about break", "Diameter", "Diameter 1 after break", "Diameter 2 after break",
    "Diameter of the rollers", "End of Young's modulus determination",
    "FINDINGS", "Fineness", "Force shutdown threshold",
    "GRIPS", "GRIPS_SPECIFICATION", "Gage length after break", "Gage length, fine strain",
    "Grip to grip separation at the start position", "Headline for the report",
    "Inner circumference", "Inner diameter", "JAWS", "JOB_NO", "LOAD_CELL",
    "Length of the reference beam", "MACHINE_DATA", "MACHINE_TYPE_STR",
    "MATERIAL", "MATERIAL_P", "Marked initial gage length",
    "Mass per unit area of the specimen", "Max. permissible force at end of test",
    "Maximum extension", "Mid span", "NOTE", "NOTES",
    "Negative cross-section correction value", "Optical assessment", "Outer diameter",
    "PRE_TREATMENT", "Parallel specimen length", "Part no.", "Removal",
    "SPECIMEN_REMOVAL", "SPECIMEN_THICKNESS", "SPECIMEN_TYPE", "SPECIMEN_WIDTH",
    "STANDARD", "Series designation", "Specimen ID", "Specimen designation",
    "Specimen thickness after break", "Specimen width after break",
    "Speed, Young's modulus", "Speed, point of load removal", "Speed, yield point",
    "Supply description", "TESTER", "TEST_SPEED", "TYPE", "TYPE_AND_DESTINATION",
    "TYPE_OF_TEST", "TYPE_OF_TESTING", "TYPE_OF_TESTING_STR",
    "Total length of the specimen", "Travel preset x1%", "Travel preset x2%",
    "Travel preset x3%", "Travel preset x4%", "Travel preset x5%", "Travel preset x6%",
    "Tube definition", "Tube length", "Type of Young's modulus determination",
    "Upper force limit", "Wall thickness", "Weight of the specimen", "Young's modulus preset",
]

# Key filterable fields
FILTERABLE_FIELDS = {
    "customer": "CUSTOMER",
    "material": "MATERIAL",
    "test_type": "TYPE_OF_TESTING_STR",
    "machine": "MACHINE_DATA",
    "tester": "TESTER",
    "standard": "STANDARD",
    "date": "Date",
}

# Known channel UUIDs in valueColumns (from the _tests.valueColumns entries)
CHANNEL_NAMES = {
    "E4C21909": "Strain / Deformation",
    "F4640D35": "Strain (plastic)",
    "E5F23924": "Standard force",
    "2C840DA7": "Standard travel",
    "3BCEDF86": "Crosshead travel",
    "740A4C83": "Standard load cell",
    "289C9C84": "Standard extensometer",
    "04A31CB5": "System time",
    "A2CA0D5E": "Fine strain",
    "CBE74C00": "Nominal strain",
    "B58A6F2B": "Grip to grip separation",
    "C2058AF2": "Work",
    "110A8DC1": "Temperature",
}

# Unit table types
UNIT_TABLES = {
    "Zwick.Unittable.Displacement": "Displacement (mm)",
    "Zwick.Unittable.Force": "Force (N)",
    "Zwick.Unittable.Stress": "Stress (MPa)",
    "Zwick.Unittable.Ratio": "Ratio (%)",
    "Zwick.Unittable.Energy": "Energy (J)",
    "Zwick.Unittable.Time": "Time (s)",
    "Zwick.Unittable.Area": "Area (mm²)",
}


def resolve_channel_from_child_id(child_id: str) -> dict:
    """Parse a childId to extract channel name and unit info."""
    for uuid_prefix, name in CHANNEL_NAMES.items():
        if uuid_prefix in child_id:
            # Extract unit table
            unit = "unknown"
            for ut_key, ut_name in UNIT_TABLES.items():
                if ut_key in child_id:
                    unit = ut_name
                    break
            return {"name": name, "unit": unit}
    return {"name": child_id, "unit": "unknown"}
