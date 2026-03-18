# Database Structure: txp_clean

## Collections

| Collection | Documents | Description |
|---|---|---|
| `_tests` | 31,099 | Test metadata + parameter definitions |
| `valuecolumns_migrated` | 214,889 | Actual numeric values (time-series + single results) |
| `unittables_new` | 126 | Unit definitions (mm, N, MPa, etc.) |
| `translations` | 5,817,780 | i18n translations for field names |

## Key Fact: Only 2,422 of 31,099 tests have value data in `valuecolumns_migrated`

---

## `_tests` Collection

### Top-level fields
```
_id                          → UUID string e.g. "{D1CB87C7-D89F-4583-9DA8-5372DC59F25A}"
clientAppType                → "testXpert III"
state                        → "finishedOK"
tags                         → array of UUIDs
version                      → e.g. "2.1772195387.0"
testProgramId                → e.g. "TestProgram_2"
testProgramVersion           → version string
name                         → specimen name e.g. "01", "z4"
modifiedOn                   → date object
hasMachineConfigurationInfo  → boolean
TestParametersFlat           → object with all test parameters (human-readable keys)
valueColumns                 → array of channel/result definitions (schema only, no values)
```

### TestParametersFlat (92 possible keys, all human-readable)

**Key filterable fields:**
- `CUSTOMER` → e.g. "Company_1" (226 distinct)
- `MATERIAL` → e.g. "Aluminium", "Steel" (72 distinct)
- `TYPE_OF_TESTING_STR` → "tensile", "compression", "flexure" (3 values)
- `MACHINE_DATA` → machine description (187 distinct)
- `TESTER` → e.g. "Tester_1" (122 distinct)
- `STANDARD` → testing standard (250 distinct)
- `Date` → e.g. "22.10.2025" (DD.MM.YYYY format)
- `MACHINE_TYPE_STR` → "Static" (only value)

**Specimen parameters:**
- `SPECIMEN_WIDTH`, `SPECIMEN_THICKNESS` → numeric (meters)
- `Specimen ID`, `Specimen designation`
- `Cross-section input`, `Parallel specimen length`
- `Marked initial gage length`, `Total length of the specimen`
- `Diameter`, `Inner diameter`, `Outer diameter`, `Wall thickness`
- `Density of the specimen material`, `Weight of the specimen`

**Test configuration:**
- `TEST_SPEED` → numeric (m/s)
- `Upper force limit`, `Maximum extension`, `Force shutdown threshold`
- `Begin of Young's modulus determination`, `End of Young's modulus determination`
- `Type of Young's modulus determination`
- `Speed, Young's modulus`, `Speed, yield point`, `Speed, point of load removal`

**Other:**
- `CUSTOMER_NAME`, `APPLICATION_ENGINEER`, `JOB_NO`
- `COMMENT`, `NOTES`, `NOTE`, `FINDINGS`
- `GRIPS`, `GRIPS_SPECIFICATION`, `JAWS`, `LOAD_CELL`
- `PRE_TREATMENT`, `SPECIMEN_TYPE`, `SPECIMEN_REMOVAL`

### valueColumns array (schema definitions, NOT actual values)

Each test has a `valueColumns` array defining available channels and results.
Each entry has:
```
_id          → "{UUID}-UnitTable_Key" or "{UUID}-UnitTable_Value"
name         → human-readable name (e.g. "Maximum force", "Strain / Deformation")
unitTableId  → unit type (e.g. "Zwick.Unittable.Force", "Zwick.Unittable.Stress")
valueTableId → reference identifier
segments     → optional, marks valid data ranges (fromKey, toKey)
```

**Important:** `_Key` entries are index arrays. `_Value` entries are the actual measurement data.
The same result appears in multiple units (Force, Stress, ForcePerDisplacement, ForcePerTiter).

**Named results found in tests:**
- Maximum force (Force, Stress)
- Result Force at break (Force, Stress)
- Young's modulus (Stress, ForcePerDisplacement)
- Upper yield point (Force, Stress)
- Upper yield point without hysteresis (Force, Stress)
- Strain at break (Displacement, Ratio)
- Strain at maximum force (Displacement, Ratio)
- Nominal strain at break (Displacement, Ratio)
- Nominal strain at maximum force (Displacement, Ratio)
- Work up to break (Energy)
- Work up to maximum force (Energy)
- Test duration (Time)
- Point of break (Displacement)
- Result Crosssection (Area)

