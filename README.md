# Often Hotels API

A robust and scalable FastAPI application with JWT authentication for hotel booking management.

## 🚀 Features

- **JWT Authentication**: Secure token-based authentication with refresh tokens
- **User Management**: Registration, login, password reset, and profile management
- **Role-Based Access**: Support for regular users and administrators
- **Database Integration**: PostgreSQL with SQLAlchemy and Alembic migrations
- **Redis Caching**: Session management and caching layer
- **Security**: Comprehensive security headers, rate limiting, and input validation
- **Monitoring**: Prometheus metrics and Grafana dashboards
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation
- **Docker Support**: Full containerization with development and production configurations
- **Logging**: Structured logging with request tracing
- **Error Handling**: Comprehensive error handling with detailed responses

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- PostgreSQL 15+
- Redis 7+

## 🛠️ Quick Start

### Using Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd often-hotels
   ```

2. **Create environment file**
   ```bash
   make create-env
   # Edit .env file with your configuration
   ```

3. **Generate SSL certificates for development**
   ```bash
   make ssl-cert
   ```

4. **Start the services**
   ```bash
   make up
   ```

5. **Run database migrations**
   ```bash
   make migrate
   ```

6. **Access the API**
   - API: https://localhost/
   - Documentation: https://localhost/docs
   - Alternative docs: https://localhost/redoc
   - Grafana: http://localhost:3000 (admin/admin)
   - Prometheus: http://localhost:9090

### Local Development

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your local database and Redis settings
   ```

3. **Run the development server**
   ```bash
   make dev-server
   ```

## 🔧 Configuration

Key environment variables in `.env`:

```env
# Application
SECRET_KEY=your-super-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=11520
REFRESH_TOKEN_EXPIRE_MINUTES=43200

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/often_hotels

# Redis
REDIS_URL=redis://localhost:6379/0

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000","https://yourdomain.com"]

# Email (Optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

## 🔐 Authentication

The API uses JWT tokens for authentication with the following endpoints:

### Register a new user
```bash
curl -X POST "https://localhost/api/v1/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "user@example.com",
       "password": "securepassword123",
       "confirm_password": "securepassword123",
       "first_name": "John",
       "last_name": "Doe"
     }'
```

### Login
```bash
curl -X POST "https://localhost/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "user@example.com",
       "password": "securepassword123"
     }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 691200
}
```

### Using the token
```bash
curl -X GET "https://localhost/api/v1/auth/me" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 📊 API Endpoints

### Authentication Endpoints
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - Logout (revoke refresh token)
- `POST /api/v1/auth/logout-all` - Logout from all devices
- `GET /api/v1/auth/me` - Get current user info
- `PUT /api/v1/auth/me` - Update user profile
- `POST /api/v1/auth/change-password` - Change password

### Hotel Endpoints
- `GET /api/v1/hotels/` - Get hotels list (public with optional auth)
- `GET /api/v1/hotels/{id}` - Get hotel details
- `POST /api/v1/hotels/{id}/book` - Book hotel (requires verified user)
- `GET /api/v1/hotels/{id}/reviews` - Get hotel reviews (requires auth)
- `POST /api/v1/hotels/{id}/reviews` - Create review (requires verified user)
- `GET /api/v1/hotels/bookings/my` - Get user's bookings

### Admin Endpoints (Superuser only)
- `GET /api/v1/users/` - List all users
- `POST /api/v1/users/` - Create user
- `GET /api/v1/users/{id}` - Get user by ID
- `PUT /api/v1/users/{id}` - Update user
- `DELETE /api/v1/users/{id}` - Delete user
- `POST /api/v1/users/{id}/activate` - Activate user
- `POST /api/v1/users/{id}/deactivate` - Deactivate user
- `GET /api/v1/hotels/admin/statistics` - Get booking statistics

### System Endpoints
- `GET /health` - Health check
- `GET /health/detailed` - Detailed health check

## 🗄️ Database

