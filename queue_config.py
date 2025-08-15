import os
import redis
from rq import Queue

# Cấu hình Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_conn = redis.from_url(REDIS_URL)

# Queue mặc định
queue = Queue("default", connection=redis_conn)
