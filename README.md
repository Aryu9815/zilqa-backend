# Production-Ready FastAPI E-Commerce Backend

A high-performance, asynchronous REST API for an e-commerce platform built with **FastAPI**, **PostgreSQL**, and direct **asyncpg** connection pooling.

---

## Key Features

- **Layered Clean Architecture**: Strict separation of concerns (`API` → `Service` → `Repository` → `Database`).
- **Direct Async PostgreSQL with asyncpg**: No synchronous ORM overhead; parameterized queries, high-throughput connection pooling, and atomic transactions.
- **Authentication & Security**:
  - Secure password hashing with Argon2 / Bcrypt via `pwdlib`.
  - Stateless short-lived JWT access tokens.
  - Opaque refresh tokens with database tracking, token rotation, and instant revocation.
  - Role-based access control (`customer`, `admin`).
- **Storefront & Catalog**:
  - Paginated categories and products with SQL JOINs (no N+1 queries).
  - Multi-criteria filtering (category, price range, search in name/description).
  - Flexible sorting (`price_asc`, `price_desc`, `newest`, `oldest`, `name_asc`, `name_desc`).
- **Cart & Wishlist**:
  - Server-calculated cart totals and live pricing validation.
  - Single-default address enforcement per user.
- **Transactional Checkout & Order Management**:
  - Full transactional order placement with live product price verification.
  - Immutable order item snapshots (preserves historical pricing and product details).
  - Strict order lifecycle state machine validation (`pending` → `confirmed` → `processing` → `shipped` → `delivered` / `cancelled`).
- **Admin Analytics Dashboard**:
  - High-performance PostgreSQL aggregation queries for revenue time-series, order status volume, top-selling products, and top categories.
- **Database Migrations & SQL DDL**:
  - Standalone SQL scripts (`schema.sql`, `indexes.sql`, `constraints.sql`, `seed.sql`).
  - Alembic migration environment ready (`alembic upgrade head`).

---

## Project Structure

