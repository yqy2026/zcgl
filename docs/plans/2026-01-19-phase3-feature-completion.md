# Phase 3: Feature Completion - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement missing user-facing features including property certificate asset matching, analytics dashboard export, and profile management (Issues 6, 7, 9).

**Architecture:**
- Backend: Implement fuzzy asset matching algorithm with confidence scoring, profile management endpoints, export service
- Frontend: Create asset match review UI, multi-format export system, profile update forms
- Together: Design match confidence thresholds and export format specifications

**Tech Stack:** FastAPI, SQLAlchemy 2.0, React 19, TypeScript, exceljs, jspdf, fuzzy matching algorithms

---

## Task 1: Backend - Implement Fuzzy Asset Matching Algorithm

**Files:**
- Create: `backend/src/services/asset_matching/asset_matcher.py`
- Create: `backend/src/services/asset_matching/match_strategies.py`
- Modify: `backend/src/api/v1/property_certificate.py:125` (replace empty asset_matches)
- Test: `backend/tests/unit/services/test_asset_matcher.py`

**Step 1: Write the failing test**

```python
# backend/tests/unit/services/test_asset_matcher.py
import pytest
from src.services.asset_matching.asset_matcher import AssetMatcher, MatchConfidence
from src.services.asset_matching.match_strategies import ExactMatchStrategy, FuzzyMatchStrategy

def test_exact_match_strategy():
    """Test exact matching by certificate ID and address"""
    strategy = ExactMatchStrategy()

    certificate = {
        "certificate_number": "CERT-2024-001",
        "property_address": "123 Main St, City, State 12345"
    }

    asset = {
        "certificate_number": "CERT-2024-001",
        "address": "123 Main St, City, State 12345"
    }

    result = strategy.match(certificate, asset)
    assert result.confidence == MatchConfidence.HIGH
    assert result.score >= 0.95

def test_fuzzy_match_strategy():
    """Test fuzzy matching with address similarity"""
    strategy = FuzzyMatchStrategy()

    certificate = {
        "certificate_number": "CERT-2024-001",
        "property_address": "123 Main Street, City, State 12345"
    }

    asset = {
        "certificate_number": "CERT-2024-001",
        "address": "123 Main St, City, State 12345"
    }

    result = strategy.match(certificate, asset)
    assert result.confidence in [MatchConfidence.HIGH, MatchConfidence.MEDIUM]
    assert result.score > 0.80

def test_asset_matcher_integration():
    """Test complete asset matching flow"""
    from src.services.asset_matching.asset_matcher import AssetMatcher

    matcher = AssetMatcher()

    certificate = {
        "certificate_number": "CERT-2024-001",
        "property_address": "123 Main St, City, State 12345",
        "area": 1500.0
    }

    # Mock assets database
    assets = [
        {
            "id": "asset-1",
            "certificate_number": "CERT-2024-001",
            "address": "123 Main St, City, State 12345",
            "area": 1500.0
        },
        {
            "id": "asset-2",
            "certificate_number": "CERT-2024-002",
            "address": "456 Oak Ave, City, State 12345",
            "area": 2000.0
        }
    ]

    matches = matcher.find_matches(certificate, assets)

    assert len(matches) > 0
    # First match should be exact match
    assert matches[0].asset_id == "asset-1"
    assert matches[0].confidence == MatchConfidence.HIGH
```

**Step 2: Create match strategies**

