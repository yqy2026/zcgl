# Project Context

## Purpose

The Land Property Asset Management System (土地物业资产管理系统) is a comprehensive full-stack web application designed to streamline real estate asset management, rental contract administration, and property operations. The system provides:

- **Centralized Asset Management**: Track and manage diverse property portfolios including land, buildings, and residential/commercial units
- **Rental Contract Automation**: Digitize contract lifecycle management with PDF processing, OCR capabilities, and automated data extraction
- **Stakeholder Management**: Manage ownership structures, tenant relationships, and organizational hierarchies
- **Financial Analytics**: Provide comprehensive reporting on rental income, occupancy rates, and asset performance
- **Regulatory Compliance**: Ensure adherence to Chinese property management regulations and documentation requirements

**Primary Goals**:
- Reduce manual paperwork through digital transformation
- Improve operational efficiency in property management workflows
- Provide data-driven insights for asset optimization
- Enable scalable management of growing property portfolios
- Support Chinese/English bilingual operations

## Tech Stack

### Frontend Stack
- **React 18** with TypeScript 5.x - Modern UI framework with strict type safety
- **Ant Design 5.x** - Enterprise-class UI component library with Chinese localization
- **Vite** - Next-generation build tool with fast HMR and optimized builds
- **Zustand** - Lightweight state management for global application state
- **React Query (TanStack Query)** - Server state management and caching
- **React Router 6** - Declarative routing with lazy loading and performance monitoring
- **TypeScript** - 95%+ type coverage with strict mode enabled

### Backend Stack
- **FastAPI 0.104+** - Modern async Python web framework with automatic OpenAPI documentation
- **Python 3.12** - Latest stable Python with enhanced performance and type hints
- **SQLAlchemy 2.0** - Modern async ORM with relationship mapping and query optimization
- **Pydantic v2** - Data validation and serialization settings management
- **Alembic** - Database migration management
- **Redis** - Caching layer for session management and API response caching
- **SQLite** - Development database with PostgreSQL compatibility for production

### PDF Processing & OCR
- **PaddleOCR** - Chinese-optimized OCR engine with high accuracy for mixed text documents
- **pdfplumber** - PDF text extraction with table structure preservation
- **python-multipart** - File upload handling with progress tracking
- **Pillow** - Image processing for PDF quality assessment

### Development & Deployment
- **Docker Compose** - Multi-container deployment with Nginx reverse proxy
- **Nginx** - Static asset serving and SSL termination
- **pytest** - Async testing framework with comprehensive coverage reporting
- **Jest + Testing Library** - Frontend component testing with React support
- **ESLint + Prettier** - Code quality and formatting
- **ruff + mypy** - Python linting and type checking

## Project Conventions

### Code Style

#### Frontend (TypeScript/React)
- **Naming Conventions**:
  - Components: PascalCase (`AssetForm.tsx`, `RentContractModal.tsx`)
  - Files: kebab-case for utilities (`api-client.ts`), PascalCase for components
  - Variables/Functions: camelCase (`getUserProfile`, `assetList`)
  - Constants: UPPER_SNAKE_CASE (`API_BASE_URL`, `DEFAULT_PAGE_SIZE`)
  - Types/Interfaces: PascalCase with descriptive suffixes (`UserProfile`, `ApiResponse<T>`)

- **File Structure**:
  ```
  src/
  ├── components/FeatureName/
  │   ├── ComponentName.tsx
  │   ├── ComponentName.test.tsx
  │   ├── types.ts
  │   └── index.ts
  ├── services/
  │   ├── featureService.ts
  │   └── __tests__/
  ├── hooks/
  │   ├── useFeature.ts
  │   └── index.ts
  ```

- **Code Organization**:
  - Co-locate tests with source files in `__tests__/` directories
  - Export barrel imports (`index.ts`) for clean imports
  - Separate types into dedicated `types.ts` files
  - Use functional components with hooks exclusively

#### Backend (Python/FastAPI)
- **Naming Conventions**:
  - Files: snake_case (`pdf_processing_service.py`, `asset_repository.py`)
  - Classes: PascalCase (`AssetService`, `PDFProcessingService`)
  - Functions/Variables: snake_case (`process_pdf_document`, `user_repository`)
  - Constants: UPPER_SNAKE_CASE (`MAX_FILE_SIZE`, `DEFAULT_TIMEOUT`)
  - Private members: leading underscore (`_validate_input`, `_cache_manager`)

