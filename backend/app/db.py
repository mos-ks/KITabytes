"""MongoDB connection and database access."""

from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

# Async client (for request handling)
async_client = AsyncIOMotorClient(settings.MONGO_URI, tlsAllowInvalidCertificates=True)
db = async_client[settings.MONGO_DB]

# Collections - actual names in txp_clean database
tests_collection = db["_tests"]
values_collection = db["valuecolumns_migrated"]
unittables_collection = db["unittables_new"]
translations_collection = db["translations"]


async def get_database_overview():
    """Get a summary of what's in the database."""
    test_count = await tests_collection.count_documents({})

    pipeline = [
        {"$group": {
            "_id": None,
            "customers": {"$addToSet": "$TestParametersFlat.CUSTOMER"},
            "materials": {"$addToSet": "$TestParametersFlat.MATERIAL"},
            "test_types": {"$addToSet": "$TestParametersFlat.TYPE_OF_TESTING_STR"},
            "machines": {"$addToSet": "$TestParametersFlat.MACHINE_DATA"},
            "standards": {"$addToSet": "$TestParametersFlat.STANDARD"},
            "testers": {"$addToSet": "$TestParametersFlat.TESTER"},
            "test_programs": {"$addToSet": "$testProgramId"},
        }}
    ]
    result = await tests_collection.aggregate(pipeline).to_list(1)

    if not result:
        return {"test_count": 0}

    data = result[0]
    clean = lambda lst: sorted([x for x in (lst or []) if x is not None and str(x).strip()])

    return {
        "test_count": test_count,
        "customers": clean(data.get("customers")),
        "materials": clean(data.get("materials")),
        "test_types": clean(data.get("test_types")),
        "machines": clean(data.get("machines"))[:20],  # Limit - can be very long
        "standards": clean(data.get("standards"))[:20],
        "testers": clean(data.get("testers")),
        "test_programs": clean(data.get("test_programs")),
    }