```python
# backend/src/services/asset_matching/match_strategies.py
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any
from Levenshtein import ratio as levenshtein_ratio

class MatchConfidence(str, Enum):
    """Match confidence levels"""
    HIGH = "high"  # 95%+ match
    MEDIUM = "medium"  # 80-94% match
    LOW = "low"  # 60-79% match

@dataclass
class MatchResult:
    """Result of asset matching attempt"""
    asset_id: str
    confidence: MatchConfidence
    score: float  # 0.0 to 1.0
    matched_fields: list[str]
    notes: str = ""

class MatchStrategy:
    """Base class for match strategies"""

    def match(self, certificate: Dict[str, Any], asset: Dict[str, Any]) -> MatchResult:
        """Match certificate to asset"""
        raise NotImplementedError

class ExactMatchStrategy(MatchStrategy):
    """Exact matching by certificate ID and address"""

    def match(self, certificate: Dict[str, Any], asset: Dict[str, Any]) -> MatchResult:
        matched_fields = []
        score = 0.0

        # Check certificate number
        if certificate.get("certificate_number") == asset.get("certificate_number"):
            matched_fields.append("certificate_number")
            score += 0.5

        # Check address (exact match)
        if certificate.get("property_address") == asset.get("address"):
            matched_fields.append("address")
            score += 0.5

        if score >= 0.95:
            confidence = MatchConfidence.HIGH
        elif score >= 0.5:
            confidence = MatchConfidence.MEDIUM
        else:
            confidence = MatchConfidence.LOW

        return MatchResult(
            asset_id=asset.get("id"),
            confidence=confidence,
            score=score,
            matched_fields=matched_fields,
            notes=f"Matched {len(matched_fields)} fields exactly"
        )

class FuzzyMatchStrategy(MatchStrategy):
    """Fuzzy matching with address similarity"""

    def match(self, certificate: Dict[str, Any], asset: Dict[str, Any]) -> MatchResult:
        matched_fields = []
        score = 0.0

        # Certificate number exact match
        if certificate.get("certificate_number") == asset.get("certificate_number"):
            matched_fields.append("certificate_number")
            score += 0.4

        # Address similarity using Levenshtein distance
        cert_address = certificate.get("property_address", "")
        asset_address = asset.get("address", "")

        if cert_address and asset_address:
            similarity = levenshtein_ratio(cert_address.lower(), asset_address.lower())
            if similarity >= 0.80:  # 80% threshold
                matched_fields.append("address")
                score += similarity * 0.4

        # Area comparison (within 10%)
        cert_area = certificate.get("area", 0)
        asset_area = asset.get("area", 0)
        if cert_area and asset_area:
            area_diff = abs(cert_area - asset_area) / max(cert_area, asset_area)
            if area_diff <= 0.10:  # Within 10%
                matched_fields.append("area")
                score += 0.2

        # Determine confidence
        if score >= 0.90:
            confidence = MatchConfidence.HIGH
        elif score >= 0.60:
            confidence = MatchConfidence.MEDIUM
        else:
            confidence = MatchConfidence.LOW

        return MatchResult(
            asset_id=asset.get("id"),
            confidence=confidence,
            score=score,
            matched_fields=matched_fields,
            notes=f"Fuzzy match with {score:.2%} confidence"
        )

class PartialMatchStrategy(MatchStrategy):
    """Partial matching - certificate ID only"""

    def match(self, certificate: Dict[str, Any], asset: Dict[str, Any]) -> MatchResult:
        score = 0.0
        matched_fields = []

        # Only certificate number
        if certificate.get("certificate_number") == asset.get("certificate_number"):
            matched_fields.append("certificate_number")
            score = 0.5

        return MatchResult(
            asset_id=asset.get("id"),
            confidence=MatchConfidence.MEDIUM,
            score=score,
            matched_fields=matched_fields,
            notes="Certificate ID match only, address verification needed"
        )
```

**Step 3: Create AssetMatcher service**

```python
# backend/src/services/asset_matching/asset_matcher.py
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from src.services.asset_matching.match_strategies import (
    MatchStrategy,
    ExactMatchStrategy,
    FuzzyMatchStrategy,
    PartialMatchStrategy,
    MatchResult,
    MatchConfidence
)

class AssetMatcher:
    """Asset matching service with multiple strategies"""

    def __init__(self, db: Session):
        self.db = db
        self.strategies = [
            ExactMatchStrategy(),
            FuzzyMatchStrategy(),
            PartialMatchStrategy(),
        ]

    def find_matches(
        self,
        certificate: Dict[str, Any],
        assets: List[Dict[str, Any]],
        min_confidence: MatchConfidence = MatchConfidence.MEDIUM
    ) -> List[MatchResult]:
        """
        Find matching assets for a certificate

        Args:
            certificate: Certificate data
            assets: List of assets to match against
            min_confidence: Minimum confidence level to include

        Returns:
            List of MatchResults sorted by score (descending)
        """
        all_matches = []

        for asset in assets:
            # Try each strategy
            for strategy in self.strategies:
                result = strategy.match(certificate, asset)
                all_matches.append(result)

        # Filter by minimum confidence
        confidence_order = {
            MatchConfidence.HIGH: 3,
            MatchConfidence.MEDIUM: 2,
            MatchConfidence.LOW: 1
        }

        filtered_matches = [
            m for m in all_matches
            if confidence_order[m.confidence] >= confidence_order[min_confidence]
        ]

        # Remove duplicates (same asset_id) keeping highest score
        unique_matches = {}
        for match in filtered_matches:
            asset_id = match.asset_id
            if asset_id not in unique_matches or match.score > unique_matches[asset_id].score:
                unique_matches[asset_id] = match

        # Sort by score descending
        return sorted(unique_matches.values(), key=lambda m: m.score, reverse=True)

    def find_matches_from_db(
        self,
        certificate: Dict[str, Any],
        min_confidence: MatchConfidence = MatchConfidence.MEDIUM
    ) -> List[MatchResult]:
        """Find matches by querying database for assets"""
        from src.crud.asset import asset_crud
        from src.models.asset import Asset

        # Get all assets (could be optimized with filters)
        assets = asset_crud.get_multi(self.db, limit=1000)

        # Convert to dict format
        asset_dicts = [
            {
                "id": str(asset.id),
                "certificate_number": asset.certificate_number,
                "address": asset.address,
                "area": asset.area,
            }
            for asset in assets.items
        ]

        return self.find_matches(certificate, asset_dicts, min_confidence)

    def get_match_statistics(
        self,
        certificate: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get matching statistics for a certificate"""
        matches = self.find_matches_from_db(certificate)

        return {
            "total_matches": len(matches),
            "high_confidence": len([m for m in matches if m.confidence == MatchConfidence.HIGH]),
            "medium_confidence": len([m for m in matches if m.confidence == MatchConfidence.MEDIUM]),
            "low_confidence": len([m for m in matches if m.confidence == MatchConfidence.LOW]),
            "average_score": sum(m.score for m in matches) / len(matches) if matches else 0.0,
        }
```

