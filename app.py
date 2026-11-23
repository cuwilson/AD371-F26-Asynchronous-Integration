"""FastAPI ingress: accept -> store -> publish -> return 202."""
import json
import os
from pathlib import Path
from uuid import uuid4

import pika
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from storage import create_job, get_job, init_db, set_status

RABBITMQ_URL = os.getenv('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/%2F')
QUEUE = 'jobs'

app = FastAPI(title='Event-Driven Job Processor')
init_db()


class JobRequest(BaseModel):
    task: str = Field(min_length=1, max_length=200)


@app.get('/')
def homepage():
    return FileResponse(Path(__file__).with_name('index.html'))


@app.post('/api/jobs', status_code=202)
def submit_job(payload: JobRequest, response: Response):
    job_id = str(uuid4())
    create_job(job_id, payload.task)
    connection = None
    try:
        connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE, durable=True)
        channel.confirm_delivery()
        channel.basic_publish(
            exchange='', routing_key=QUEUE,
            body=json.dumps({'id': job_id, 'task': payload.task}),
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent,
                content_type='application/json', message_id=job_id),
            mandatory=True,
        )
    except Exception as exc:
        # If a publish confirmation is lost, the message might still be queued.
        # The worker is idempotent for terminal states.
        set_status(job_id, 'failed', error='Could not confirm queue publication')
        raise HTTPException(status_code=503, detail='Queue unavailable; job not accepted') from exc
    finally:
        if connection and connection.is_open:
            connection.close()
    response.headers['Location'] = f'/api/jobs/{job_id}'
    return {'job_id': job_id, 'status': 'queued', 'status_url': f'/api/jobs/{job_id}'}


@app.get('/api/jobs/{job_id}')
def job_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail='Job not found')
    return job
