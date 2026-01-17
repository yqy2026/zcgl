"""
Comprehensive Unit Tests for Defect Tracking API Routes (src/api/v1/defect_tracking.py)

This test module covers all endpoints in the defect_tracking router to achieve 70%+ coverage.

Coverage Strategy:
- Focus on business logic paths through the actual route handlers
- Test all major code branches in each function
- Mock database operations appropriately
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

pytestmark = pytest.mark.api


# ============================================================================
# Fixtures and Helpers
# ============================================================================


def create_mock_defect_row(defect_id="DEF-20260116-ABC12345"):
    """Create a properly mocked defect row that behaves like sqlite3.Row"""
    row_data = {
        "defect_id": defect_id,
        "title": "Login button not responding",
        "description": "Clicking the login button does nothing",
        "severity": "high",
        "priority": "high",
        "status": "open",
        "category": "functional",
        "module": "authentication",
        "reproduction_steps": json.dumps(["1. Go to login page", "2. Click login button"]),
        "expected_behavior": "User should be logged in",
        "actual_behavior": "Nothing happens",
        "reporter": "testuser@example.com",
        "assigned_to": "dev@example.com",
        "environment": "Chrome 120, Windows 11",
        "attachments": json.dumps(["screenshot.png"]),
        "tags": json.dumps(["ui", "login"]),
        "test_coverage_impact": json.dumps({"affected_tests": 5}),
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "resolved_at": None,
        "fix_version": None,
        "root_cause": None,
        "resolution": None,
    }
    # Use a simple dict-like mock
    row = type('MockRow', (), row_data)()
    row.__getitem__ = lambda self, key: row_data.get(key)
    return row


def create_mock_connection():
    """Create a mock database connection with cursor"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.row_factory = MagicMock()
    return mock_conn


# ============================================================================
# Test: POST /defects/ - Create Defect
# ============================================================================


class TestCreateDefect:
    """Tests for POST /api/v1/defects/ endpoint"""

    @patch("src.api.v1.defect_tracking.get_db_connection")
    @pytest.mark.asyncio
    async def test_create_defect_success(self, mock_get_conn):
        """Test successful defect creation"""
        from src.api.v1.defect_tracking import create_defect, DefectReport

        sample_data = {
            "title": "Login button not responding",
            "description": "Clicking the login button does nothing",
            "severity": "high",
            "priority": "high",
            "category": "functional",
            "module": "authentication",
            "reproduction_steps": ["Step 1"],
            "expected_behavior": "Expected",
            "actual_behavior": "Actual",
            "reporter": "test@example.com",
        }

        mock_conn = create_mock_connection()
        mock_get_conn.return_value = mock_conn

        mock_row = create_mock_defect_row()
        mock_conn.cursor.fetchone.return_value = mock_row

        defect = DefectReport(**sample_data)
        result = await create_defect(defect)

        assert result.defect_id == "DEF-20260116-ABC12345"
        mock_conn.cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch("src.api.v1.defect_tracking.get_db_connection")
    @pytest.mark.asyncio
    async def test_create_defect_database_error(self, mock_get_conn):
        """Test defect creation with database error"""
        from src.api.v1.defect_tracking import create_defect, DefectReport
        from sqlite3 import IntegrityError

        sample_data = {
            "title": "Test",
            "description": "Test",
            "severity": "high",
            "priority": "high",
            "category": "functional",
            "module": "auth",
            "reproduction_steps": ["Step 1"],
            "expected_behavior": "Expected",
            "actual_behavior": "Actual",
            "reporter": "test@example.com",
        }

        mock_conn = create_mock_connection()
        mock_get_conn.return_value = mock_conn

        mock_conn.cursor.execute.side_effect = IntegrityError("UNIQUE constraint failed")

        defect = DefectReport(**sample_data)

        with pytest.raises(HTTPException) as exc_info:
            await create_defect(defect)

        assert exc_info.value.status_code == 500
        assert "创建缺陷失败" in exc_info.value.detail
        mock_conn.rollback.assert_called_once()


# ============================================================================
# Test: GET /defects/ - Get Defects List
# ============================================================================