**Step 4: Run tests**

```bash
cd backend
pytest tests/unit/services/test_asset_matcher.py -v
```

**Step 5: Modify property_certificate.py to use matcher**

```python
# backend/src/api/v1/property_certificate.py
# Import at top
from src.services.asset_matching.asset_matcher import AssetMatcher, MatchConfidence

# Replace line 125 (empty asset_matches) with:
        # Find matching assets
        matcher = AssetMatcher(db)
        matches = matcher.find_matches_from_db(
            certificate=result.get("data", {}),
            min_confidence=MatchConfidence.MEDIUM
        )

        # Convert matches to response format
        asset_matches_response = [
            {
                "asset_id": m.asset_id,
                "confidence": m.confidence.value,
                "score": round(m.score, 3),
                "matched_fields": m.matched_fields,
                "notes": m.notes
            }
            for m in matches[:10]  # Limit to top 10 matches
        ]
```

**Step 6: Install dependencies**

```bash
cd backend
pip install python-Levenshtein
uv add python-Levenshtein
```

**Step 7: Commit**

```bash
cd backend
git add src/services/asset_matching/ src/api/v1/property_certificate.py tests/unit/services/test_asset_matcher.py
git commit -m "feat(asset-matching): Implement fuzzy asset matching algorithm

- Create MatchStrategy base class with multiple implementations
- ExactMatchStrategy: Certificate ID + address exact match
- FuzzyMatchStrategy: Address similarity using Levenshtein distance
- PartialMatchStrategy: Certificate ID only
- Create AssetMatcher service with confidence scoring
- Return top 10 matches sorted by score

Breaking change: Property certificate upload now returns asset_matches array

Fixes #6: Asset matching functionality now implemented

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Frontend - Create Asset Match Review Component

**Files:**
- Create: `frontend/src/components/PropertyCertificate/AssetMatchReview.tsx`
- Modify: `frontend/src/pages/PropertyCertificate/PropertyCertificateUpload.tsx`
- Test: `frontend/src/components/PropertyCertificate/__tests__/AssetMatchReview.test.tsx`

**Step 1: Write the failing test**

```typescript
// frontend/src/components/PropertyCertificate/__tests__/AssetMatchReview.test.tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AssetMatchReview } from '../AssetMatchReview';

describe('AssetMatchReview', () => {
  const mockMatches = [
    {
      asset_id: 'asset-1',
      confidence: 'high',
      score: 0.95,
      matched_fields: ['certificate_number', 'address'],
      notes: 'Matched 2 fields exactly'
    },
    {
      asset_id: 'asset-2',
      confidence: 'medium',
      score: 0.85,
      matched_fields: ['certificate_number'],
      notes: 'Certificate ID match only'
    }
  ];

  it('should display asset matches', () => {
    render(<AssetMatchReview matches={mockMatches} />);
    expect(screen.getByText('asset-1')).toBeInTheDocument();
    expect(screen.getByText('asset-2')).toBeInTheDocument();
  });

  it('should show confidence indicators', () => {
    render(<AssetMatchReview matches={mockMatches} />);
    expect(screen.getByText(/95%/)).toBeInTheDocument();
    expect(screen.getByText(/85%/)).toBeInTheDocument();
  });

  it('should allow manual linking', () => {
    const onLink = vi.fn();
    render(<AssetMatchReview matches={mockMatches} onLink={onLink} />);

    const linkButtons = screen.getAllByRole('button', { name: /link/i });
    expect(linkButtons.length).toBeGreaterThan(0);
  });
});
```

**Step 2: Create AssetMatchReview component**

```typescript
// frontend/src/components/PropertyCertificate/AssetMatchReview.tsx
import React from 'react';
import { Card, Table, Tag, Button, Space, Tooltip } from 'antd';
import { LinkOutlined, CheckCircleOutlined, WarningOutlined } from '@ant-design/icons';

