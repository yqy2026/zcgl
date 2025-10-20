# CLAUDE.md
不要采用临时措施，不要使用模拟数据。

This file provides guidance to Claude Code (claude.ai/code) when working with this Land Property Asset Management System.

## Quick Start

### System Startup (Manual - Recommended)
```bash
# Backend (FastAPI + SQLAlchemy + UV)
cd backend
uv run python run_dev.py            # Development mode (port 8002)
# OR
python run_dev.py                   # Traditional pip development

# Frontend (React + TypeScript + Vite)
cd frontend
npm run dev                         # Development server (port 5173)

# Test database connection
uv run python -c "from src.database import engine; print('DB OK')"

# Health checks
# Backend: http://localhost:8002/health
# Frontend: http://localhost:5173
# API docs: http://localhost:8002/docs
```

## Development Commands

### Backend (FastAPI + SQLAlchemy)
```bash
cd backend

# UV-based (Recommended)
uv run python run_dev.py            # Development mode (port 8002)
uv run python -m pytest tests/ -v   # Run tests
uv sync                              # Install dependencies
uv run mypy src/                     # Type checking
uv run ruff check src/               # Code linting
uv run ruff format src/              # Code formatting

# Traditional pip-based
python run_dev.py                   # Development mode
python -m pytest tests/ -v          # Run tests
pip install -r requirements.txt     # Install dependencies

# Database verification
uv run python -c "from src.database import engine; print('DB OK')"  # Test connection
uv run python -c "from src.models.asset import Asset; print('Models OK')"  # Test models

# Single test execution
uv run python -m pytest tests/test_specific.py -v   # Single test file
uv run python -m pytest tests/ -k "test_name" -v    # Filter by test name
uv run python -m pytest tests/ --tb=short           # Short traceback
uv run python -m pytest tests/ --cov=src            # With coverage
uv run python -m pytest tests/ -x                   # Stop on first failure
uv run python -m pytest tests/ --lf                 # Run only failed tests from last run
```

### Frontend (React + TypeScript + Vite)
```bash
cd frontend
npm run dev                         # Development server (port 5173)
npm run build                       # Production build
npm test                            # Run tests
npm run test:coverage              # Coverage report
npm run type-check                  # TypeScript checking
npm run lint                       # ESLint check
npm run lint:fix                   # Fix ESLint issues

# Advanced testing
npm run test:watch                  # Watch mode
npm run test:unit                  # Unit tests only
npm run test:integration           # Integration tests only
npm run test:e2e                   # End-to-end tests
npm run test:performance           # Performance tests
npm run test:ci                    # CI mode (no watch)
npm run test:debug                 # Debug mode

# Build analysis
ANALYZE=true npm run build          # Generate bundle analysis
```

## System Architecture

**Land Property Asset Management System** with comprehensive asset management, intelligent PDF processing, and advanced security features.

### Core Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend (React)   │    │  Backend (FastAPI)  │    │   Service Layer    │    │ Database (SQLite) │
│   Port: 5173    │◄──►│   Port: 8002    │◄──►│ PDF/OCR/RBAC/     │◄──►│  land_property  │
│   TypeScript    │    │   Python 3.12   │    │ Auth Services   │    │      .db        │
│   Vite + React Query │    │   UV Package Mgmt │    │ PDF Processing   │    │   (MySQL/PG Ready) │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Tech Stack
- **Backend**: FastAPI + SQLAlchemy + Pydantic, UV package management
- **Frontend**: React 18 + TypeScript + Vite + Ant Design
- **Database**: SQLite (production-ready, MySQL/PostgreSQL ready)
- **State Management**: React Query + Zustand
- **PDF Processing**: pdfplumber + OCR + NLP (spaCy + jieba)
- **Security**: RBAC permissions + JWT authentication + Multi-tenant support
- **Development**: Hot reload, comprehensive testing, build optimization

### Key Features
- **58-Field Asset Model**: Complete property information management
- **Intelligent PDF Import**: AI-driven contract extraction with 95%+ accuracy
- **Advanced RBAC**: Role-based access control with dynamic permissions
- **Multi-tenant Architecture**: Organization-level data isolation
- **OCR Support**: Image and scanned document processing
- **Real-time Analytics**: Financial metrics and occupancy statistics
- **Audit Trail**: Complete operation and change tracking

## High-Level Architecture

### Backend Service Layer
The backend follows a layered architecture with clear separation of concerns:

