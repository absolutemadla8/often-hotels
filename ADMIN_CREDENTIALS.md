# Admin Access Credentials

## ✅ Admin Account Details

**Email**: `trippy@oftenhotels.com`  
**Password**: `admin123`  
**Status**: Active admin user with superuser privileges  
**Database ID**: 3  

## 🔐 Authentication

### Login Request
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "trippy@oftenhotels.com", "password": "admin123"}'
```

### Expected Response
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 691200
}
```

## 🛡️ Admin Endpoints

All admin endpoints require the access token in the Authorization header:

```bash
-H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### Available Admin Routes
- `POST /api/v1/admin/hotel-tracking/start` - Start hotel tracking task
- `GET /api/v1/admin/hotel-tracking/status` - Get tracking task status  
- `POST /api/v1/admin/hotel-tracking/stop` - Stop running tracking tasks

### Usage Example
```bash
curl -X POST "http://localhost:8000/api/v1/admin/hotel-tracking/start" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -H "Content-Type: application/json"
```

## 🔧 Technical Details

### bcrypt/passlib Fix Applied
- **Issue**: bcrypt 5.0.0 removed `__about__` attribute causing passlib 1.7.4 compatibility issues
- **Solution**: Downgraded bcrypt to version 4.1.3 for compatibility
- **Status**: ✅ Resolved - Authentication working properly

### Updated Dependencies
```txt
passlib[bcrypt]==1.7.4
bcrypt==4.1.3
```

### Security Features
- ✅ JWT-based authentication
- ✅ Admin middleware protection
- ✅ Admin action logging
- ✅ Refresh token support
- ✅ bcrypt password hashing

## 📋 Verification Checklist

- [x] Admin user created in database
- [x] bcrypt/passlib compatibility fixed
- [x] Authentication endpoints working
- [x] Admin middleware active
- [x] JWT tokens generated successfully
- [x] Password verification working
- [x] Admin endpoints accessible (with valid tokens)

## 🚨 Security Notes

- Admin user has full system access
- All admin actions are logged for audit
- Change default password in production
- Use strong passwords (8+ characters, mixed case, numbers, symbols)
- Rotate access tokens regularly

## 📖 Related Documentation

- [Enhanced Hotel Search API Guide](./ENHANCED_HOTEL_SEARCH_API_GUIDE.md)
- Authentication endpoints: `/api/v1/auth/*`
- Admin endpoints: `/api/v1/admin/*`