```text
zilqa-backend/
├── app/
│   ├── main.py                          # FastAPI app entrypoint, lifespan, CORS & exception handlers
│   │
│   ├── core/
│   │   ├── config.py                    # pydantic-settings configuration (.env loader)
│   │   ├── security.py                  # Password hashing (pwdlib/Argon2), JWT encoding/decoding
│   │   ├── database.py                  # asyncpg pool lifecycle, transactions, query helpers
│   │   ├── dependencies.py              # FastAPI auth dependencies (get_current_user, require_admin)
│   │   └── exceptions.py                # Custom API exception classes & error codes
│   │
│   ├── models/
│   │   └── database_models.py           # Typed dataclasses for database entities
│   │
│   ├── schemas/
│   │   ├── common.py                    # Standard envelopes (ResponseEnvelope, PaginatedResponse)
│   │   ├── auth.py                      # RegisterRequest, LoginRequest, TokenResponse
│   │   ├── user.py                      # UserResponse, UserUpdate
│   │   ├── address.py                   # AddressCreate, AddressUpdate, AddressResponse
│   │   ├── category.py                  # CategoryCreate, CategoryUpdate, CategoryResponse
│   │   ├── product.py                   # ProductCreate, ProductUpdate, ProductResponse, SortBy
│   │   ├── cart.py                      # CartItemCreate, CartItemResponse, CartResponse
│   │   ├── wishlist.py                  # WishlistItemResponse, WishlistResponse
│   │   ├── order.py                     # OrderCreate, OrderStatusUpdate, OrderResponse
│   │   └── analytics.py                 # Overview, Revenue, Orders, Top Products/Categories
│   │
│   ├── repositories/
│   │   ├── base_repository.py           # Shared asyncpg query execution helpers
│   │   ├── user_repository.py           # User & refresh token queries
│   │   ├── address_repository.py        # User address queries & default address management
│   │   ├── category_repository.py       # Category CRUD & pagination
│   │   ├── product_repository.py        # Product CRUD, filters, search, sorting, joins
│   │   ├── cart_repository.py           # Cart & cart items transactional operations
│   │   ├── wishlist_repository.py       # Wishlist item queries
│   │   ├── order_repository.py          # Transactional order creation & status updates
│   │   └── analytics_repository.py      # PostgreSQL aggregation for revenue, orders, KPIs
│   │
│   ├── services/
│   │   ├── auth_service.py              # Registration, login, token rotation, logout logic
│   │   ├── user_service.py              # Profile & address business logic
│   │   ├── category_service.py          # Category management logic
│   │   ├── product_service.py           # Product catalog management & validation
│   │   ├── cart_service.py              # Cart management & live price calculation
│   │   ├── wishlist_service.py          # Wishlist management
│   │   ├── order_service.py             # Order placement, price verification, state transitions
│   │   └── analytics_service.py         # Admin analytics data aggregation
│   │
│   ├── api/
│   │   ├── router.py                    # Main v1 API router assembling all sub-routers
│   │   ├── auth.py                      # /api/v1/auth
│   │   ├── users.py                     # /api/v1/users
│   │   ├── addresses.py                 # /api/v1/users/me/addresses
│   │   ├── categories.py                # /api/v1/categories & /api/v1/admin/categories
│   │   ├── products.py                  # /api/v1/products & /api/v1/admin/products
│   │   ├── cart.py                      # /api/v1/cart
│   │   ├── wishlist.py                  # /api/v1/wishlist
│   │   ├── orders.py                    # /api/v1/orders & /api/v1/admin/orders
│   │   ├── analytics.py                 # /api/v1/admin/analytics
│   │   └── health.py                    # /health & /health/db
│   │
│   └── utils/
│       └── helpers.py                   # Record parsing, date math, pagination calculators
│
├── database/
│   ├── schema.sql                       # DDL: Tables, UUID defaults, Foreign Keys
│   ├── indexes.sql                      # Performance & Foreign Key Indexes
│   ├── constraints.sql                  # Integrity constraints, checks, partial unique index
│   └── seed.sql                         # Initial admin user, categories, and products
│
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_initial_schema.py        # Initial migration
│
├── scripts/
│   └── seed.py                          # Python asyncpg seed runner script
│
├── tests/                               # Comprehensive unit & schema test suite
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_products.py
│   ├── test_categories.py
│   ├── test_cart.py
│   ├── test_wishlist.py
│   ├── test_addresses.py
│   ├── test_orders.py
│   └── test_analytics.py
│
├── .env.example
├── .gitignore
├── requirements.txt
├── alembic.ini
├── Dockerfile
└── docker-compose.yml
```

---

## Getting Started

### 1. Prerequisites

- Python 3.12+
- PostgreSQL 14+ or Docker

### 2. Environment Setup

Clone the repository and create a Python virtual environment:

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

Copy `.env.example` to `.env` and adjust database credentials:

```bash
cp .env.example .env
```

Default `.env` configuration:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ecommerce
JWT_SECRET_KEY=your-secure-secret-key-at-least-32-characters
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

---

## Database Setup & Migrations

You have two options for database initialization:

### Option A: Direct SQL Execution (Recommended for fresh PostgreSQL)

Run the SQL files in order against your PostgreSQL database:

```bash
psql -U postgres -d ecommerce -f database/schema.sql
psql -U postgres -d ecommerce -f database/indexes.sql
psql -U postgres -d ecommerce -f database/constraints.sql
psql -U postgres -d ecommerce -f database/seed.sql
```

### Option B: Alembic Migrations

Run database migrations:

```bash
alembic upgrade head
```

Then seed the initial admin user and sample catalog:

```bash
python scripts/seed.py
```

### Default Seed Credentials

- **Admin User**: `admin@example.com` / `Admin@123` (Role: `admin`)
- **Customer User**: `customer@example.com` / `Customer@123` (Role: `customer`)

> [!WARNING]
> Change the default admin password immediately in any non-development environment!

---

## Running the Application

Start the development server with hot-reload:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be accessible at `http://localhost:8000`.

---

## Interactive API Documentation

FastAPI automatically generates interactive Swagger and ReDoc documentation:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI JSON**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## Running with Docker Compose

To start both PostgreSQL and the FastAPI application in isolated containers:

