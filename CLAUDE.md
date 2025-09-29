# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Primary Development Workflow
```bash
start.bat          # One-click full system startup (backend + frontend) - Windows
start.sh           # One-click full system startup (backend + frontend) - Unix/macOS
stop.bat           # Stop all running services - Windows
stop.sh            # Stop all running services - Unix/macOS
```

### Backend Development
```bash
cd backend
python run.py                       # Production mode (port 8001)
python run_dev.py                   # Development mode with hot reload
python -m pytest tests/             # Run backend tests
python src/init_data.py             # Initialize with sample data
python src/services/backup_service.py  # Create backup
```

### Frontend Development
```bash
cd frontend
npm run dev                         # Development server (port 5173)
npm run build                       # Production build
npm test                            # Run frontend tests
npm run lint                        # Code quality checks
npm run type-check                  # TypeScript type checking
```

### Testing Commands
```bash
# Backend tests
cd backend
python -m pytest tests/ -v          # Run all tests with verbose output
python -m pytest tests/test_api.py  # Run specific API tests
python -m pytest tests/ --cov=src   # Run with coverage report
python test_api.py                   # Quick API functionality test
python test_new_features.py          # Test new features
python test_simple_relationships.py  # Test database relationships

# Frontend tests
cd frontend
npm test                            # Run all tests
npm run test:watch                  # Run tests in watch mode
npm run test:coverage               # Run tests with coverage
npm run test:unit                   # Run unit tests only
npm run test:integration            # Run integration tests
npm run test:ci                     # Run CI-friendly tests
```

### Database Operations
```bash
cd backend
python -c "from src.database import engine; print('DB OK')"  # Test database connection
python src/init_data.py             # Initialize with sample data
# Apply database migrations from backend/migrations/
python scripts/data_migration_tool.py    # Data migration utilities
python test_relationships.py         # Test database relationships
python check_table.py               # Check table structure
python create_projects_table.py     # Create projects table if missing
```

## Architecture Overview

This is a **Land Property Asset Management System** with 58-field comprehensive asset records, real-time occupancy calculations, and financial analysis capabilities.

### Backend Architecture (FastAPI)
- **Entry Point**: `backend/src/main.py` - FastAPI application configuration with comprehensive error handling
- **API Layer**: `backend/src/api/v1/` - RESTful endpoints organized by domain
  - Assets API (`/api/v1/assets/`) - Core CRUD operations with advanced search and filtering
  - Statistics API (`/api/v1/statistics/`) - Real-time occupancy and financial analytics
  - Excel API (`/api/v1/excel/`) - Import/export with standardized templates
  - Backup API (`/api/v1/backup/`) - Data backup and recovery
  - Dictionary API (`/api/v1/dictionaries/`) - System dictionaries and enums
  - Admin API (`/api/v1/admin/`) - System administration and configuration
  - Project API (`/api/v1/project/`) - Project management endpoints
  - Ownership API (`/api/v1/ownership/`) - Ownership structure management
  - Rent Contract API (`/api/v1/rent_contract/`) - Rental contract management
  - Custom Fields API (`/api/v1/custom_fields/`) - Custom field definitions
  - Organization API (`/api/v1/organization/`) - Multi-tenant organization support
- **Business Logic**: `backend/src/services/` - Core business logic and calculations
  - `statistics.py` - Real-time occupancy rate calculations and financial analysis
  - `excel_export.py` - Excel export with 58-field mapping
  - `backup_service.py` - Automated backup and recovery
  - `rent_contract_excel.py` - Rental contract Excel operations
  - `asset_calculator.py` - Asset calculations and metrics
- **Data Access**: `backend/src/crud/` - Database operations with repository pattern
- **Models**: `backend/src/models/` - SQLAlchemy ORM models with comprehensive relationships
- **Validation**: `backend/src/schemas/` - Pydantic schemas for request/response validation
- **Utilities**: `backend/src/utils/` - Utility functions and helpers

