# Auth Module Design

## Database

### user 表

| Column     | Type         | Constraint          |
|------------|--------------|---------------------|
| id         | INT          | PK, AUTO_INCREMENT  |
| username   | VARCHAR(20)  | NOT NULL, UNIQUE    |
| password   | VARCHAR(60)  | NOT NULL (bcrypt)   |
| created_at | DATETIME     | NOT NULL, DEFAULT CURRENT_TIMESTAMP |

## Pydantic Schema

| Class         | Fields                          | Purpose    |
|---------------|---------------------------------|------------|
| UserRegister  | username, password              | 注册请求    |
| UserLogin     | username, password              | 登录请求    |
| UserOut       | id, username, created_at        | 公开返回    |
| TokenOut      | access_token, token_type, user  | 登录响应    |

## API

| Method | Path             | Request       | Response   |
|--------|------------------|---------------|------------|
| POST   | /auth/register   | UserRegister  | UserOut    |
| POST   | /auth/login      | UserLogin     | TokenOut   |
| GET    | /auth/me         | —             | UserOut    |

## Security

- bcrypt via passlib for password hashing
- JWT via python-jose, payload `{sub: user_id, exp}`
- Access token 24h expiry, no refresh token
- Dependency `get_current_user` to extract user from Authorization header

## Dependencies

```toml
passlib[bcrypt]>=1.7
python-jose[cryptography]>=3.3
```