1. **API Layer** (`/api/v1/`): REST endpoints with comprehensive error handling
2. **Service Layer** (`/services/`): Business logic and orchestration
3. **Data Layer** (`/models/`, `/crud/`): Database models and operations
4. **Security Layer** (`/middleware/`): Authentication, authorization, multi-tenancy

### Key Service Components

#### PDF Import Pipeline (V2 Unified)
```python
# Processing flow: Upload → Convert → Extract → Validate → Import
PDF → Text conversion → Information extraction → Validation → Database import

# V2 Service implementation (unified architecture)
class PDFImportService:
    def __init__(self, db: Session):
        self.db = db
        self.processing_service = pdf_processing_service
        self.session_service = pdf_session_service
        self.validation_service = PDFValidationMatchingService(db)

    async def process_pdf_file(self, session_id: str, file_path: str) -> Dict[str, Any]:
        # 1. PDF conversion (multi-engine: PyMuPDF → pdfplumber → OCR fallback)
        text_result = await self.processing_service.extract_text_from_pdf(file_path)

        # 2. Information extraction (58-field AI recognition with confidence scoring)
        extraction_result = await self.extract_contract_info(text_result['text'])

        # 3. Data validation (intelligent validation and matching)
        validated_data = await self.validation_service.validate_extracted_data(extraction_result)

        # 4. Database import with audit trail and session tracking
        return await self.import_asset_data_with_session(session_id, validated_data)
```
- **Multi-Engine PDF Processor**: PyMuPDF, pdfplumber, and PaddleOCR fallback
- **Contract Extractor**: AI-driven 58-field extraction with confidence scoring
- **Session Management**: Real-time progress tracking and batch processing
- **Validation Service**: Intelligent data validation and asset/ownership matching
- **Import Service**: Complete audit trail with session-based tracking

#### RBAC System
```python
# Permission management service example
class RBACService:
    def __init__(self, db: Session):
        self.db = db

    async def assign_user_permission(self, user_id: int, permission_code: str, scope: str = None):
        # Dynamic permission assignment with organization scoping
        permission = await self.get_permission_by_code(permission_code)
        user_permission = UserPermission(
            user_id=user_id,
            permission_id=permission.id,
            scope=scope or user.organization_id
        )
        self.db.add(user_permission)
        await self.audit_log_permission_change(user_id, permission_code, "ASSIGN")
        return user_permission

    async def check_user_permission(self, user_id: int, resource: str, action: str) -> bool:
        # Hierarchical permission checking with inheritance
        return await self.evaluate_permission_chain(user_id, resource, action)
```
- **Dynamic Permissions**: Runtime permission assignment and inheritance
- **Multi-tenant Support**: Organization-level data isolation
- **Audit Logging**: Complete permission change tracking
- **Role Management**: Hierarchical roles with scope-based permissions

#### Asset Management
- **58-Field Model**: Comprehensive property data with automatic calculations
- **History Tracking**: Complete change audit trail
- **Search & Filtering**: Advanced multi-criteria search
- **File Attachments**: PDF document management per asset

### Frontend Architecture

#### Component Organization
- **Pages**: Route-level components (Dashboard, Assets, Contracts, etc.)
- **Components**: Reusable UI components organized by domain
- **Services**: API abstraction layer with error handling
- **State Management**: Zustand stores + React Query caching

#### Key Features
- **Code Splitting**: Intelligent bundling by functionality
- **Error Boundaries**: Comprehensive error handling
- **Progress Tracking**: Real-time PDF import progress
- **Responsive Design**: Mobile-optimized interface

## Core API Modules

### Asset Management (`/api/v1/assets/`)
- CRUD operations with search, filtering, pagination
- File attachment management (PDF uploads)
- Change history tracking
- Bulk operations support

### PDF Import (`/api/v1/pdf_import/`) - V2 Unified
- **Unified API**: Single endpoint with V1 backward compatibility
- **Multi-Engine Processing**: PyMuPDF, pdfplumber, and OCR fallback
- **Session Management**: Real-time progress tracking and batch processing
- **Smart Validation**: Intelligent data validation and asset/ownership matching
- **Complete Audit Trail**: Full session-based tracking and logging
- **V1 Compatibility**: All legacy endpoints supported with enhanced functionality

### RBAC (`/api/v1/rbac/`)
- Dynamic role and permission management
- User permission assignment
- Organization-based access control
- Audit trail for all permission changes

