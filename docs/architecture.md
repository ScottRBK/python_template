# JWT Authentication Service Architecture

## Executive Summary

A lightweight, centralized JWT authentication service designed for single VPS deployment, providing authentication and authorization capabilities for multiple projects. The service prioritizes resource efficiency, operational simplicity, and straightforward implementation while maintaining security best practices.

## System Overview

### Design Principles
- **Minimal resource footprint** - Optimized for single VPS deployment
- **Stateless authentication** - JWT tokens eliminate session storage needs
- **Cross-project reusability** - Shared authentication across multiple applications
- **Simple integration** - Drop-in authentication for new projects
- **Gradual enhancement** - Start simple, add OAuth providers later

### Architecture Type
- **Monolithic authentication service** with JWT token issuance
- **Shared secret validation** for resource-constrained environments
- **Database-backed user management** with PostgreSQL

## Component Architecture

### 1. Authentication Service Core

```
┌─────────────────────────────────────────────────┐
│           JWT Authentication Service            │
├─────────────────────────────────────────────────┤
│  API Layer (FastAPI)                            │
│  ├── /auth/register                             │
│  ├── /auth/login                                │
│  ├── /auth/refresh                              │
│  ├── /auth/logout                               │
│  └── /auth/me                                   │
├─────────────────────────────────────────────────┤
│  Business Logic                                 │
│  ├── User Registration                          │
│  ├── Password Hashing (bcrypt)                  │
│  ├── JWT Token Generation                       │
│  └── Token Refresh Logic                        │
├─────────────────────────────────────────────────┤
│  Data Layer (PostgreSQL)                        │
│  ├── Users Table                                │
│  └── Refresh Tokens Table                       │
└─────────────────────────────────────────────────┘
```

### 2. Token Flow Architecture

```
Frontend App          Auth Service          Backend Service
     │                      │                      │
     │──────Register───────>│                      │
     │<─────User Created────│                      │
     │                      │                      │
     │──────Login──────────>│                      │
     │<───JWT + Refresh─────│                      │
     │                      │                      │
     │──Request with JWT──────────────────────────>│
     │                      │                      │ Validate JWT
     │<───────Response─────────────────────────────│ (local validation)
     │                      │                      │
     │──Expired JWT────────────────────────────────>│
     │<──────401 Unauthorized──────────────────────│
     │                      │                      │
     │─────Refresh Token───>│                      │
     │<────New JWT──────────│                      │
```

### 3. Database Schema

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Refresh tokens table
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP,
    CONSTRAINT valid_token CHECK (
        revoked_at IS NULL OR revoked_at > created_at
    )
);

-- Indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_token_hash ON refresh_tokens(token_hash);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);
```

## API Specification

### Authentication Endpoints

#### POST /auth/register
```json
Request:
{
    "email": "user@example.com",
    "password": "SecurePassword123!"
}

Response (201):
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "role": "user",
    "created_at": "2024-01-01T00:00:00Z"
}
```

#### POST /auth/login
```json
Request:
{
    "email": "user@example.com",
    "password": "SecurePassword123!"
}

Response (200):
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 3600
}
```

#### POST /auth/refresh
```json
Request:
{
    "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}

Response (200):
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 3600
}
```

#### POST /auth/logout
```json
Request Headers:
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

Request:
{
    "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}

Response (200):
{
    "message": "Successfully logged out"
}
```

#### GET /auth/me
```json
Request Headers:
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

Response (200):
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "role": "user",
    "created_at": "2024-01-01T00:00:00Z"
}
```

## JWT Token Structure

### Access Token Claims
```json
{
    "sub": "550e8400-e29b-41d4-a716-446655440000",  // user_id
    "email": "user@example.com",
    "role": "user",
    "exp": 1704067200,  // Expiration (1 hour)
    "iat": 1704063600,  // Issued at
    "type": "access"
}
```

### Refresh Token Claims
```json
{
    "sub": "550e8400-e29b-41d4-a716-446655440000",  // user_id
    "jti": "660e8400-e29b-41d4-a716-446655440000",  // Token ID
    "exp": 1704668400,  // Expiration (7 days)
    "iat": 1704063600,  // Issued at
    "type": "refresh"
}
```

## Integration Patterns

### Client Service Integration

#### Python/FastAPI Integration
```python
from jose import jwt, JWTError
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

class AuthValidator:
    def __init__(self, jwt_secret: str, algorithm: str = "HS256"):
        self.jwt_secret = jwt_secret
        self.algorithm = algorithm
    
    async def validate_token(
        self, 
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ):
        token = credentials.credentials
        try:
            payload = jwt.decode(
                token, 
                self.jwt_secret, 
                algorithms=[self.algorithm]
            )
            if payload.get("type") != "access":
                raise HTTPException(401, "Invalid token type")
            return {
                "user_id": payload["sub"],
                "email": payload.get("email"),
                "role": payload.get("role", "user")
            }
        except JWTError:
            raise HTTPException(401, "Invalid or expired token")

# Usage in your agent service
auth = AuthValidator(jwt_secret="your-shared-secret")

@app.get("/protected")
async def protected_route(user = Depends(auth.validate_token)):
    return {"message": f"Hello {user['email']}"}