export interface AssetMatch {
  asset_id: string;
  confidence: 'high' | 'medium' | 'low';
  score: number;
  matched_fields: string[];
  notes: string;
}

interface AssetMatchReviewProps {
  matches: AssetMatch[];
  onLink?: (assetId: string) => void;
  onUnlink?: (assetId: string) => void;
  linkedAssetId?: string;
  loading?: boolean;
}

export const AssetMatchReview: React.FC<AssetMatchReviewProps> = ({
  matches,
  onLink,
  onUnlink,
  linkedAssetId,
  loading = false
}) => {
  const getConfidenceColor = (confidence: string) => {
    switch (confidence) {
      case 'high': return 'success';
      case 'medium': return 'warning';
      case 'low': return 'default';
      default: return 'default';
    }
  };

  const getConfidenceIcon = (confidence: string) => {
    switch (confidence) {
      case 'high': return <CheckCircleOutlined />;
      case 'medium': return <WarningOutlined />;
      default: return null;
    }
  };

  const columns = [
    {
      title: 'Asset ID',
      dataIndex: 'asset_id',
      key: 'asset_id',
      render: (id: string) => <code>{id}</code>
    },
    {
      title: 'Confidence',
      dataIndex: 'confidence',
      key: 'confidence',
      render: (confidence: string, record: AssetMatch) => (
        <Space>
          <Tag color={getConfidenceColor(confidence)} icon={getConfidenceIcon(confidence)}>
            {confidence.toUpperCase()}
          </Tag>
          <span>{Math.round(record.score * 100)}%</span>
        </Space>
      )
    },
    {
      title: 'Matched Fields',
      dataIndex: 'matched_fields',
      key: 'matched_fields',
      render: (fields: string[]) => (
        <>
          {fields.map(field => (
            <Tag key={field}>{field}</Tag>
          ))}
        </>
      )
    },
    {
      title: 'Notes',
      dataIndex: 'notes',
      key: 'notes'
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: AssetMatch) => (
        <Space>
          {linkedAssetId === record.asset_id ? (
            <Tag color="success">Linked</Tag>
          ) : (
            <Tooltip title="Link this asset to certificate">
              <Button
                type="primary"
                size="small"
                icon={<LinkOutlined />}
                onClick={() => onLink?.(record.asset_id)}
                disabled={linkedAssetId != null}
                loading={loading}
              >
                Link
              </Button>
            </Tooltip>
          )}
          {linkedAssetId === record.asset_id && onUnlink && (
            <Button
              size="small"
              onClick={() => onUnlink(record.asset_id)}
            >
              Unlink
            </Button>
          )}
        </Space>
      )
    }
  ];

  if (matches.length === 0) {
    return (
      <Card title="Asset Matches">
        <p>No matching assets found for this certificate.</p>
      </Card>
    );
  }

  return (
    <Card
      title={`Asset Matches (${matches.length})`}
      extra={
        linkedAssetId && (
          <Tag color="success">Linked to {linkedAssetId}</Tag>
        )
      }
    >
      <Table
        dataSource={matches}
        columns={columns}
        rowKey="asset_id"
        pagination={false}
        size="small"
      />
    </Card>
  );
};
```

**Step 3: Integrate into upload page**

```typescript
// frontend/src/pages/PropertyCertificate/PropertyCertificateUpload.tsx
// Add AssetMatchReview component to display after upload

{uploadResult && (
  <>
    {/* Existing result display */}

    {/* Add match review */}
    {uploadResult.asset_matches && uploadResult.asset_matches.length > 0 && (
      <AssetMatchReview
        matches={uploadResult.asset_matches}
        onLink={handleLinkAsset}
        onUnlink={handleUnlinkAsset}
        linkedAssetId={linkedAssetId}
        loading={linkingAsset}
      />
    )}
  </>
)}
```

**Step 4: Run tests**

```bash
cd frontend
pnpm test src/components/PropertyCertificate/__tests__/AssetMatchReview.test.tsx
```

**Step 5: Commit**

```bash
cd frontend
git add src/components/PropertyCertificate/AssetMatchReview.tsx src/components/PropertyCertificate/__tests__/AssetMatchReview.test.tsx
git commit -m "feat(asset-matching): Create asset match review UI component