**Time-series channels:**
- Standard force (Force, Stress)
- Standard travel (Displacement, Ratio)
- Strain / Deformation (Displacement, Ratio)
- Fine strain (Displacement, Ratio)
- Nominal strain (Displacement, Ratio)
- Strain (plastic) (Displacement, Ratio)
- Grip to grip separation (Displacement)
- Work (Energy)
- Temperature, Temperature 2, Temperature 3 (TemperatureV2)
- Test time (Time)

---

## `valuecolumns_migrated` Collection

### Document structure
```
_id          → ObjectId
fileId       → GridFS reference string
filename     → URL-encoded identifier: %7BtestId%7D-version-%7BchannelUUID%7D-UnitTable.channelId-UnitTable_Value
uploadDate   → date
bufferLength → byte count
values       → array of floats (THE ACTUAL DATA)
valuesCount  → number of values
metadata:
  refId      → test _id (e.g. "{D1CB87C7-D89F-4583-9DA8-5372DC59F25A}")
  rootVersion → version string
  childId    → channel identifier linking to test.valueColumns._id format
               e.g. "{E4C21909-...}-Zwick.Unittable.Displacement.{E4C21909-...}-Zwick.Unittable.Displacement_Value"
```

### How to link values to tests

1. `metadata.refId` = `_tests._id` (the test this value belongs to)
2. `metadata.childId` contains the channel UUID and unit table
3. Match channel UUID from childId to `_tests.valueColumns[]._id` to get the channel name

### Value types

| Type | valuesCount | Description |
|---|---|---|
| Single-value results | 1 | Computed results like Maximum force, Young's modulus |
| Time-series | 10,000-50,000+ | Continuous measurements (force, strain, displacement over time) |

### Distribution (sample of 500 docs)
- Single value (result): 403
- Large (10k+, time-series): 97

---

## `unittables_new` Collection

Maps unit table IDs to actual units:
```
Zwick.Unittable.Force          → N, kN
Zwick.Unittable.Stress         → MPa, N/mm²
Zwick.Unittable.Displacement   → mm, µm
Zwick.Unittable.Ratio          → %, mm/mm
Zwick.Unittable.Energy         → J, mJ
Zwick.Unittable.Time           → s, min
Zwick.Unittable.Area           → mm²
Zwick.Unittable.ForcePerDisplacement → N/mm
Zwick.Unittable.ForcePerTiter  → cN/tex
Zwick.Unittable.TemperatureV2  → °C
Zwick.Unittable.Deformation    → mm
```

---

## `translations` Collection

5.8M translation entries for UI labels. Key format:
```
_id: "{channelUUID}-UnitTable_Value.name"
en: English name (often "N/A")
de: German name (e.g. "Dehnung_Value")
```

---

## Query Patterns

### Find tests by filter
```python
db._tests.find({"TestParametersFlat.MATERIAL": {"$regex": "Aluminium", "$options": "i"}})
```

### Get value data for a test
```python
db.valuecolumns_migrated.find({"metadata.refId": "{test-uuid}"})
```

### Get a specific result (e.g. Maximum force in N) for a test
```python
# 1. Find the _Value entry in test.valueColumns with name="Maximum force" and unitTableId containing "Force"
# 2. Extract its _id (e.g. "{9DB9C049-...}-Zwick.Unittable.Force_Value")
# 3. Query: db.valuecolumns_migrated.find_one({"metadata.refId": test_id, "metadata.childId": {"$regex": "9DB9C049.*Force_Value"}})
# 4. Result: doc.values = [81127.859375]  (single float)
```

### Get time-series (e.g. force vs displacement curve)
```python
# Find Standard force channel values
force_doc = db.valuecolumns_migrated.find_one({
    "metadata.refId": test_id,
    "metadata.childId": {"$regex": "E5F23924.*Force_Value"}  # Standard force UUID
})
# Find Standard travel channel values
travel_doc = db.valuecolumns_migrated.find_one({
    "metadata.refId": test_id,
    "metadata.childId": {"$regex": "2C840DA7.*Displacement_Value"}  # Standard travel UUID
})
# Plot: force_doc.values vs travel_doc.values
```