```bash
docker compose up --build
```

The database container automatically initializes with the schema, indexes, constraints, and seed data from `/database/*.sql`.

---

## Running Tests

Execute the test suite using pytest:

```bash
pytest -v
```

---

## API Endpoints Reference

All API routes are prefixed with `/api/v1`.

### 1. Authentication
- `POST /api/v1/auth/register` - Register a new customer
- `POST /api/v1/auth/login` - Login with email and password
- `POST /api/v1/auth/refresh` - Rotate and refresh JWT access token
- `POST /api/v1/auth/logout` - Revoke refresh token
- `GET /api/v1/auth/me` - Get current user profile

### 2. Users & Addresses
- `GET /api/v1/users/me` - Get profile
- `PUT /api/v1/users/me` - Update profile details
- `GET /api/v1/users/me/addresses` - List user shipping addresses
- `POST /api/v1/users/me/addresses` - Add a new address
- `GET /api/v1/users/me/addresses/{id}` - Get single address
- `PUT /api/v1/users/me/addresses/{id}` - Update address
- `DELETE /api/v1/users/me/addresses/{id}` - Delete address
- `PATCH /api/v1/users/me/addresses/{id}/default` - Set as default address

### 3. Categories
- `GET /api/v1/categories` - List categories (Paginated)
- `GET /api/v1/categories/{id}` - Get single category
- `POST /api/v1/admin/categories` - Create category *(Admin only)*
- `PUT /api/v1/admin/categories/{id}` - Update category *(Admin only)*
- `DELETE /api/v1/admin/categories/{id}` - Delete category *(Admin only)*

### 4. Products
- `GET /api/v1/products` - List products with search, filtering, and sorting
- `GET /api/v1/products/{id}` - Get single product details
- `POST /api/v1/admin/products` - Create product *(Admin only)*
- `PUT /api/v1/admin/products/{id}` - Update product *(Admin only)*
- `DELETE /api/v1/admin/products/{id}` - Soft delete / deactivate product *(Admin only)*

### 5. Cart
- `GET /api/v1/cart` - Get user shopping cart with live subtotals
- `POST /api/v1/cart/items` - Add item to cart
- `PUT /api/v1/cart/items/{id}` - Update item quantity
- `DELETE /api/v1/cart/items/{id}` - Remove item from cart
- `DELETE /api/v1/cart` - Clear entire cart

### 6. Wishlist
- `GET /api/v1/wishlist` - Get user wishlist
- `POST /api/v1/wishlist/{product_id}` - Add product to wishlist
- `DELETE /api/v1/wishlist/{product_id}` - Remove product from wishlist

### 7. Orders
- `POST /api/v1/orders` - Place order from current cart (Transactional)
- `GET /api/v1/orders` - List customer's orders (Paginated)
- `GET /api/v1/orders/{id}` - Get single order details

### 8. Admin Orders *(Admin only)*
- `GET /api/v1/admin/orders` - List all orders with filters (`status`, `payment_status`, `date_from`, `date_to`, `search`)
- `GET /api/v1/admin/orders/{id}` - Get order details with customer & address
- `PATCH /api/v1/admin/orders/{id}/status` - Update fulfillment status
- `PATCH /api/v1/admin/orders/{id}/payment-status` - Update payment status

### 9. Admin Dashboard Analytics *(Admin only)*
- `GET /api/v1/admin/analytics/overview` - Overall revenue, orders, customers & products KPIs
- `GET /api/v1/admin/analytics/revenue` - Revenue time-series for charts (`today`, `7_days`, `30_days`, `90_days`, `1_year`, `custom`)
- `GET /api/v1/admin/analytics/orders` - Order status breakdown and daily count charts
- `GET /api/v1/admin/analytics/recent-orders` - Recent orders list with customer info
- `GET /api/v1/admin/analytics/top-products` - Top selling products by units & revenue
- `GET /api/v1/admin/analytics/top-categories` - Top selling categories by units & revenue

### 10. Health
- `GET /health` - Liveness probe
- `GET /health/db` - PostgreSQL database readiness probe

---

## License

MIT License
