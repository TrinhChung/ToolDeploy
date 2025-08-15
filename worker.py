from queue_config import queue, redis_conn
from rq import Worker
from app_factory import create_app

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        worker = Worker([queue])
        worker.work()