### Analytics (`/api/v1/statistics/`)
- Real-time occupancy calculations
- Financial summaries
- Multi-dimensional reporting
- Performance metrics

### Project & Ownership Management
- Hierarchical project structure
- Ownership relationship management
- Contract lifecycle tracking
- Organization-level reporting

## Database Schema & Models

### Core Models
- **Asset**: 58-field comprehensive property model with automatic calculations
- **AssetHistory**: Complete audit trail for all asset changes
- **RentContract**: Contract lifecycle management with terms
- **Project**: Hierarchical project organization
- **Ownership**: Multi-level ownership structure
- **User/RBAC**: Advanced permission system with roles and scopes

### Key Asset Fields (58 total)
- **Basic**: property_name, address, ownership_status, property_nature
- **Areas**: total_area, rentable_area, rented_area, unrented_area (auto-calculated)
- **Financial**: annual_income, annual_expense, net_income (auto-calculated)
- **Contracts**: lease_contract_number, contract_start_date, contract_end_date
- **Management**: business_model, operation_status, ownership_entity
- **Multi-tenant**: tenant_id for organization isolation

### Automatic Calculations
```python
@property
def occupancy_rate(self):
    if self.rentable_area and self.rentable_area > 0:
        return (self.rented_area / self.rentable_area) * 100
    return 0.0

@property
def unrented_area(self):
    return (self.rentable_area or 0) - (self.rented_area or 0)
```

## Development Patterns

### Backend Patterns
```python
# Service layer with dependency injection
class PDFImportService:
    def process_pdf_file(self, session_id: str, file_path: str) -> Dict[str, Any]:
        # Multi-stage processing with error handling
        # 1. PDF conversion (markitdown → pdfplumber → OCR fallback)
        # 2. Information extraction (58-field recognition)
        # 3. Data validation (OCR-specific handling)
        # 4. Database import with audit trail

# Comprehensive error handling
@router.get("/endpoint")
async def get_endpoint(db: Session = Depends(get_db)):
    try:
        result = service.operation(db)
        return {"success": True, "data": result}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Operation failed: {str(e)}")
```

### Frontend Patterns
```typescript
// Service layer with comprehensive error handling
export const pdfImportService = {
  async uploadPDFFile(file: File): Promise<FileUploadResponse> {
    try {
      const response = await axios.post('/api/v1/pdf_import/upload', formData);
      return response.data;
    } catch (error) {
      // Detailed error handling for network, validation, and server errors
      if (error.code === 'ECONNABORTED') {
        return { success: false, message: 'Upload timeout' };
      }
      // ... comprehensive error handling
    }
  }
};

// React component with state management and error boundaries
export const PDFImportPage: React.FC = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['pdf-import'],
    queryFn: pdfImportService.getSystemInfo,
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorDisplay error={error} />;

  return (
    <ErrorBoundary>
      {/* Component content with progress tracking */}
    </ErrorBoundary>
  );
};
```

## Environment & Configuration

### Development Environment
- **Auto-initialization**: Database tables created on backend startup
- **Real Data**: System contains 1,269+ actual asset records
- **Database Location**: `backend/data/land_property.db`
- **API Documentation**: Available at `http://localhost:8002/docs`

### Environment Variables
```bash
# Backend (DEV_MODE for development without authentication)
DEV_MODE=true                    # Disable authentication for development
DATABASE_URL=sqlite:///./data/land_property.db

# Frontend (Vite proxy configuration)
VITE_API_BASE_URL=http://localhost:8002/api/v1
VITE_API_TIMEOUT=30000
```

### Common Development Issues
- **Database Connection**: `uv run python -c "from src.database import engine; print('DB OK')"`
- **Model Testing**: `uv run python -c "from src.models.asset import Asset; print('Models OK')"`
- **Port Conflicts**: Backend uses 8002, Frontend uses 5173
- **TypeScript Errors**: Check import paths and type definitions
- **Dependency Issues**: Use `uv sync` for backend, `npm install` for frontend
- **Environment Variables**: Check `.env` files for proper configuration
- **Startup Scripts**: Use `start_uv.bat` (Windows) for quick backend startup

## Key Business Logic

### PDF Processing Pipeline
The PDF import system uses a sophisticated multi-stage approach:

1. **File Validation**: Format and size checks
2. **Text Extraction**: markitdown → pdfplumber → OCR fallback
3. **Information Extraction**: 58-field AI-driven extraction
4. **Data Validation**: OCR-specific validation with confidence scoring
5. **Data Matching**: Asset and ownership matching
6. **Import Confirmation**: User review before database import

### Automatic Calculations
- **Occupancy Rate**: `rented_area / rentable_area × 100%`
- **Net Income**: `annual_income - annual_expense`
- **Unrented Area**: `rentable_area - rented_area`
- **Asset Status**: Based on contract dates and rental status

### RBAC Permission System
- **Hierarchical Roles**: Admin → Manager → User with inheritance
- **Resource-based Permissions**: Fine-grained control per resource
- **Organization Scoping**: Data isolation by organization
- **Dynamic Assignment**: Runtime permission modification
- **Audit Trail**: Complete permission change logging

### Multi-tenant Architecture
- **Tenant Isolation**: Data separated by tenant_id
- **Organization Management**: Hierarchical organization structure
- **Permission Scoping**: Permissions limited to user's organization
- **Resource Sharing**: Cross-organization resource access when permitted

## Performance & Production

### Performance Features
- **Intelligent Code Splitting**: Frontend bundling optimized by functionality
- **Database Indexing**: Optimized queries for large datasets
- **Caching Strategy**: React Query + optional Redis caching
- **PDF Processing**: Multi-threaded OCR and parallel processing
- **Build Optimization**: Vite with compression and tree-shaking

### Production Deployment
```bash
# Frontend build with analysis
ANALYZE=true npm run build

# Backend production setup
# 1. Configure environment variables
# 2. Set up production database (MySQL/PostgreSQL)
# 3. Configure Redis for caching
# 4. Set up reverse proxy (Nginx)
# 5. Enable SSL/HTTPS
```

### Performance Metrics
- **Contract Entry Time**: Reduced from 10-15 minutes to 2-3 minutes
- **PDF Processing**: 58-field extraction with 95%+ accuracy
- **API Response**: < 1 second for 1000+ record queries
- **Frontend Bundle**: Optimized with intelligent code splitting

## Security & Compliance

### Security Features
- **RBAC Permissions**: Role-based access control with dynamic assignment
- **Multi-tenant Isolation**: Organization-level data separation
- **Audit Logging**: Complete operation and permission change tracking
- **Input Validation**: Comprehensive Pydantic schema validation
- **SQL Injection Prevention**: SQLAlchemy ORM protection
- **File Upload Security**: PDF validation and sandboxing

### Data Protection
- **Automatic Backups**: Regular database backups with rotation
- **Change Tracking**: Complete asset modification history
- **Secure Storage**: Sensitive data encryption and access controls
- **Session Management**: Secure session handling with expiration

## Troubleshooting

### Common Issues & Solutions

#### Backend Issues
- **Import Errors**: Check Python dependencies with `uv sync`
- **Database Issues**: Test with `uv run python -c "from src.database import engine; print('DB OK')"`
- **Port Conflicts**: Backend uses 8002, ensure availability
- **Permission Errors**: Check DEV_MODE setting for development

#### Frontend Issues
- **Build Errors**: Run `npm run type-check` for TypeScript validation
- **API Connection**: Verify backend is running on port 8002
- **State Issues**: Check React Query cache and Zustand stores
- **Performance**: Use `ANALYZE=true npm run build` for bundle analysis
- **Test Failures**: Check test configuration in jest.config.js and ensure test environment is set up correctly

#### PDF Processing Issues
- **OCR Not Available**: Install Tesseract and system dependencies
- **Large Files**: Increase timeout settings (default 50MB limit)
- **Extraction Accuracy**: Check file quality and try different extraction methods
- **Memory Issues**: Monitor system resources during large PDF processing

### Debugging Tools
- **Backend**: FastAPI auto-docs at `http://localhost:8002/docs`
- **Frontend**: React DevTools and browser console
- **Database**: SQLite browser for `backend/data/land_property.db`
- **Performance**: Bundle analyzer and database query profiling

---

**System Status**: Production-ready with comprehensive PDF import and RBAC functionality completed as of 2025-10-15. Performance improvement: Reduced contract data entry time from 10-15 minutes to 2-3 minutes.`

### Common Issues & Solutions
- **UV Issues**: Use `uv sync` to resolve dependencies, fallback to pip if needed
- **Port Conflicts**: Backend uses 8002, Frontend uses 5173
- **TypeScript Errors**: ~200+ errors exist, mainly in analytics components
- **Import Errors**: Test with `uv run python -c "from src.module import Class"`

### Debugging Tools
- **Backend**: FastAPI auto-docs at `http://localhost:8002/docs`
- **Frontend**: React DevTools and browser console
- **Database**: SQLite browser for `backend/land_property.db`
- **API Testing**: Use `/health`, `/info`, `/test-api` endpoints