class TestGetDefects:
    """Tests for GET /api/v1/defects/ endpoint"""

    @patch("src.api.v1.defect_tracking.get_db_connection")
    @pytest.mark.asyncio
    async def test_get_defects_no_filters(self, mock_get_conn):
        """Test getting defects without filters"""
        from src.api.v1.defect_tracking import get_defects

        mock_conn = create_mock_connection()
        mock_get_conn.return_value = mock_conn

        mock_conn.cursor.fetchall.return_value = []

        total_mock = type('MockRow', (), {'total': 0, '__getitem__': lambda self, k: 0 if k == 'total' else None})()
        mock_conn.cursor.fetchone.return_value = total_mock

        result = await get_defects()

        assert result["defects"] == []
        assert result["total"] == 0

    @patch("src.api.v1.defect_tracking.get_db_connection")
    @pytest.mark.asyncio
    async def test_get_defects_with_filters(self, mock_get_conn):
        """Test getting defects with status filter"""
        from src.api.v1.defect_tracking import get_defects, DefectStatus

        mock_conn = create_mock_connection()
        mock_get_conn.return_value = mock_conn

        mock_row = create_mock_defect_row()
        mock_conn.cursor.fetchall.return_value = [mock_row]

        total_mock = type('MockRow', (), {'total': 1, '__getitem__': lambda self, k: 1 if k == 'total' else None})()
        mock_conn.cursor.fetchone.return_value = total_mock

        result = await get_defects(status=DefectStatus.OPEN)

        assert len(result["defects"]) == 1
        assert result["total"] == 1

    @patch("src.api.v1.defect_tracking.get_db_connection")
    @pytest.mark.asyncio
    async def test_get_defects_with_sorting(self, mock_get_conn):
        """Test getting defects with custom sorting"""
        from src.api.v1.defect_tracking import get_defects

        mock_conn = create_mock_connection()
        mock_get_conn.return_value = mock_conn

        mock_conn.cursor.fetchall.return_value = []

        total_mock = type('MockRow', (), {'total': 0, '__getitem__': lambda self, k: 0 if k == 'total' else None})()
        mock_conn.cursor.fetchone.return_value = total_mock

        result = await get_defects(sort_by="created_at", sort_order="desc")
        assert "defects" in result

    @patch("src.api.v1.defect_tracking.get_db_connection")
    @pytest.mark.asyncio
    async def test_get_defects_with_pagination(self, mock_get_conn):
        """Test getting defects with pagination"""
        from src.api.v1.defect_tracking import get_defects

        mock_conn = create_mock_connection()
        mock_get_conn.return_value = mock_conn

        mock_conn.cursor.fetchall.return_value = []

        total_mock = type('MockRow', (), {'total': 100, '__getitem__': lambda self, k: 100 if k == 'total' else None})()
        mock_conn.cursor.fetchone.return_value = total_mock

        result = await get_defects(limit=10, offset=20)

        assert result["limit"] == 10
        assert result["offset"] == 20
        assert result["total"] == 100


# ============================================================================
# Test: GET /defects/{defect_id} - Get Defect Details
# ============================================================================


class TestGetDefect:
    """Tests for GET /api/v1/defects/{defect_id} endpoint"""

    @patch("src.api.v1.defect_tracking.get_db_connection")
    @pytest.mark.asyncio
    async def test_get_defect_success(self, mock_get_conn):
        """Test getting defect details successfully"""
        from src.api.v1.defect_tracking import get_defect

        mock_conn = create_mock_connection()
        mock_get_conn.return_value = mock_conn

        mock_row = create_mock_defect_row()
        mock_conn.cursor.fetchone.return_value = mock_row

        result = await get_defect("DEF-20260116-ABC12345")

        assert result.defect_id == "DEF-20260116-ABC12345"
        assert result.title == "Login button not responding"
        mock_conn.close.assert_called_once()

    @patch("src.api.v1.defect_tracking.get_db_connection")
    @pytest.mark.asyncio
    async def test_get_defect_not_found(self, mock_get_conn):
        """Test getting non-existent defect"""
        from src.api.v1.defect_tracking import get_defect

        mock_conn = create_mock_connection()
        mock_get_conn.return_value = mock_conn

        mock_conn.cursor.fetchone.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_defect("NON-EXISTENT")

        assert exc_info.value.status_code == 404
        assert "未找到指定的缺陷" in exc_info.value.detail