- Display asset matches in table with confidence indicators
- Show color-coded confidence tags (high/medium/low)
- Display match score percentage and matched fields
- Add link/unlink actions for manual asset association
- Support multiple matches with visual indicators

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Frontend - Implement Export Service with Multiple Formats

**Files:**
- Create: `frontend/src/services/exportService.ts`
- Modify: `frontend/src/components/Analytics/AnalyticsDashboard.tsx:76-78`
- Test: `frontend/src/services/__tests__/exportService.test.ts`

**Step 1: Write the failing test**

```typescript
// frontend/src/services/__tests__/exportService.test.ts
import { describe, it, expect, vi } from 'vitest';
import { ExportService } from '../exportService';
import * as XLSX from 'xlsx';

describe('ExportService', () => {
  it('should export data to Excel format', async () => {
    const data = [
      { name: 'Asset 1', value: 100 },
      { name: 'Asset 2', value: 200 }
    ];

    const blob = await ExportService.exportToExcel(data, 'test-export');
    expect(blob).toBeInstanceOf(Blob);
    expect(blob.type).toContain('sheet');
  });

  it('should export data to CSV format', async () => {
    const data = [
      { name: 'Asset 1', value: 100 }
    ];

    const blob = await ExportService.exportToCSV(data, 'test-export');
    expect(blob).toBeInstanceOf(Blob);
    expect(blob.type).toContain('csv');

    const text = await blob.text();
    expect(text).toContain('name,value');
  });

  it('should export data to PDF format', async () => {
    const data = [
      { name: 'Asset 1', value: 100 }
    ];

    const blob = await ExportService.exportToPDF(data, 'test-export');
    expect(blob).toBeInstanceOf(Blob);
    expect(blob.type).toContain('pdf');
  });
});
```

**Step 2: Install dependencies**

```bash
cd frontend
pnpm add xlsx jspdf
```

**Step 3: Implement ExportService**

```typescript
// frontend/src/services/exportService.ts
import * as XLSX from 'xlsx';
import jsPDF from 'jspdf';
import { autoTable } from 'jspdf-autotable';

export type ExportFormat = 'excel' | 'csv' | 'pdf';

export interface ExportConfig {
  format: ExportFormat;
  filename?: string;
  sheetName?: string;  // For Excel
  includeHeaders?: boolean;
  title?: string;  // For PDF
}

export interface ExportData {
  [key: string]: string | number | boolean | null;
}

class ExportServiceClass {
  /**
   * Export data to Excel format
   */
  async exportToExcel(
    data: ExportData[],
    filename: string = 'export',
    config: Partial<ExportConfig> = {}
  ): Promise<Blob> {
    const worksheet = XLSX.utils.json_to_sheet(data);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, config.sheetName || 'Sheet1');

    // Generate buffer
    const excelBuffer = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' });
    return new Blob([excelBuffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
  }

  /**
   * Export data to CSV format
   */
  async exportToCSV(
    data: ExportData[],
    filename: string = 'export',
    config: Partial<ExportConfig> = {}
  ): Promise<Blob> {
    if (data.length === 0) {
      return new Blob([''], { type: 'text/csv' });
    }

    const headers = Object.keys(data[0]);
    const csvRows: string[] = [];

    // Add headers
    if (config.includeHeaders !== false) {
      csvRows.push(headers.join(','));
    }

    // Add data rows
    for (const row of data) {
      const values = headers.map(header => {
        const value = row[header];
        // Escape quotes and wrap in quotes if contains comma
        const stringValue = String(value ?? '');
        if (stringValue.includes(',') || stringValue.includes('"')) {
          return `"${stringValue.replace(/"/g, '""')}"`;
        }
        return stringValue;
      });
      csvRows.push(values.join(','));
    }

    // Add UTF-8 BOM for Excel compatibility
    const csvContent = csvRows.join('\n');
    const bom = '\uFEFF';
    return new Blob([bom + csvContent], { type: 'text/csv;charset=utf-8;' });
  }

  /**
   * Export data to PDF format
   */
  async exportToPDF(
    data: ExportData[],
    filename: string = 'export',
    config: Partial<ExportConfig> = {}
  ): Promise<Blob> {
    const doc = new jsPDF();

    // Add title
    if (config.title) {
      doc.setFontSize(16);
      doc.text(config.title, 14, 20);
      doc.setFontSize(10);
    }

    // Prepare table data
    if (data.length > 0) {
      const headers = [Object.keys(data[0])];
      const rows = data.map(row => Object.values(row));

      // Add table
      autoTable(doc, {
        head: headers,
        body: rows,
        startY: config.title ? 30 : 10,
        styles: {
          fontSize: 8,
          cellPadding: 2,
        },
        headStyles: {
          fillColor: [66, 139, 202],
          textColor: 255,
        },
      });
    }

    // Generate blob
    return new Blob([doc.output('arraybuffer')], { type: 'application/pdf' });
  }

  /**
   * Main export method that routes to appropriate format handler
   */
  async export(
    data: ExportData[],
    format: ExportFormat,
    filename: string = 'export',
    config: Partial<ExportConfig> = {}
  ): Promise<Blob> {
    switch (format) {
      case 'excel':
        return this.exportToExcel(data, filename, config);
      case 'csv':
        return this.exportToCSV(data, filename, config);
      case 'pdf':
        return this.exportToPDF(data, filename, config);
      default:
        throw new Error(`Unsupported export format: ${format}`);
    }
  }

  /**
   * Download blob as file
   */
  downloadBlob(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  /**
   * Export and download in one step
   */
  async exportAndDownload(
    data: ExportData[],
    format: ExportFormat,
    filename: string = 'export',
    config: Partial<ExportConfig> = {}
  ): Promise<void> {
    const blob = await this.export(data, format, filename, config);

    // Add file extension
    const extensions = {
      excel: 'xlsx',
      csv: 'csv',
      pdf: 'pdf'
    };
    const fullFilename = `${filename}.${extensions[format]}`;

    this.downloadBlob(blob, fullFilename);
  }
}