### Frontend Architecture (React + TypeScript)
- **Entry Point**: `frontend/src/main.tsx` - React application with React Query and Ant Design
- **Routing**: `frontend/src/routes/` - Application route configuration with lazy loading
- **Pages**: `frontend/src/pages/` - Page-level components organized by feature
  - Dashboard page with real-time statistics
  - Asset management pages with advanced search and filtering
  - Project management pages (new)
  - Ownership management pages (new)
  - Rental contract management pages (new)
  - Analytics and reporting pages
- **Components**: `frontend/src/components/` - Reusable UI components
  - Asset components for CRUD operations
  - Project components for project management
  - Ownership components for ownership structure
  - Rental components for contract management
  - Layout components with modern responsive design
  - Form components with validation using react-hook-form + Zod
- **Services**: `frontend/src/services/` - API abstraction layer with Axios
  - `assetService.ts` - Asset CRUD operations
  - `projectService.ts` - Project management
  - `ownershipService.ts` - Ownership structure
  - `rentContractService.ts` - Rental contracts
  - `dictionaryService.ts` - Dictionary management
- **State Management**: React Query for server state, Zustand for client state
- **Types**: `frontend/src/types/` - Comprehensive TypeScript definitions
- **Utils**: `frontend/src/utils/` - Utility functions and helpers

### Key Business Logic
- **Automatic Calculations**:
  - Occupancy rate = rented area ÷ rentable area × 100%
  - Net income = annual income - annual expense
  - Unrented area = rentable area - rented area
- **Financial Metrics**: Real-time calculation of revenue, expenses, and profit
- **Audit Trail**: Complete change tracking for all asset modifications
- **Excel Integration**: Standardized templates supporting all 58 fields
- **Advanced Search**: Multi-criteria search with filtering capabilities

## API Module Documentation

### Core Business Modules

#### Assets Management API (`/api/v1/assets/`)
- **GET /assets** - Asset list with advanced search, filtering, and pagination
- **POST /assets** - Create new asset with 58-field validation
- **PUT /assets/{id}** - Update asset with full validation
- **DELETE /assets/{id}** - Delete asset with cascade protection
- **GET /assets/{id}/history** - Asset modification history
- **GET /assets/ownership-entities** - Ownership entity dropdown options
- **GET /assets/business-categories** - Business category dropdown options
- **GET /assets/statistics/summary** - Asset statistics summary

#### Statistics API (`/api/v1/statistics/`)
- **GET /statistics/basic** - Basic statistics data
- **GET /statistics/summary** - Statistics summary information
- **GET /statistics/area-summary** - Area summary statistics
- **GET /statistics/financial-summary** - Financial summary statistics
- **GET /statistics/occupancy-rate/overall** - Overall occupancy rate statistics
- **GET /statistics/occupancy-rate/by-category** - Occupancy rate statistics by category

#### Project Management API (`/api/v1/project/`)
- **GET /project** - Project list with search and filtering
- **POST /project** - Create new project
- **PUT /project/{id}** - Update project
- **DELETE /project/{id}** - Delete project
- **PUT /project/{id}/toggle-status** - Toggle project active status
- **GET /project/statistics/summary** - Project statistics

#### Ownership Management API (`/api/v1/ownership/`)
- **GET /ownership** - Ownership structure list
- **POST /ownership** - Create new ownership
- **PUT /ownership/{id}** - Update ownership
- **DELETE /ownership/{id}** - Delete ownership
- **GET /ownership/dropdown-options** - Dropdown options for forms
- **GET /ownership/statistics/summary** - Ownership statistics

#### Rental Contract API (`/api/v1/rent_contract/`)
- **GET /rent_contract/contracts** - Rental contract list
- **POST /rent_contract/contracts** - Create rental contract
- **PUT /rent_contract/contracts/{id}** - Update rental contract
- **DELETE /rent_contract/contracts/{id}** - Delete rental contract
- **GET /rent_contract/ledgers** - Rental ledger records
- **POST /rent_contract/ledgers/batch-update** - Batch update ledger status
- **GET /rent_contract/statistics/summary** - Rental statistics

### Supporting Modules