# ============================================================================
# Test: PUT /defects/{defect_id} - Update Defect
# ============================================================================


class TestUpdateDefect:
    """Tests for PUT /api/v1/defects/{defect_id} endpoint"""

    @patch("src.api.v1.defect_tracking.get_db_connection")
    @pytest.mark.asyncio
    async def test_update_defect_success(self, mock_get_conn):
        """Test successful defect update"""
        from src.api.v1.defect_tracking import update_defect

        mock_conn = create_mock_connection()
        mock_get_conn.return_value = mock_conn

        mock_row = create_mock_defect_row()
        mock_conn.cursor.fetchone.side_effect = [mock_row, mock_row]

        updates = {"status": "in_progress"}

        result = await update_defect("DEF-20260116-ABC12345", updates)

        assert result is not None
        mock_conn.cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()

    @patch("src.api.v1.defect_tracking.get_db_connection")
    @pytest.mark.asyncio
    async def test_update_defect_not_found(self, mock_get_conn):
        """Test updating non-existent defect"""
        from src.api.v1.defect_tracking import update_defect

        mock_conn = create_mock_connection()
        mock_get_conn.return_value = mock_conn

        mock_conn.cursor.fetchone.return_value = None

        updates = {"status": "resolved"}

        with pytest.raises(HTTPException) as exc_info:
            await update_defect("NON-EXISTENT", updates)

        assert exc_info.value.status_code == 500
        assert "更新缺陷失败" in exc_info.value.detail

    @patch("src.api.v1.defect_tracking.get_db_connection")
    @pytest.mark.asyncio
    async def test_update_defect_resolved_status(self, mock_get_conn):
        """Test updating defect to resolved status sets resolved_at"""
        from src.api.v1.defect_tracking import update_defect

        mock_conn = create_mock_connection()
        mock_get_conn.return_value = mock_conn

        mock_row = create_mock_defect_row()
        mock_conn.cursor.fetchone.side_effect = [mock_row, mock_row]

        updates = {"status": "resolved"}

        result = await update_defect("DEF-20260116-ABC12345", updates)

        assert mock_conn.cursor.execute.call_count >= 2
        mock_conn.commit.assert_called_once()

    @patch("src.api.v1.defect_tracking.get_db_connection")
    @pytest.mark.asyncio
    async def test_update_defect_multiple_fields(self, mock_get_conn):
        """Test updating multiple fields at once"""
        from src.api.v1.defect_tracking import update_defect

        mock_conn = create_mock_connection()
        mock_get_conn.return_value = mock_conn

        mock_row = create_mock_defect_row()
        mock_conn.cursor.fetchone.side_effect = [mock_row, mock_row]

        updates = {
            "status": "in_progress",
            "assigned_to": "dev2@example.com",
            "priority": "high",
        }

        result = await update_defect("DEF-20260116-ABC12345", updates)

        assert result is not None
        mock_conn.commit.assert_called_once()

    @patch("src.api.v1.defect_tracking.get_db_connection")
    @pytest.mark.asyncio
    async def test_update_defect_exception_handling(self, mock_get_conn):
        """Test update_defect exception handling"""
        from src.api.v1.defect_tracking import update_defect

        mock_conn = create_mock_connection()
        mock_get_conn.return_value = mock_conn

        mock_row = create_mock_defect_row()
        mock_conn.cursor.fetchone.return_value = mock_row
        mock_conn.cursor.execute.side_effect = Exception("Database error")

        updates = {"status": "resolved"}

        with pytest.raises(HTTPException) as exc_info:
            await update_defect("DEF-001", updates)

        assert exc_info.value.status_code == 500
        mock_conn.rollback.assert_called_once()