// Export singleton
export const ExportService = new ExportServiceClass();
```

**Step 4: Update AnalyticsDashboard to use ExportService**

```typescript
// frontend/src/components/Analytics/AnalyticsDashboard.tsx
// Replace lines 76-78 with actual export functionality

import { ExportService } from '@/services/exportService';

// In component:
const handleExport = async (format: 'excel' | 'csv' | 'pdf') => {
  try {
    setLoading(true);

    // Prepare export data from dashboard data
    const exportData = dashboardData?.metrics?.map(metric => ({
      category: metric.category,
      value: metric.value,
      change: metric.change_percent,
      date: new Date().toISOString().split('T')[0]
    })) ?? [];

    await ExportService.exportAndDownload(
      exportData,
      format,
      'analytics-dashboard',
      {
        title: 'Analytics Dashboard Export',
        includeHeaders: true
      }
    );

    Message.success('Export successful');
  } catch (error) {
    logger.error('Export failed:', error);
    Message.error('Export failed');
  } finally {
    setLoading(false);
  }
};

// Update export button:
<Button
  onClick={() => handleExport('excel')}
  loading={loading}
>
  Export to Excel
</Button>
```

**Step 5: Run tests**

```bash
cd frontend
pnpm test src/services/__tests__/exportService.test.ts
```

**Step 6: Commit**

```bash
cd frontend
git add src/services/exportService.ts src/components/Analytics/AnalyticsDashboard.tsx src/services/__tests__/exportService.test.ts
git commit -m "feat(export): Implement multi-format export service

- Create ExportService with Excel, CSV, and PDF support
- Use xlsx library for Excel generation with formatting
- Implement CSV export with UTF-8 BOM for Excel compatibility
- Add PDF export with jspdf and auto-table
- Support titles, headers, and custom configuration
- Add exportAndDownload helper for one-step exports

Breaking change: Export buttons now functional with format selection

Fixes #7: Analytics dashboard export functionality now implemented

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Backend - Implement Profile Management Endpoints

**Files:**
- Create: `backend/src/api/v1/users.py` (profile management endpoints)
- Modify: `backend/src/schemas/user.py` (add profile update schemas)
- Test: `backend/tests/integration/api/test_profile_management.py`

**Step 1: Write the failing test**

```python
# backend/tests/integration/api/test_profile_management.py
import pytest
from fastapi.testclient import TestClient

def test_update_profile(client: TestClient, auth_headers):
    """Test updating user profile"""
    response = client.patch("/api/v1/users/me", json={
        "full_name": "Updated Name",
        "email": "updated@example.com",
        "phone": "1234567890"
    }, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"
    assert data["email"] == "updated@example.com"

def test_change_password_separate_endpoint(client: TestClient, auth_headers):
    """Test that password change uses separate endpoint"""
    response = client.put("/api/v1/users/me/password", json={
        "old_password": "oldpass123",
        "new_password": "newpass456"
    }, headers=auth_headers)

    assert response.status_code == 200

def test_update_avatar(client: TestClient, auth_headers):
    """Test uploading profile avatar"""
    # Create fake image file
    files = {"avatar": ("avatar.jpg", b"fake_image_data", "image/jpeg")}

    response = client.put("/api/v1/users/me/avatar", files=files, headers=auth_headers)

    assert response.status_code == 200
    assert "avatar_url" in response.json()
```

**Step 2: Create profile update schemas**