- **Code Organization**:
  ```
  src/
  ├── models/          # SQLAlchemy ORM models
  ├── schemas/         # Pydantic request/response models
  ├── api/v1/          # API endpoints (versioned architecture)
  ├── services/        # Business logic layer
  ├── crud/            # Database operations
  ├── core/            # Configuration and utilities
  └── middleware/      # Request/response processing
  ```

### Architecture Patterns

#### Backend Architecture
- **Router Registry System**: Centralized route management with automatic registration
  - All APIs registered through `core/router_registry.py`
  - Unified versioned API architecture (`/api/v1/*`)
  - Automatic version prefix application and route management

- **Dependency Injection**: Centralized DI container for service management
  - Service lifetimes: Singleton for services, Scoped per request
  - Interface-based design with implementation abstractions
  - Automatic dependency resolution in FastAPI endpoints

- **Repository Pattern**: Enhanced base classes with CRUD operations
  - Generic repository with async operations
  - Relationship handling and eager loading optimization
  - Built-in audit fields and soft delete support

- **Service Layer**: Business logic separation
  - Transaction management with rollbacks
  - Error handling with internationalized messages
  - Performance monitoring and caching integration

#### Frontend Architecture
- **Component Architecture**:
  - Smart components (container components) for data fetching
  - Dumb components (presentational) for pure UI rendering
  - Error boundaries for graceful failure handling
  - Lazy loading with route-based code splitting

- **State Management**:
  - **Zustand** for global UI state, user preferences, auth tokens
  - **React Query** for server state, caching, and synchronization
  - **Local state** for component-specific UI interactions

- **API Client Architecture**:
  - **EnhancedApiClient**: Centralized HTTP client with retry logic
  - **Response Extraction**: Intelligent data extraction from various API formats
  - **Error Handling**: Unified error processing with user-friendly messages

### Testing Strategy

#### Backend Testing
- **Test Categories**:
  - **Unit tests** (`@pytest.mark.unit`): Fast, isolated component testing
  - **Integration tests** (`@pytest.mark.integration`): Database and service integration
  - **API tests** (`@pytest.mark.api`): Full endpoint testing with test database
  - **Slow tests** (`@pytest.mark.slow`): PDF processing and external service testing

- **Requirements**:
  - 95%+ code coverage requirement for new code
  - Async testing with pytest-asyncio
  - Database fixtures with transaction rollback
  - Mock external services (OCR, file systems)

- **Test Structure**:
  ```python
  # tests/unit/services/test_asset_service.py
  class TestAssetService:
      async def test_create_asset_success(self, db_session):
          # Arrange
          service = AssetService(db_session)
          asset_data = AssetCreate(name="Test Asset")

          # Act
          result = await service.create_asset(asset_data)

          # Assert
          assert result.name == "Test Asset"
  ```

#### Frontend Testing
- **Test Categories**:
  - **Unit tests**: Individual component testing with React Testing Library
  - **Integration tests**: Component interaction and user flow testing
  - **API tests**: Mock server responses and error handling

- **Requirements**:
  - Focus on user behavior over implementation details
  - Mock external dependencies (API calls, browser APIs)
  - Test error states and loading states
  - Accessibility testing with jest-axe

- **Test Structure**:
  ```typescript
  // src/components/Asset/__tests__/AssetForm.test.tsx
  describe('AssetForm', () => {
    it('should submit form with valid data', async () => {
      // Arrange
      const mockSubmit = jest.fn()

      // Act
      render(<AssetForm onSubmit={mockSubmit} />)
      // ... user interactions

      // Assert
      expect(mockSubmit).toHaveBeenCalledWith(expectedData)
    })
  })
  ```

### Git Workflow

