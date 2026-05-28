# 退出登录接口设计

## 背景

当前 bms-backend 使用无状态 JWT 认证，token 签发后直到过期前一直有效，无法主动失效。参考 kms-backend 的设计哲学（后端做最少的事），设计退出登录接口。

kms-backend 的退出登录是委托模式——后端本身不做 token 失效，而是透传到外部 SSO/ACC 系统。bms-backend 是自包含 JWT 认证，无外部 IdP，因此采用 Redis 黑名单方案实现 token 主动失效。

## 方案

**Redis 黑名单**：签发 JWT 时写入 `jti` 唯一标识，退出时将 `jti` 存入 Redis 黑名单（TTL = token 剩余有效期），认证时先查黑名单。

### 选型对比

| 方案 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| 客户端删除 token | 零服务端改动 | token 仍可复用，不安全 | 不选 |
| Token 版本号 | 简洁，无额外存储 | 所有设备同时登出 | 不选 |
| **Redis 黑名单** | 精确控制单个 token，TTL 自动清理 | 需要 Redis 依赖 | **选用** |

## 接口定义

```
POST /auth/logout
Headers: Authorization: Bearer <token>
Response 200: { "message": "已退出登录" }
```

- 需要登录状态（通过 `get_current_user` 依赖注入）
- 无需请求体
- 支持重复调用（幂等）

## Redis Key 设计

```
Key:   bl:<jti>
Value: 1
TTL:   exp - now（秒），与 JWT 有效期同步，到期自动清理
```

选择 `bl:` 短前缀而非 `blacklist:`，减少存储空间。

## JWT Payload 变化

```json
{
  "sub": "1",
  "jti": "uuid-v4",
  "iat": 1234567890,
  "exp": 1234567890
}
```

新增字段：
- `jti`：JWT ID，UUID v4，唯一标识每个 token
- `iat`：签发时间（python-jose 默认不写入，显式写入用于日志/审计）

## 数据流

```
POST /auth/logout
Authorization: Bearer <token>
        │
        ▼
  get_current_user()  ← 解析 JWT，检查 Redis 黑名单
        │
        ▼
  AuthService.logout(jti, exp)
        │
        ▼
  Redis: SET bl:<jti> 1 EX <remaining_seconds>
        │
        ▼
  { "message": "已退出登录" }
```

## 文件变更

| 文件 | 操作 | 改动 |
|------|------|------|
| `requirements.txt` | 修改 | 新增 `redis[hiredis]>=5.0` |
| `app/config.py` | 修改 | 新增 `REDIS_URL` 环境变量 |
| `app/core/redis.py` | **新建** | Redis 连接管理（单例连接池） |
| `app/core/security.py` | 修改 | `create_access_token` 加入 `jti` |
| `app/services/auth.py` | 修改 | 新增 `logout(jti, exp)` 方法 |
| `app/api/deps.py` | 修改 | `get_current_user` 增加 Redis 黑名单检查 |
| `app/schemas/auth.py` | 修改 | 新增 `LogoutOut` |
| `app/api/auth.py` | 修改 | 新增 `POST /auth/logout` |

## 错误处理

| 场景 | HTTP 状态 | 响应 |
|------|-----------|------|
| 未提供 token | 401 | `{"detail": "未提供认证凭据"}` |
| token 在黑名单（已退出） | 401 | `{"detail": "凭据已失效"}` |
| token 格式无效 | 401 | `{"detail": "认证格式无效"}` |
| token 过期 | 401 | `{"detail": "凭据无效或已过期"}` |
| 正常退出 | 200 | `{"message": "已退出登录"}` |

## 注意事项

- Redis 不可用时，认证直接放行（降级策略），不阻塞正常请求
- 黑名单 TTL 与 JWT exp 同步，无需额外清理任务
- `bl:` 前缀避免与其他业务 key 冲突