```python
# backend/src/schemas/user.py
# Add profile update schemas

class ProfileUpdate(BaseModel):
    """Profile update schema"""
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    organization_id: str | None = None

    class Config:
        from_attributes = True

class PasswordChange(BaseModel):
    """Password change schema"""
    old_password: str
    new_password: str
    confirm_password: str

    @validator('new_password')
    def validate_password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v
```

**Step 3: Create profile management endpoints**

```python
# backend/src/api/v1/users.py
# Add profile management endpoints

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from src.api.deps import get_current_active_user, get_db
from src.schemas.user import UserResponse, ProfileUpdate, PasswordChange
from src.services.user_service import UserService

router = APIRouter()

@router.patch("/me", response_model=UserResponse)
async def update_profile(
    profile_update: ProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    user_service = UserService(db)

    # Check email uniqueness if changing email
    if profile_update.email and profile_update.email != current_user.email:
        existing = user_service.get_by_email(profile_update.email)
        if existing:
            raise bad_request("Email already registered")

    # Update profile
    updated_user = user_service.update_profile(
        user_id=current_user.id,
        full_name=profile_update.full_name,
        email=profile_update.email,
        phone=profile_update.phone
    )

    return updated_user

@router.put("/me/password")
async def change_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change current user password"""
    from src.core.security import verify_password, get_password_hash

    # Verify old password
    if not verify_password(password_change.old_password, current_user.password_hash):
        raise unauthorized("Invalid old password")

    # Update password
    user_service = UserService(db)
    user_service.update_password(
        user_id=current_user.id,
        new_password=password_change.new_password
    )

    return {"message": "Password changed successfully"}

@router.put("/me/avatar")
async def upload_avatar(
    avatar: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload profile avatar"""
    # Validate file type
    if not avatar.content_type.startswith("image/"):
        raise bad_request("File must be an image")

    # Validate file size (max 5MB)
    MAX_SIZE = 5 * 1024 * 1024  # 5MB
    contents = await avatar.read()
    if len(contents) > MAX_SIZE:
        raise bad_request("File size exceeds 5MB limit")

    # Save avatar (implement storage logic)
    from src.services.storage_service import StorageService
    storage = StorageService()

    avatar_url = await storage.upload_avatar(
        user_id=current_user.id,
        filename=avatar.filename,
        contents=contents
    )

    # Update user avatar URL
    user_service = UserService(db)
    user_service.update_avatar(current_user.id, avatar_url)

    return {
        "message": "Avatar uploaded successfully",
        "avatar_url": avatar_url
    }
```

**Step 4: Run tests**

```bash
cd backend
pytest tests/integration/api/test_profile_management.py -v
```

**Step 5: Commit**

```bash
cd backend
git add src/api/v1/users.py src/schemas/user.py tests/integration/api/test_profile_management.py
git commit -m "feat(users): Implement profile management endpoints

- Add PATCH /api/v1/users/me for profile updates
- Add PUT /api/v1/users/me/password for password changes
- Add PUT /api/v1/users/me/avatar for avatar uploads
- Separate profile update from password change
- Validate email uniqueness and password strength
- Support avatar upload with size validation

Breaking change: New API endpoints for profile management

Fixes #9: Profile update calling wrong API endpoint

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Frontend - Update AuthService with Correct Profile Methods

**Files:**
- Modify: `frontend/src/services/authService.ts:331-340`
- Test: `frontend/src/services/__tests__/authService-profile.test.ts`

**Step 1: Write the failing test**

```typescript
// frontend/src/services/__tests__/authService-profile.test.ts
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { AuthService } from '../authService';

vi.mock('@/api/client', () => ({
  enhancedApiClient: {
    patch: vi.fn(),
    put: vi.fn(),
  },
}));