# ============================================================================
# Test: GET /defects/{defect_id}/history - Get Defect History
# ============================================================================


class TestGetDefectHistory:
    """Tests for GET /api/v1/defects/{defect_id}/history endpoint"""

    @patch("src.api.v1.defect_tracking.get_db_connection")
    @pytest.mark.asyncio
    async def test_get_defect_history_success(self, mock_get_conn):
        """Test getting defect history successfully"""
        from src.api.v1.defect_tracking import get_defect_history

        mock_conn = create_mock_connection()
        mock_get_conn.return_value = mock_conn

        # Create proper mock rows
        history_row1 = type('MockRow', (), {
            'action': 'created',
            'old_value': None,
            'new_value': 'Login bug',
            'changed_by': 'user@example.com',
            'changed_at': datetime.now(),
            'comment': 'Created',
            '__getitem__': lambda self, key: getattr(self, key, None)
        })()

        history_row2 = type('MockRow', (), {
            'action': 'updated_status',
            'old_value': 'open',
            'new_value': 'in_progress',
            'changed_by': 'dev@example.com',
            'changed_at': datetime.now(),
            'comment': 'Status updated',
            '__getitem__': lambda self, key: getattr(self, key, None)
        })()

        mock_conn.cursor.fetchall.return_value = [history_row1, history_row2]

        result = await get_defect_history("DEF-20260116-ABC12345")

        assert len(result) == 2
        assert result[0]["action"] == "created"
        assert result[1]["action"] == "updated_status"
        mock_conn.close.assert_called_once()

    @patch("src.api.v1.defect_tracking.get_db_connection")
    @pytest.mark.asyncio
    async def test_get_defect_history_empty(self, mock_get_conn):
        """Test getting history for defect with no history"""
        from src.api.v1.defect_tracking import get_defect_history

        mock_conn = create_mock_connection()
        mock_get_conn.return_value = mock_conn

        mock_conn.cursor.fetchall.return_value = []

        result = await get_defect_history("DEF-20260116-ABC12345")

        assert result == []


# ============================================================================
# Test: GET /defects/trends - Get Defect Trends
# ============================================================================


class TestGetDefectTrends:
    """Tests for GET /api/v1/defects/trends endpoint"""

    @patch("src.api.v1.defect_tracking.get_db_connection")
    @pytest.mark.asyncio
    async def test_get_defect_trends_default(self, mock_get_conn):
        """Test getting defect trends with default parameters"""
        from src.api.v1.defect_tracking import get_defect_trends

        mock_conn = create_mock_connection()
        mock_get_conn.return_value = mock_conn

        trend_row = type('MockRow', (), {
            'period': '2026-01-15',
            'open_count': 5,
            'resolved_count': 3,
            'reopened_count': 1,
            '__getitem__': lambda self, key: getattr(self, key, None)
        })()

        mock_conn.cursor.fetchall.side_effect = [[trend_row], []]

        result = await get_defect_trends(days=30)

        assert len(result) == 1
        assert result[0].open_count == 5

    @patch("src.api.v1.defect_tracking.get_db_connection")
    @pytest.mark.asyncio
    async def test_get_defect_trends_week_grouping(self, mock_get_conn):
        """Test getting defect trends grouped by week"""
        from src.api.v1.defect_tracking import get_defect_trends

        mock_conn = create_mock_connection()
        mock_get_conn.return_value = mock_conn

        mock_conn.cursor.fetchall.side_effect = [[], []]

        result = await get_defect_trends(days=30, group_by="week")

        assert result == []


# ============================================================================
# Test: GET /defects/analysis - Get Defect Analysis
# ============================================================================