```

#### Frontend Integration
```javascript
// Store tokens
const login = async (email, password) => {
    const response = await fetch('http://auth-service/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    });
    
    const data = await response.json();
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    return data;
};

// Use tokens in requests
const makeAuthenticatedRequest = async (url, options = {}) => {
    const token = localStorage.getItem('access_token');
    
    const response = await fetch(url, {
        ...options,
        headers: {
            ...options.headers,
            'Authorization': `Bearer ${token}`
        }
    });
    
    if (response.status === 401) {
        // Token expired, try refresh
        await refreshToken();
        return makeAuthenticatedRequest(url, options);
    }
    
    return response;
};

// Refresh logic
const refreshToken = async () => {
    const refresh = localStorage.getItem('refresh_token');
    const response = await fetch('http://auth-service/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh })
    });
    
    const data = await response.json();
    localStorage.setItem('access_token', data.access_token);
    return data;
};
```

## Security Considerations

### Token Security
- **Access tokens**: Short-lived (15-60 minutes)
- **Refresh tokens**: Long-lived (7 days), stored hashed in database
- **Secrets**: Strong, randomly generated, stored in environment variables
- **HTTPS only**: Enforce TLS in production

### Password Security
- **Bcrypt hashing**: Cost factor 12 (adjustable based on server capacity)
- **Password requirements**: Minimum 8 characters, complexity rules
- **Rate limiting**: Prevent brute force attacks on login endpoint

### Token Validation
- **Signature verification**: All tokens cryptographically signed
- **Expiration checking**: Automatic rejection of expired tokens
- **Token type validation**: Ensure correct token type for endpoint
- **Revocation support**: Refresh tokens can be revoked

## Deployment Architecture

### Single VPS Deployment
```
┌──────────────────────────────────────┐
│           VPS Instance                │
├──────────────────────────────────────┤
│  Nginx (Reverse Proxy)                │
│  ├── /auth/* → Auth Service:8001      │
│  ├── /api/* → Agent Service:8000      │
│  └── /* → Frontend:3000               │
├──────────────────────────────────────┤
│  Services                             │
│  ├── Auth Service (FastAPI)           │
│  ├── Agent Service (FastAPI)          │
│  ├── Frontend (React/Next.js)         │
│  └── PostgreSQL Database              │
└──────────────────────────────────────┘
```

### Resource Allocation (4GB VPS Example)
- **Auth Service**: ~100MB RAM
- **Agent Service**: ~500MB RAM  
- **Frontend**: ~200MB RAM
- **PostgreSQL**: ~500MB RAM
- **System/Buffer**: ~2.7GB

## Configuration Management

### Environment Variables
```bash
# Auth Service
AUTH_DATABASE_URL=postgresql://user:pass@localhost/authdb
AUTH_JWT_SECRET=your-256-bit-secret-key-here
AUTH_JWT_ALGORITHM=HS256
AUTH_ACCESS_TOKEN_EXPIRE_MINUTES=60
AUTH_REFRESH_TOKEN_EXPIRE_DAYS=7
AUTH_BCRYPT_ROUNDS=12
AUTH_PORT=8001

# Client Services
JWT_SECRET=your-256-bit-secret-key-here  # Same as AUTH_JWT_SECRET
JWT_ALGORITHM=HS256
```

### Docker Compose Configuration
```yaml
version: '3.8'

services:
  auth-service:
    build: ./auth-service
    environment:
      - AUTH_DATABASE_URL=${AUTH_DATABASE_URL}
      - AUTH_JWT_SECRET=${AUTH_JWT_SECRET}
    ports:
      - "8001:8001"
    depends_on:
      - postgres
    restart: unless-stopped

  agent-service:
    build: ./agent-service
    environment:
      - JWT_SECRET=${AUTH_JWT_SECRET}
      - DATABASE_URL=${AGENT_DATABASE_URL}
    ports:
      - "8000:8000"
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

## Future Enhancements

### Phase 2: OAuth Provider Integration
- Add social login (Google, GitHub)
- Implement OAuth2 authorization code flow
- Store provider tokens for API access

### Phase 3: Advanced Features
- Multi-factor authentication (TOTP)
- Password reset via email
- Account verification flow
- Session management dashboard
- Audit logging

### Phase 4: Scaling Considerations
- Redis for token blacklisting
- Rate limiting with Redis
- Horizontal scaling with shared secrets
- Migration to asymmetric keys (RS256)

## Monitoring and Observability

### Key Metrics
- Authentication success/failure rates
- Token refresh patterns
- Average response times
- Database connection pool usage
- Memory and CPU utilization

### Logging Strategy
- Structured JSON logging
- Authentication events (login, logout, refresh)
- Failed authentication attempts
- Token validation errors
- System errors and exceptions

### Health Checks
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "auth-service",
        "version": "1.0.0",
        "database": check_database_connection()
    }
```

## Migration from Current System

### Step 1: Deploy Auth Service
1. Set up PostgreSQL database
2. Deploy auth service on same VPS
3. Configure environment variables
4. Test endpoints

### Step 2: Update Agent Service
1. Add JWT validation library
2. Update authentication middleware
3. Map JWT claims to user context
4. Test with auth service

### Step 3: Update Frontend
1. Implement login/register UI
2. Add token management
3. Update API calls with auth headers
4. Handle token refresh

### Step 4: Migration
1. Create user accounts for existing users
2. Communicate authentication changes
3. Provide password reset mechanism
4. Monitor adoption and issues

## Conclusion

This architecture provides a pragmatic, resource-efficient authentication solution suitable for single VPS deployment while maintaining the flexibility to scale and enhance as requirements evolve. The JWT-based approach eliminates session storage overhead while providing secure, stateless authentication across multiple projects