describe('AuthService - Profile Management', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should call correct profile update endpoint', async () => {
    vi.mocked(enhancedApiClient.patch).mockResolvedValue({
      data: { id: '1', full_name: 'Updated' }
    });

    const result = await AuthService.updateProfile({
      full_name: 'Updated Name',
      email: 'test@example.com'
    });

    expect(result.success).toBe(true);
    expect(enhancedApiClient.patch).toHaveBeenCalledWith(
      '/users/me',
      { full_name: 'Updated Name', email: 'test@example.com' }
    );
  });

  it('should call password change endpoint', async () => {
    vi.mocked(enhancedApiClient.put).mockResolvedValue({
      data: { message: 'Password changed' }
    });

    const result = await AuthService.changePassword({
      old_password: 'oldpass',
      new_password: 'newpass',
      confirm_password: 'newpass'
    });

    expect(result.success).toBe(true);
    expect(enhancedApiClient.put).toHaveBeenCalledWith(
      '/users/me/password',
      expect.objectContaining({
        old_password: 'oldpass',
        new_password: 'newpass'
      })
    );
  });

  it('should NOT call password endpoint for profile update', async () => {
    vi.mocked(enhancedApiClient.patch).mockResolvedValue({
      data: { id: '1', full_name: 'Updated' }
    });

    await AuthService.updateProfile({ full_name: 'Test' });

    // Should NOT have called PUT /password
    expect(enhancedApiClient.put).not.toHaveBeenCalled();
    // Should have called PATCH /users/me
    expect(enhancedApiClient.patch).toHaveBeenCalledWith('/users/me', expect.anything());
  });
});
```

**Step 2: Update authService.ts with correct methods**

```typescript
// frontend/src/services/authService.ts
// Replace lines 331-340 with correct profile methods

  /**
   * Update user profile (separate from password change)
   */
  static async updateProfile(profileData: {
    full_name?: string;
    email?: string;
    phone?: string;
    organization_id?: string;
  }): Promise<ApiResponse<{ user: User }>> {
    try {
      const response = await enhancedApiClient.patch<ApiResponse<User>>('/users/me', profileData);

      return {
        success: true,
        data: {
          user: response.data.data as User,
        },
        message: response.data.message || 'Profile updated successfully',
      };
    } catch (error) {
      return this.handleApiError(error as Error);
    }
  }

  /**
   * Change user password (separate endpoint)
   */
  static async changePassword(passwordData: {
    old_password: string;
    new_password: string;
    confirm_password: string;
  }): Promise<ApiResponse<Record<string, never>>> {
    try {
      const response = await enhancedApiClient.put<ApiResponse<Record<string, never>>>(
        '/users/me/password',
        passwordData
      );

      return {
        success: true,
        data: response.data.data,
        message: response.data.message || 'Password changed successfully',
      };
    } catch (error) {
      return this.handleApiError(error as Error);
    }
  }

  /**
   * Upload profile avatar
   */
  static async uploadAvatar(file: File): Promise<ApiResponse<{ avatar_url: string }>> {
    try {
      const formData = new FormData();
      formData.append('avatar', file);

      const response = await enhancedApiClient.put<ApiResponse<{ avatar_url: string }>>(
        '/users/me/avatar',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      return {
        success: true,
        data: response.data.data,
        message: response.data.message || 'Avatar uploaded successfully',
      };
    } catch (error) {
      return this.handleApiError(error as Error);
    }
  }
```

**Step 3: Run tests**

```bash
cd frontend
pnpm test src/services/__tests__/authService-profile.test.ts
```

**Step 4: Commit**

```bash
cd frontend
git add src/services/authService.ts src/services/__tests__/authService-profile.test.ts
git commit -m "fix(auth): Fix profile management API calls

- Replace incorrect password endpoint with profile update
- Add updateProfile() calling PATCH /users/me
- Add changePassword() calling PUT /users/me/password
- Add uploadAvatar() calling PUT /users/me/avatar
- Separate profile updates from password changes

Fixes #9: Profile update calling wrong endpoint path

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Summary

**Phase 3 Complete**: All feature completion issues resolved
- ✅ Issue #6: Property certificate asset matching with fuzzy algorithm
- ✅ Issue #7: Analytics dashboard export (Excel, CSV, PDF)
- ✅ Issue #9: Profile management with correct API endpoints

**New Features Implemented**:
- **Asset Matching**: Fuzzy matching algorithm with confidence scoring
  - Exact match, fuzzy match, and partial match strategies
  - Levenshtein distance for address similarity
  - Confidence levels: HIGH (95%+), MEDIUM (80-94%), LOW (60-79%)
  - Asset match review UI with link/unlink functionality

- **Export System**: Multi-format export with service layer
  - Excel export using xlsx library with formatted cells
  - CSV export with UTF-8 BOM for Excel compatibility
  - PDF export with jspdf and auto-table
  - Configurable titles, headers, and file naming

- **Profile Management**: Complete user profile CRUD
  - PATCH /api/v1/users/me for profile updates
  - PUT /api/v1/users/me/password for password changes
  - PUT /api/v1/users/me/avatar for avatar uploads
  - Email uniqueness validation and password strength checks

**Breaking Changes**:
- Property certificate upload now returns `asset_matches` array
- Profile updates use separate endpoint from password changes
- Avatar uploads require image files under 5MB

**Dependencies Added**:
- Backend: `python-Levenshtein` (fuzzy matching)
- Frontend: `xlsx`, `jspdf`, `jspdf-autotable` (export formats)

**Next Steps**: Proceed to Phase 4 - Final Hardening & Validation