### Running Migrations

```bash
# Generate migration
make migrate-auto

# Run migrations
make migrate

# Check migration history
make migrate-history
```

### Database Schema

The application includes the following main models:

- **Users**: User accounts with authentication data
- **RefreshTokens**: JWT refresh token management
- **Hotels**: Hotel information (example data)
- **Bookings**: Hotel bookings (example implementation)

## 🐳 Docker Commands

```bash
# Development
make build          # Build images
make up             # Start services
make down           # Stop services
make logs           # View logs
make shell          # Access app container
make db-shell       # Access database

# Production
make prod-build     # Build production images
make prod-up        # Start production services
make prod-down      # Stop production services

# Database
make migrate        # Run migrations
make db-backup      # Backup database
make seed-db        # Seed with sample data

# Utilities
make test           # Run tests
make lint           # Run linting
make clean          # Clean Docker resources
```

## 🔒 Security Features

- **Password Hashing**: Bcrypt with salt
- **JWT Tokens**: RS256 algorithm with configurable expiration
- **Rate Limiting**: Configurable per-endpoint rate limits
- **CORS**: Configurable cross-origin resource sharing
- **Security Headers**: Comprehensive HTTP security headers
- **Input Validation**: Pydantic models with strict validation
- **SQL Injection Protection**: SQLAlchemy ORM with parameterized queries
- **Host Header Validation**: Protection against host header injection

## 📈 Monitoring

### Metrics Available

- **Application Metrics**: Request count, response times, error rates
- **System Metrics**: CPU, memory, disk usage
- **Database Metrics**: Connection pool, query performance
- **Custom Metrics**: User registrations, authentication events

### Accessing Monitoring

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Application Metrics**: http://localhost:8000/metrics

## 🧪 Testing

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test
docker-compose exec app pytest tests/test_auth.py -v
```

## 📝 Logging

The application uses structured logging with the following log levels:

- **INFO**: Normal application events
- **WARNING**: Important events that might need attention
- **ERROR**: Error conditions
- **DEBUG**: Detailed diagnostic information

Logs are output in JSON format for production and console format for development.

## 🚀 Production Deployment

### Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.prod.yml often-hotels

# Scale services
docker service scale often-hotels_app=5
```

### Environment Variables for Production

```env
DATABASE_URL=postgresql+asyncpg://user:password@db:5432/often_hotels
REDIS_URL=redis://redis:6379/0
SECRET_KEY=your-production-secret-key
BACKEND_CORS_ORIGINS=["https://yourdomain.com"]
POSTGRES_PASSWORD=secure-production-password
```

## 🛡️ Security Best Practices

1. **Change default passwords** in production
2. **Use strong SECRET_KEY** (32+ characters)
3. **Enable HTTPS** with proper certificates
4. **Configure CORS** for your specific domains
5. **Set up proper firewall rules**
6. **Regular security updates** of dependencies
7. **Monitor logs** for suspicious activity
8. **Use environment variables** for secrets

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## 📚 API Documentation

Once the application is running, you can access:

- **Interactive API docs**: https://localhost/docs
- **Alternative docs**: https://localhost/redoc
- **OpenAPI spec**: https://localhost/api/v1/openapi.json

## 🐛 Troubleshooting

### Common Issues

**Port already in use:**
```bash
# Stop conflicting services
make down
docker-compose ps
```

**Database connection errors:**
```bash
# Check database status
make status
make logs db
```

**Permission errors:**
```bash
# Fix file permissions
sudo chown -R $USER:$USER .
```

**SSL certificate errors:**
```bash
# Regenerate certificates
rm -rf nginx/ssl
make ssl-cert
```

### Getting Help

- Check the logs: `make logs`
- Verify service status: `make status`
- Test API health: `curl -k https://localhost/health`
- Check database connection: `make db-shell`

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- FastAPI framework
- SQLAlchemy ORM
- Pydantic data validation
- PostgreSQL database
- Redis cache
- Docker containerization