#### Branching Strategy
- **main**: Production-ready code, protected branch
- **develop**: Integration branch for feature completion
- **feature/***: Individual feature development
- **hotfix/***: Critical production fixes
- **release/***: Release preparation and final testing

#### Commit Convention
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code formatting (no functional change)
- `refactor`: Code improvement without feature addition
- `test`: Adding or updating tests
- `chore`: Maintenance tasks, dependency updates

**Examples**:
```
feat(auth): add JWT token refresh mechanism
fix(pdf): resolve OCR encoding issues for Chinese text
docs(api): update OpenAPI documentation
refactor(services): implement dependency injection pattern
test(assets): add integration tests for CRUD operations
```

## Domain Context

### Property Management Domain (Chinese Context)

**Asset Types**:
- **土地使用权** (Land Use Rights): State-owned land with usage rights
- **房产** (Real Estate): Buildings and structures with ownership certificates
- **商铺** (Commercial Properties): Retail spaces and business premises
- **住宅** (Residential Properties): Housing units and apartment buildings

**Legal Framework**:
- **《物权法》**: Property Law governing ownership and usage rights
- **《合同法》**: Contract Law for rental agreements
- **《不动产登记暂行条例》**: Real estate registration regulations
- **房产证** (Property Certificate): Official ownership documentation

**Business Processes**:
- **资产录入** (Asset Registration): Initial property registration with legal documents
- **租赁合同管理** (Rental Contract Management): Contract lifecycle from signing to termination
- **收租管理** (Rent Collection): Payment processing and arrears tracking
- **维护管理** (Maintenance Management): Property maintenance and repair coordination
- **业主关系** (Stakeholder Relations): Communication with property owners and tenants

**Data Requirements**:
- **地址信息** (Address Information): Standardized Chinese address formats
- **面积计算** (Area Calculation): Gross floor area vs. usable area distinctions
- **租金标准** (Rent Standards): Market-based pricing with regional variations
- **产权信息** (Ownership Information): Chain of title and ownership percentages

## Important Constraints

### Technical Constraints
- **OCR Performance**: Chinese OCR processing is computationally intensive and memory-heavy
- **PDF Compatibility**: Must handle various PDF formats including scanned documents and digital forms
- **Database Scaling**: SQLite for development, must support PostgreSQL migration
- **Bilingual Support**: All user-facing content must support Chinese/English switching
- **File Storage**: Limited to 50MB per PDF upload for performance reasons

### Business Constraints
- **Regulatory Compliance**: Must comply with Chinese property management regulations
- **Data Privacy**: Personal information protection under Chinese privacy laws
- **Audit Requirements**: All asset changes must be logged with user attribution
- **Multi-tenancy**: Organizations must have data isolation from each other
- **Working Hours**: System must support Chinese business hours (9 AM - 6 PM CST)

### Performance Constraints
- **Response Time**: API responses must be under 2 seconds for 95% of requests
- **PDF Processing**: OCR processing must complete within 30 seconds for typical documents
- **Concurrent Users**: System must support 100+ concurrent users per organization
- **File Upload**: Support for up to 10 concurrent PDF uploads
- **Database Connections**: Maximum 50 concurrent database connections per instance

### Security Constraints
- **Authentication**: JWT-based authentication with 24-hour token expiry
- **Authorization**: Role-based access control (RBAC) with resource-level permissions
- **Data Encryption**: All sensitive data encrypted at rest
- **API Security**: Rate limiting, input validation, and SQL injection prevention
- **Audit Trail**: Complete audit log for all data modifications

## External Dependencies

### External Services
- **PaddleOCR**: OCR engine for Chinese text recognition (can be disabled for compatibility)
- **Redis**: In-memory caching for session management and API response caching
- **Nginx**: Reverse proxy and static file serving in production
- **Docker Hub**: Container registry for deployment images

### API Dependencies
- **Ant Design**: UI component library (CDN in development)
- **Font Awesome**: Icon library for UI elements
- **Chinese Government APIs**: Potential integration with property registration services
- **Payment Gateways**: Future integration with Chinese payment platforms (Alipay, WeChat Pay)

### System Dependencies
- **Python Package Index (PyPI)**: Backend package management
- **npm Registry**: Frontend package management
- **GitHub Actions**: CI/CD pipeline and automated testing
- **Docker Hub**: Container image storage and distribution

### File System Dependencies
- **Local Storage**: Temporary file storage for PDF processing
- **Database Storage**: Long-term file storage for uploaded documents
- **Log Storage**: Structured logging with rotation and retention policies