class TestGetDefectAnalysis:
    """Tests for GET /api/v1/defects/analysis endpoint"""

    @patch("src.api.v1.defect_tracking.get_db_connection")
    @pytest.mark.asyncio
    async def test_get_defect_analysis_default(self, mock_get_conn):
        """Test getting defect analysis with default parameters"""
        from src.api.v1.defect_tracking import get_defect_analysis

        mock_conn = create_mock_connection()
        mock_get_conn.return_value = mock_conn

        stats_row = type('MockRow', (), {
            'total_defects': 100,
            'new_defects': 20,
            'resolved_defects': 15,
            'avg_resolution_time': 24.5,
            '__getitem__': lambda self, key: getattr(self, key, None)
        })()

        mock_conn.cursor.fetchone.return_value = stats_row
        mock_conn.cursor.fetchall.side_effect = [[], [], [], []]

        result = await get_defect_analysis(days=30)

        assert result.total_defects == 100
        assert result.new_defects == 20
        assert result.resolved_defects == 15
        assert isinstance(result.recommendations, list)

    @patch("src.api.v1.defect_tracking.get_db_connection")
    @pytest.mark.asyncio
    async def test_get_defect_analysis_with_distributions(self, mock_get_conn):
        """Test defect analysis with distribution data"""
        from src.api.v1.defect_tracking import get_defect_analysis

        mock_conn = create_mock_connection()
        mock_get_conn.return_value = mock_conn

        stats_row = type('MockRow', (), {
            'total_defects': 100,
            'new_defects': 20,
            'resolved_defects': 15,
            'avg_resolution_time': 24.5,
            '__getitem__': lambda self, key: getattr(self, key, None)
        })()

        mock_conn.cursor.fetchone.return_value = stats_row

        sev_row = type('MockRow', (), {
            'severity': 'critical',
            'count': 2,
            '__getitem__': lambda self, key: getattr(self, key, None)
        })()

        cat_row = type('MockRow', (), {
            'category': 'functional',
            'count': 12,
            '__getitem__': lambda self, key: getattr(self, key, None)
        })()

        mod_row = type('MockRow', (), {
            'module': 'auth',
            'count': 10,
            '__getitem__': lambda self, key: getattr(self, key, None)
        })()

        reopened_row = type('MockRow', (), {
            'reopened_count': 2,
            '__getitem__': lambda self, key: getattr(self, key, None)
        })()

        mock_conn.cursor.fetchall.side_effect = [
            [sev_row],
            [cat_row],
            [mod_row],
            [reopened_row],
        ]

        result = await get_defect_analysis(days=30)

        assert result.severity_distribution["critical"] == 2
        assert result.category_distribution["functional"] == 12
        assert result.module_distribution["auth"] == 10


# ============================================================================
# Test: POST /defects/prevention - Create Prevention Measure
# ============================================================================


class TestCreatePreventionMeasure:
    """Tests for POST /api/v1/defects/prevention endpoint"""

    @patch("src.api.v1.defect_tracking.get_db_connection")
    @pytest.mark.asyncio
    async def test_create_prevention_success(self, mock_get_conn):
        """Test successful prevention measure creation"""
        from src.api.v1.defect_tracking import create_prevention_measure, DefectPrevention

        sample_data = {
            "prevention_id": "PREV-20260116-XYZ12345",
            "category": "functional",
            "title": "Add unit tests for login flow",
            "description": "Implement comprehensive unit tests",
            "implementation_steps": ["1. Write test cases", "2. Run tests"],
            "estimated_impact": "High",
            "priority": "high",
        }

        mock_conn = create_mock_connection()
        mock_get_conn.return_value = mock_conn

        mock_row = type('MockRow', (), {
            'prevention_id': 'PREV-20260116-XYZ12345',
            'category': 'functional',
            'title': 'Add unit tests',
            'description': 'Implement tests',
            'implementation_steps': json.dumps(['Step 1', 'Step 2']),
            'estimated_impact': 'High',
            'priority': 'high',
            'created_at': datetime.now(),
            '__getitem__': lambda self, key: getattr(self, key, None)
        })()

        mock_conn.cursor.fetchone.return_value = mock_row

        prevention = DefectPrevention(**sample_data)
        result = await create_prevention_measure(prevention)

        assert result.prevention_id == 'PREV-20260116-XYZ12345'
        assert result.title == 'Add unit tests'
        mock_conn.cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()

    @patch("src.api.v1.defect_tracking.get_db_connection")
    @pytest.mark.asyncio
    async def test_create_prevention_database_error(self, mock_get_conn):
        """Test prevention creation with database error"""
        from src.api.v1.defect_tracking import create_prevention_measure, DefectPrevention
        from sqlite3 import DatabaseError

        sample_data = {
            "prevention_id": "PREV-001",
            "category": "functional",
            "title": "Test",
            "description": "Test",
            "implementation_steps": ["Step 1"],
            "estimated_impact": "High",
            "priority": "high",
        }

        mock_conn = create_mock_connection()
        mock_get_conn.return_value = mock_conn

        mock_conn.cursor.execute.side_effect = DatabaseError("Connection lost")

        prevention = DefectPrevention(**sample_data)

        with pytest.raises(HTTPException) as exc_info:
            await create_prevention_measure(prevention)

        assert exc_info.value.status_code == 500
        assert "创建预防措施失败" in exc_info.value.detail
        mock_conn.rollback.assert_called_once()