#### Dictionary Management
- **System Dictionaries** (`/api/v1/system_dictionaries/`) - Traditional dictionary management
- **Enum Fields** (`/api/v1/enum_fields/`) - Advanced enum management with hierarchy
- **Custom Fields** (`/api/v1/custom_fields/`) - Dynamic field definitions
- **Unified Dictionary** (`/api/v1/dictionaries/`) - Integrated dictionary interface

#### Organization API (`/api/v1/organization/`)
- **GET /organization** - Organization structure with tree support
- **POST /organization** - Create organization
- **PUT /organization/{id}** - Update organization
- **DELETE /organization/{id}** - Delete organization
- **GET /organization/{id}/path** - Organization path to root

#### Admin API (`/api/v1/admin/`)
- **POST /admin/reset-database** - Reset database (requires confirmation)
- **POST /admin/clear-all-data** - Clear all data (requires confirmation)
- **GET /admin/system-info** - System information and statistics

## Database Schema

### Core Asset Fields (Asset Model)
- **Basic Information**: project_name, property_name, address, ownership_status, property_nature
- **Area Management**: total_area, land_area, total_building_area, actual_property_area, rentable_area, rented_area, unrented_area
- **Occupancy Calculations**: occupancy_rate (auto-calculated), include_in_occupancy_rate
- **Usage Information**: certificated_usage, actual_usage, business_category
- **Tenant Information**: tenant_name, tenant_type, lease_contract_number
- **Contract Management**: contract_start_date, contract_end_date, contract_status, monthly_rent, deposit
- **Financial Data**: annual_income, annual_expense, net_income (auto-calculated)
- **Management Fields**: business_model, operation_status, ownership_entity
- **System Fields**: data_status, version, audit_status, created_at, updated_at

### Supporting Models
- **AssetHistory**: Complete audit trail for all asset modifications
- **AssetDocument**: Document management for assets
- **SystemDictionary**: Centralized dictionary management for enums and lookups
- **Organization**: Multi-tenant organization support with tree structure
- **Project**: Project management with asset association
- **Ownership**: Ownership structure management
- **RentContract**: Comprehensive contract management with ledger system
- **CustomField**: Dynamic field definitions for extensibility

### Database Configuration
- **Database**: SQLite (production-ready, supports MySQL/PostgreSQL)
- **ORM**: SQLAlchemy 2.0 with declarative base
- **File Location**: `backend/land_property.db`
- **Test Data**: 1,269 pre-populated asset records for testing
- **Session Management**: Dependency injection with `get_db()` function
- **Migrations**: SQL-based migrations in `backend/migrations/`
- **Auto-initialization**: Database tables are auto-created on application startup

## Frontend Component Library

### Core Components

#### Asset Components (`src/components/Asset/`)
- **AssetCard** - Asset display card with key information
- **AssetList** - Asset list with search, filter, and pagination
- **AssetForm** - Asset creation and editing form
- **AssetSearch** - Advanced search interface
- **AssetDetailInfo** - Detailed asset information display
- **AssetAnalyticsPage** - Asset analytics and reporting page with charts and statistics

#### Project Components (`src/components/Project/`)
- **ProjectCard** - Project display card
- **ProjectList** - Project list with management features
- **ProjectForm** - Project creation and editing form
- **ProjectStats** - Project statistics display

#### Ownership Components (`src/components/Ownership/`)
- **OwnershipCard** - Ownership structure display
- **OwnershipList** - Ownership list management
- **OwnershipForm** - Ownership creation and editing form
- **OwnershipTree** - Tree view of ownership structure

#### Rental Components (`src/components/Rental/`)
- **ContractCard** - Rental contract display
- **ContractList** - Contract list management
- **ContractForm** - Contract creation and editing form
- **LedgerTable** - Rental ledger management

### Layout Components (`src/components/Layout/`)
- **ModernAppLayout** - Main application layout with sidebar
- **AppSidebar** - Navigation sidebar with menu items
- **AppBreadcrumb** - Breadcrumb navigation
- **BusinessLayout** - Business-specific layout

### Utility Components (`src/components/`)
- **ErrorBoundary** - Error boundary for component error handling
- **ProgressIndicator** - Loading and progress indicators
- **SuccessNotification** - Success message notifications
- **PerformanceMonitor** - Performance monitoring utilities

