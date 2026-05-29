import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+aiomysql://root:root123456@127.0.0.1:3306/test_db?charset=utf8mb4",
)
DB_CHECK_ON_STARTUP = os.getenv("DB_CHECK_ON_STARTUP", "1") == "1"

SECRET_KEY = os.getenv("SECRET_KEY", "kms-dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")

ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://127.0.0.1:9200")