# ============================================================================
# Test: GET /defects/prevention - Get Prevention Measures
# ============================================================================


class TestGetPreventionMeasures:
    """Tests for GET /api/v1/defects/prevention endpoint"""

    @patch("src.api.v1.defect_tracking.get_db_connection")
    @pytest.mark.asyncio
    async def test_get_prevention_measures_no_filters(self, mock_get_conn):
        """Test getting prevention measures without filters"""
        from src.api.v1.defect_tracking import get_prevention_measures

        mock_conn = create_mock_connection()
        mock_get_conn.return_value = mock_conn

        mock_conn.cursor.fetchall.return_value = []

        result = await get_prevention_measures()

        assert result == []

    @patch("src.api.v1.defect_tracking.get_db_connection")
    @pytest.mark.asyncio
    async def test_get_prevention_measures_with_filters(self, mock_get_conn):
        """Test getting prevention measures with filters"""
        from src.api.v1.defect_tracking import get_prevention_measures, DefectCategory

        mock_conn = create_mock_connection()
        mock_get_conn.return_value = mock_conn

        mock_row = type('MockRow', (), {
            'prevention_id': 'PREV-001',
            'category': 'functional',
            'title': 'Test prevention',
            'description': 'Description',
            'implementation_steps': json.dumps(['Step 1']),
            'estimated_impact': 'High',
            'priority': 'high',
            'created_at': datetime.now(),
            '__getitem__': lambda self, key: getattr(self, key, None)
        })()

        mock_conn.cursor.fetchall.return_value = [mock_row]

        result = await get_prevention_measures(category=DefectCategory.FUNCTIONAL)

        assert len(result) == 1
        assert result[0].category == DefectCategory.FUNCTIONAL


# ============================================================================
# Test: Helper Functions
# ============================================================================


class TestHelperFunctions:
    """Tests for helper functions"""

    def test_row_to_defect_report(self):
        """Test _row_to_defect_report conversion"""
        from src.api.v1.defect_tracking import _row_to_defect_report

        mock_row = create_mock_defect_row()

        result = _row_to_defect_report(mock_row)

        assert result.defect_id == mock_row.defect_id
        assert result.title == mock_row.title
        assert result.severity == mock_row.severity
        assert isinstance(result.reproduction_steps, list)
        assert isinstance(result.attachments, list)
        assert isinstance(result.tags, list)

    def test_row_to_prevention(self):
        """Test _row_to_prevention conversion"""
        from src.api.v1.defect_tracking import _row_to_prevention

        mock_row = type('MockRow', (), {
            'prevention_id': 'PREV-001',
            'category': 'functional',
            'title': 'Test',
            'description': 'Description',
            'implementation_steps': json.dumps(['Step 1', 'Step 2']),
            'estimated_impact': 'High',
            'priority': 'high',
            'created_at': datetime.now(),
            '__getitem__': lambda self, key: getattr(self, key, None)
        })()

        result = _row_to_prevention(mock_row)

        assert result.prevention_id == 'PREV-001'
        assert result.category == 'functional'
        assert isinstance(result.implementation_steps, list)
        assert len(result.implementation_steps) == 2

    @patch("src.api.v1.defect_tracking.get_db_connection")
    @pytest.mark.asyncio
    async def test_module_helper_functions(self, mock_get_conn):
        """Test module-level helper functions"""
        from src.api.v1.defect_tracking import _get_module_severity, _generate_defect_recommendations

        mock_conn = create_mock_connection()
        mock_get_conn.return_value = mock_conn

        # Test with empty result (no severity data)
        mock_conn.cursor.fetchall.return_value = []

        severity = _get_module_severity(mock_conn, "auth", datetime.now())
        # When no defects, should return 'low'
        assert severity == "low"

        # Test with severity data
        sev_row = type('MockRow', (), {
            'severity': 'critical',
            'count': 1,
            '__getitem__': lambda self, key: getattr(self, key, None)
        })()
        mock_conn.cursor.fetchall.return_value = [sev_row]

        severity = _get_module_severity(mock_conn, "auth", datetime.now())
        assert severity == "critical"

        # Test _generate_defect_recommendations
        recommendations = _generate_defect_recommendations(
            {"critical": 5, "high": 10},
            {"functional": 15, "performance": 8},
            {"auth": 12, "ui": 9},
        )
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0


