# Property Certificate Management - User Guide

## Overview

The Property Certificate Management feature allows you to upload, extract, and manage Chinese property certificates (产权证) using AI-powered OCR.

## Supported Certificate Types

1. **不动产权证** (Real Estate Certificate) - Modern unified certificate for real estate and land
2. **房屋所有权证** (House Ownership Certificate) - Old-style house ownership certificate
3. **土地使用证** (Land Use Certificate) - Land use rights certificate
4. **其他权属证明** (Other) - Other property ownership documents

## Features

### AI-Powered Extraction

- Automatic text extraction from scanned certificates
- Support for PDF, PNG, JPG formats (max 10MB)
- Confidence scoring to assess extraction quality
- Validation warnings for missing or inconsistent data

### Smart Asset Matching

- Automatic matching of certificates to existing assets
- Fuzzy matching on address and owner name
- Confidence scores for match quality
- Manual override capability

### CRUD Operations

- Create certificates manually or via AI extraction
- View all certificates in searchable list
- Edit certificate information
- Delete certificates with confirmation

## Usage

### Upload and Extract Certificate

1. Navigate to **Property Certificates** → **Import**
2. Upload certificate file (PDF/PNG/JPG, max 10MB)
3. Wait for AI extraction (typically 5-30 seconds)
4. Review extracted information:
   - Check confidence score (green = high, yellow = medium, red = low)
   - Review validation errors (missing required fields)
   - Review warnings (potential data issues)
5. Edit any incorrect fields
6. (Optional) Select asset to link from suggested matches
7. Click **"确认导入"** (Confirm Import) to save

### Manual Entry

1. Click **"新建产权证"** (New Certificate) in list page
2. Fill in required fields:
   - Certificate Number (required)
   - Certificate Type (required)
   - Property Address (required)
   - Other fields as needed
3. Link assets and owners
4. Click **Save**

### Search and Filter

Use the list page filters:
- **Search**: Certificate number
- **Filter**: Certificate type
- **Sort**: By date, confidence score, etc.

### Confidence Scores

- **≥90% (优秀)**: High quality extraction, can use directly
- **70-89% (中等)**: Medium quality, recommended to review
- **<70% (需复核)**: Low quality, must verify and correct manually

## Data Fields

### Required Fields

- Certificate Number (证书编号)
- Certificate Type (证书类型)
- Property Address (坐落地址)

### Optional Fields

- Registration Date (登记日期)
- Property Type (用途)
- Building Area (建筑面积)
- Land Area (土地面积)
- Floor Info (楼层信息)
- Land Use Type (土地使用权类型)
- Land Use Term (土地使用期限)
- Co-ownership (共有情况)
- Restrictions (权利限制情况)
- Remarks (备注)

## Troubleshooting

**Upload failed**:
- Check file format (must be PDF, PNG, or JPG)
- Check file size (must be under 10MB)
- Ensure you have upload permissions

**Extraction failed**:
- Verify image quality is clear
- Ensure text is readable
- Try rescanning at higher resolution

**Validation errors**:
- Check required fields are filled
- Verify certificate number format
- Ensure dates are in correct format (YYYY-MM-DD)

**Asset matching**:
- System suggests matches automatically
- Can manually select different asset
- Can create new asset if no match found

## Security

- All operations require authentication
- Upload permissions required for file operations
- Audit trail tracks who created/modified certificates
- Sensitive data (phone numbers, ID numbers) is encrypted

## API Endpoints

See API documentation at `/api/v1/docs` for complete endpoint reference.

## Support

For issues or questions, contact the development team.