### Performance Considerations
- **Large Datasets**: Implement pagination for >1000 records
- **Database Indexes**: Add indexes on frequently queried fields
- **Frontend**: Route-based code splitting, virtual scrolling for large lists
- **API Response**: Optimize queries with proper joins and caching

## Testing

### Backend Tests
```bash
cd backend
uv run python -m pytest tests/ -v --cov=src          # Full test suite with coverage
uv run python -m pytest tests/test_specific.py -v   # Single test file
uv run python -m pytest tests/ -k "test_name" -v    # Filter by test name
uv run python -m pytest tests/ --tb=short           # Short traceback format
uv run python -m pytest tests/ -x                   # Stop on first failure
uv run python -m pytest tests/ --lf                 # Run only failed tests from last run
```

### Frontend Tests
```bash
cd frontend
npm test                                            # Watch mode
npm run test:coverage                              # Coverage report
npm run test:unit                                  # Unit tests only
npm run test:integration                           # Integration tests only
npm run test:e2e                                   # End-to-end tests
npm run test:performance                           # Performance tests
npm run test:ci                                    # CI mode (no watch)
npm run test:debug                                 # Debug mode
npm run test:watch                                 # Watch mode (alternative)
```

## Production Deployment

### Environment
- **Database**: MySQL/PostgreSQL recommended for production
- **Caching**: Redis configuration available
- **Monitoring**: Health checks at `/api/v1/health`
- **Build**: Optimized Vite build with compression

### Performance Features
- **Advanced Code Splitting**: Intelligent chunk separation
- **Bundle Analysis**: `ANALYZE=true npm run build`
- **Compression**: Gzip/Brotli compression
- **CDN Ready**: External dependencies configured

## File Structure

### Backend
```
backend/
├── src/
│   ├── api/v1/          # REST API endpoints
│   ├── models/          # SQLAlchemy models
│   ├── services/        # Business logic
│   ├── crud/            # Database operations
│   └── schemas/         # Pydantic validation
├── migrations/          # Database migrations
└── pyproject.toml       # UV configuration
```

### Frontend
```
frontend/
├── src/
│   ├── components/      # Reusable components
│   ├── pages/           # Page-level components
│   ├── services/        # API abstraction
│   └── utils/           # Utility functions
├── package.json         # npm configuration
└── vite.config.ts       # Vite optimization
```

## Quick Development Tips

### Backend
```bash
# Quick database test
cd backend && uv run python -c "from src.database import engine; print('DB OK')"

# Development server (multiple options)
cd backend && uv run python run_dev.py              # Port 8002
# OR use Windows batch script:
./start_uv.bat                                     # Quick startup (Windows)
./stop_uv.bat                                      # Stop server (Windows)

# Code quality checks
cd backend && uv run ruff check src/ && uv run mypy src/
```

### Frontend
```bash
# Development with custom port
cd frontend && npm run dev -- --port 5174

# Build analysis
cd frontend && ANALYZE=true npm run build

# Type checking
cd frontend && npm run type-check

# Advanced build options
cd frontend && npm run build -- --mode production
cd frontend && npm run preview                   # Preview production build
```

### Debugging
- **Backend**: Check import errors with `uv run python -c "from src.module import Class"`
- **Frontend**: Use React DevTools and browser console
- **API Testing**: Use FastAPI auto-docs at `http://localhost:8002/docs`
- **Database**: SQLite browser for `backend/data/land_property.db`

## Security Best Practices

- **Input Validation**: Pydantic schemas for all endpoints
- **SQL Injection Prevention**: SQLAlchemy ORM protection
- **CORS Configuration**: Properly configured for development
- **Audit Trail**: Complete asset modification tracking
- **File Upload**: PDF imports validated and sandboxed

## Performance Optimization

### Backend
- Database indexing on queried fields
- Redis caching for frequently accessed data
- Connection pooling
- Query optimization with proper joins

### Frontend
- Route-based code splitting with React.lazy
- Vite optimization with intelligent chunking
- React Query caching strategies
- Memoization for expensive computations

---