# ============================================================================
# Test: Edge Cases and Error Handling
# ============================================================================


class TestDefectTrackingEdgeCases:
    """Tests for edge cases and error handling"""

    @patch("src.api.v1.defect_tracking.get_db_connection")
    @pytest.mark.asyncio
    async def test_get_defects_with_all_filters(self, mock_get_conn):
        """Test getting defects with all possible filters"""
        from src.api.v1.defect_tracking import get_defects, DefectStatus, DefectSeverity, DefectCategory

        mock_conn = create_mock_connection()
        mock_get_conn.return_value = mock_conn

        mock_conn.cursor.fetchall.return_value = []

        total_mock = type('MockRow', (), {'total': 0, '__getitem__': lambda self, k: 0 if k == 'total' else None})()
        mock_conn.cursor.fetchone.return_value = total_mock

        result = await get_defects(
            status=DefectStatus.OPEN,
            severity=DefectSeverity.HIGH,
            category=DefectCategory.FUNCTIONAL,
            module="authentication",
            reporter="user@example.com",
            assigned_to="dev@example.com",
        )

        assert "defects" in result

    @pytest.mark.asyncio
    async def test_enums_values(self):
        """Test that all enum values are correct"""
        from src.api.v1.defect_tracking import (
            DefectSeverity,
            DefectPriority,
            DefectStatus,
            DefectCategory,
        )

        assert DefectSeverity.LOW == "low"
        assert DefectSeverity.MEDIUM == "medium"
        assert DefectSeverity.HIGH == "high"
        assert DefectSeverity.CRITICAL == "critical"

        assert DefectPriority.LOW == "low"
        assert DefectPriority.MEDIUM == "medium"
        assert DefectPriority.HIGH == "high"

        assert DefectStatus.OPEN == "open"
        assert DefectStatus.IN_PROGRESS == "in_progress"
        assert DefectStatus.RESOLVED == "resolved"
        assert DefectStatus.CLOSED == "closed"
        assert DefectStatus.REOPENED == "reopened"

        assert DefectCategory.FUNCTIONAL == "functional"
        assert DefectCategory.PERFORMANCE == "performance"
        assert DefectCategory.SECURITY == "security"
        assert DefectCategory.USABILITY == "usability"
        assert DefectCategory.COMPATIBILITY == "compatibility"
        assert DefectCategory.INTEGRATION == "integration"
        assert DefectCategory.CONFIGURATION == "configuration"

    @patch("src.api.v1.defect_tracking.get_db_connection")
    @pytest.mark.asyncio
    async def test_connection_cleanup_on_error(self, mock_get_conn):
        """Test that database connection is closed even on error"""
        from src.api.v1.defect_tracking import get_defect

        mock_conn = create_mock_connection()
        mock_get_conn.return_value = mock_conn

        mock_conn.cursor.fetchone.return_value = None

        try:
            await get_defect("DEF-001")
        except HTTPException:
            pass

        mock_conn.close.assert_called_once()
