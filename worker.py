"""Manual ACK consumer with bounded transient retries."""
import json
import os
import time

import pika

from storage import get_job, init_db, set_status

RABBITMQ_URL = os.getenv('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/%2F')
QUEUE = 'jobs'
MAX_ATTEMPTS = 3


def process(ch, method, properties, body):
    try:
        message = json.loads(body)
        job_id = message['id']
        task = message['task']
    except (ValueError, KeyError, TypeError) as exc:
        print(f'Invalid payload, discarding: {exc}', flush=True)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    job = get_job(job_id)
    if job is None or job['status'] in ('completed', 'failed'):
        # Missing or terminal jobs cannot be processed; ACK duplicate deliveries.
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    attempt = job['attempts'] + 1
    set_status(job_id, 'processing', increment_attempt=True)
    print(f'Processing {job_id}, attempt {attempt}', flush=True)
    try:
        time.sleep(4)
        # For a demo, tasks starting with "retry:" fail for the first two attempts.
        if task.lower().startswith('retry:') and attempt < 3:
            raise ConnectionError('Simulated transient dependency failure')
        # Tasks starting with "fail:" always fail (bounded at three attempts).
        if task.lower().startswith('fail:'):
            raise ConnectionError('Simulated persistent dependency failure')
        set_status(job_id, 'completed', result=f'Processed: {task}')
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f'Completed {job_id}', flush=True)
    except Exception as exc:
        print(f'Failed {job_id}: {exc}', flush=True)
        if attempt < MAX_ATTEMPTS:
            set_status(job_id, 'queued', error=f'Retrying after: {exc}')
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        else:
            set_status(job_id, 'failed', error=str(exc))
            # Terminal failure was recorded: acknowledge to prevent infinite retry.
            ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    init_db()
    while True:
        connection = None
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
            ch = connection.channel()
            ch.queue_declare(queue=QUEUE, durable=True)
            ch.basic_qos(prefetch_count=1)
            ch.basic_consume(queue=QUEUE, on_message_callback=process, auto_ack=False)
            print('Worker listening for jobs (Ctrl+C to stop)', flush=True)
            ch.start_consuming()
        except KeyboardInterrupt:
            print('Worker stopped', flush=True)
            break
        except (pika.exceptions.AMQPError, OSError) as exc:
            print(f'Broker disconnected: {exc}; reconnecting in 3 seconds', flush=True)
            time.sleep(3)
        finally:
            if connection and connection.is_open:
                connection.close()


if __name__ == '__main__':
    main()
