"""Data API routes for direct data access."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from app.services.data_service import query_tests, get_test_by_id, get_values_for_test, get_summary_table
from app.services.stats_service import descriptive_stats, compare_groups, trend_analysis, detect_outliers
from app.db import tests_collection

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/tests")
async def list_tests(
    customer: Optional[str] = Query(None),
    material: Optional[str] = Query(None),
    test_type: Optional[str] = Query(None),
    machine: Optional[str] = Query(None),
    tester: Optional[str] = Query(None),
    standard: Optional[str] = Query(None),
    site: Optional[str] = Query(None),
    limit: int = Query(50, le=500),
    skip: int = Query(0),
):
    """Query tests with filters."""
    try:
        return await query_tests(
            customer=customer, material=material, test_type=test_type,
            machine=machine, tester=tester, standard=standard,
            limit=limit, skip=skip,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tests/{test_id}")
async def get_test(test_id: str):
    """Get a single test by ID."""
    test = await get_test_by_id(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    return test


@router.get("/tests/{test_id}/values")
async def get_test_values(test_id: str):
    """Get measurement values for a test."""
    try:
        return await get_values_for_test(test_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def summary_table(
    customer: Optional[str] = Query(None),
    material: Optional[str] = Query(None),
    test_type: Optional[str] = Query(None),
    machine: Optional[str] = Query(None),
    tester: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
):
    """Get a summary table for data preview."""
    try:
        return await get_summary_table(
            customer=customer, material=material, test_type=test_type,
            machine=machine, tester=tester, limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AllIdsRequest(BaseModel):
    customer: Optional[str] = None
    material: Optional[str] = None
    test_type: Optional[str] = None


@router.post("/all-ids")
async def get_all_ids(req: AllIdsRequest):
    """Get ALL test IDs matching the given filters (no limit)."""
    from app.services.data_service import _build_filter
    try:
        query = _build_filter(customer=req.customer, material=req.material, test_type=req.test_type)
        cursor = tests_collection.find(query, {"_id": 1})
        ids = []
        async for doc in cursor:
            ids.append(str(doc["_id"]))
        return {"test_ids": ids, "total": len(ids)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CheckUpdatesRequest(BaseModel):
    known_test_ids: list[str] = []
    material: Optional[str] = None
    test_type: Optional[str] = None
    customer: Optional[str] = None


@router.post("/check-updates")
async def check_updates(req: CheckUpdatesRequest):
    """Check if new tests exist that match the same filters but aren't in the known set."""
    try:
        query = {}
        if req.material:
            query["TestParametersFlat.MATERIAL"] = {"$regex": req.material, "$options": "i"}
        if req.test_type:
            query["TestParametersFlat.TYPE_OF_TESTING_STR"] = {"$regex": req.test_type, "$options": "i"}
        if req.customer:
            query["TestParametersFlat.CUSTOMER"] = {"$regex": req.customer, "$options": "i"}

        current_count = await tests_collection.count_documents(query)
        known_count = len(req.known_test_ids)
        new_count = max(0, current_count - known_count)

        # Get the new test IDs if any
        new_tests = []
        if new_count > 0 and req.known_test_ids:
            cursor = tests_collection.find(
                {**query, "_id": {"$nin": req.known_test_ids}},
                {"_id": 1, "name": 1, "TestParametersFlat.Date": 1}
            ).limit(50)
            async for doc in cursor:
                new_tests.append({
                    "id": doc["_id"],
                    "name": doc.get("name", ""),
                    "date": doc.get("TestParametersFlat", {}).get("Date", ""),
                })

        return {
            "current_total": current_count,
            "known_count": known_count,
            "new_count": new_count,
            "new_tests": new_tests,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