## Development Standards and Patterns

### Backend Development Patterns

#### API Design Standards
- **RESTful Design**: Follow REST principles with proper HTTP methods
- **Response Format**: Consistent `{success, message, data}` response format
- **Error Handling**: Comprehensive error handling with custom exception classes
- **Validation**: Pydantic models for request/response validation
- **Documentation**: OpenAPI/Swagger documentation for all endpoints
- **CORS**: Pre-configured for development ports (3000, 5173, 5174, 8001)

#### Code Organization
```python
# Standard API endpoint pattern
@router.get("/endpoint")
async def get_endpoint(
    param: str = Query(..., description="Parameter description"),
    db: Session = Depends(get_db)
):
    """Endpoint description"""
    try:
        result = service_layer.operation(db, param)
        return {"success": True, "data": result}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Operation failed: {str(e)}")
```

#### Exception Handling Pattern
The system uses comprehensive exception handling with custom exception classes:
- `AssetNotFoundError`: Asset not found (404)
- `DuplicateAssetError`: Duplicate asset name (409)
- `BusinessLogicError`: Business logic violations (400)
- `ValidationError`: Pydantic validation errors (400)
- `RequestValidationError`: FastAPI request validation (422)
- Global exception handlers for consistent error responses

#### Database Patterns
- **CRUD Layer**: Separate CRUD operations in `backend/src/crud/`
- **Service Layer**: Business logic in `backend/src/services/`
- **Repository Pattern**: Abstract database operations
- **Transaction Management**: Proper transaction handling
- **Relationships**: Proper SQLAlchemy relationship definitions

### Frontend Development Patterns

#### Component Patterns
```typescript
// Standard React component pattern
interface ComponentProps {
  data: ItemType;
  onEdit: (item: ItemType) => void;
  onDelete: (id: string) => void;
}

export const Component: React.FC<ComponentProps> = ({ data, onEdit, onDelete }) => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['component-data', data.id],
    queryFn: () => fetchComponentData(data.id),
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorDisplay error={error} />;

  return (
    <div className="component-container">
      {/* Component content */}
    </div>
  );
};
```

#### State Management Patterns
```typescript
// React Query for server state
const { data, isLoading, error, refetch } = useQuery({
  queryKey: ['assets', { page, pageSize, search, filters }],
  queryFn: () => assetService.getAssets({ page, pageSize, search, filters }),
  retry: 2,
  staleTime: 5 * 60 * 1000,
});

// Zustand for client state
export const useAssetStore = create<AssetState>()(
  devtools(
    (set, get) => ({
      assets: [],
      setAssets: (assets) => set({ assets }),
      addAsset: (asset) => set((state) => ({ assets: [...state.assets, asset] })),
      updateAsset: (id, updates) => set((state) => ({
        assets: state.assets.map(asset => asset.id === id ? { ...asset, ...updates } : asset)
      })),
    }),
    { name: 'asset-store' }
  )
);
```

#### Service Layer Patterns
```typescript
// API Service pattern
export class AssetService {
  private api: ApiClient;

  constructor() {
    this.api = new ApiClient();
  }

  async getAssets(params?: AssetSearchParams): Promise<ApiResponse<AssetListResponse>> {
    return this.api.get<AssetListResponse>('/assets', { params });
  }

  async createAsset(data: AssetCreateRequest): Promise<ApiResponse<Asset>> {
    return this.api.post<Asset>('/assets', data);
  }

  async updateAsset(id: string, data: AssetUpdateRequest): Promise<ApiResponse<Asset>> {
    return this.api.put<Asset>(`/assets/${id}`, data);
  }

  async deleteAsset(id: string): Promise<ApiResponse<void>> {
    return this.api.delete<void>(`/assets/${id}`);
  }
}
```

### Testing Standards

#### Backend Testing
```python
# Test file naming: test_*.py
import pytest
from fastapi.testclient import TestClient

def test_create_asset(client: TestClient, db_session):
    """Test asset creation"""
    asset_data = {
        "property_name": "Test Property",
        "address": "Test Address",
        # ... other fields
    }

    response = client.post("/api/v1/assets/", json=asset_data)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["property_name"] == asset_data["property_name"]

@pytest.fixture
def db_session():
    """Database session fixture"""
    # Setup
    session = next(get_db())
    yield session
    # Cleanup
    session.close()
```

#### Frontend Testing
```typescript
// Component testing with React Testing Library
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AssetList } from './AssetList';

describe('AssetList', () => {
  it('renders asset list correctly', () => {
    const mockAssets = [
      { id: '1', property_name: 'Test Asset 1', address: 'Address 1' },
      { id: '2', property_name: 'Test Asset 2', address: 'Address 2' },
    ];

    render(<AssetList assets={mockAssets} />);

    expect(screen.getByText('Test Asset 1')).toBeInTheDocument();
    expect(screen.getByText('Test Asset 2')).toBeInTheDocument();
  });

  it('calls onEdit when edit button is clicked', () => {
    const mockOnEdit = jest.fn();
    const mockAssets = [{ id: '1', property_name: 'Test Asset', address: 'Address' }];

    render(<AssetList assets={mockAssets} onEdit={mockOnEdit} />);

    fireEvent.click(screen.getByText('Edit'));
    expect(mockOnEdit).toHaveBeenCalledWith(mockAssets[0]);
  });
});
```

## Performance Optimization

### Backend Optimization
- **Database Indexing**: Proper indexes on frequently queried fields
- **Pagination**: Implement pagination for large datasets
- **Caching**: Redis caching for frequently accessed data
- **Query Optimization**: Optimize SQLAlchemy queries with proper joins
- **Connection Pooling**: Database connection pooling for better performance

### Frontend Optimization
- **Code Splitting**: Route-based code splitting with React.lazy
- **Bundle Optimization**: Vite optimization with proper chunking
- **Image Optimization**: Lazy loading and optimization for images
- **Virtualization**: Virtual scrolling for large lists
- **Caching**: React Query caching strategies
- **Memoization**: React.memo and useMemo for expensive computations

## Common Issues and Solutions

### Database Connection Issues
- **Database File**: Ensure SQLite database exists at `backend/land_property.db`
- **Permissions**: Verify read/write permissions on the database file
- **Initialization**: Database is auto-initialized on application startup via `backend/src/main.py`
- **Migration**: Use SQL scripts in `backend/migrations/` for schema changes
- **Table Creation**: Tables are automatically created on startup, no manual intervention needed

### CORS Issues
- **Development**: Backend CORS configured for ports 3000, 5173, 5174
- **Configuration**: Update CORS settings in `backend/src/main.py` if changing ports
- **Production**: Configure proper nginx/Apache reverse proxy settings

### Build and Runtime Issues
- **Frontend Build**: Clear node_modules and reinstall if build fails
- **Python Dependencies**: Check backend/requirements.txt for missing packages
- **TypeScript Errors**: Run `npm run type-check` to identify type issues
- **Port Conflicts**: Use `stop.bat` to clear port 8001/5173 before starting

### Excel Import/Export
- **Templates**: Use standardized Excel templates from the system export feature
- **Field Mapping**: Verify all 58 fields match the expected schema
- **Encoding**: Handle UTF-8 encoding properly for Chinese characters
- **Validation**: Ensure data passes validation before importing

### Performance Issues
- **Large Datasets**: Implement pagination for asset listings (>1000 records)
- **Slow Queries**: Add database indexes on frequently queried fields
- **Memory Usage**: Monitor frontend memory usage with large asset lists
- **API Response**: Use compression and caching for expensive operations

### Development Environment Setup
- **Python Version**: Requires Python 3.8+ (verified in start.bat)
- **Node.js Version**: Requires Node.js 18+ (verified in start.bat)
- **Environment Variables**: Check .env files for proper configuration
- **Dependencies**: Run start.bat for automatic dependency installation
- **One-Click Startup**: Use start.bat (Windows) or start.sh (Unix/macOS) for full system startup
- **Service Management**: Use stop.bat or stop.sh to stop all running services