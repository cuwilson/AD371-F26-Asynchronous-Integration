# AD371 – Asynchronous Integration

**Course:** AD371 – Software Architecture  
**Quarter:** Fall 2026

## Project Overview

This project demonstrates asynchronous communication between a REST API and a background worker using RabbitMQ.

The application accepts job requests through a FastAPI backend, places them into a durable RabbitMQ message queue, and returns an HTTP 202 Accepted response without waiting for processing to finish.

A separate Python worker consumes the queued jobs, simulates a four-second processing task, and updates their status in a shared SQLite database. A lightweight HTML and JavaScript dashboard allows users to submit jobs and monitor progress.

The project was initially generated using ChatGPT, then reviewed, corrected, and tested to evaluate the reliability of AI-generated distributed messaging code.

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Backend and worker implementation |
| FastAPI | REST API for submitting and retrieving jobs |
| Uvicorn | ASGI server |
| RabbitMQ | Durable asynchronous message broker |
| Pika | Python RabbitMQ client |
| Docker Desktop / Docker Compose | RabbitMQ hosting and configuration |
| SQLite | Shared job status database |
| HTML / JavaScript | Job submission and status polling |
| GitHub | Source control and project documentation |

## System Architecture

The application uses a producer-consumer architecture to separate job ingestion from processing.

```text
             HTML / JavaScript Dashboard
                        |
                        | POST /api/jobs
                        v
                 FastAPI Producer
                        |
                        | Publish persistent message
                        v
                  RabbitMQ Broker
                        |
                  Durable jobs Queue
                        |
                        | Message delivery
                        v
                  Python Worker
                        |
                +-------+-------+
                |               |
             Success         Failure
                |               |
               ACK          Retry / NACK
                                |
                       Malformed message
                                |
                                v
                         jobs.dead Queue

                Shared SQLite Database
                  ^             ^
                  |             |
               FastAPI        Worker
                  |
            GET /api/jobs/{id}
                  |
                  v
              Dashboard
```

### Application Components

**FastAPI Producer (`app.py`)**

The producer accepts HTTP requests, validates input, generates a unique Job ID, creates a status record, and publishes a message to RabbitMQ.

It returns HTTP 202 after receiving publisher confirmation from RabbitMQ rather than waiting for the worker to finish processing.

**RabbitMQ Message Broker**

RabbitMQ stores persistent messages in a durable queue named `jobs`.

A separate queue named `jobs.dead` preserves rejected malformed messages for investigation.

**Background Worker (`worker.py`)**

The worker consumes RabbitMQ messages and simulates a four-second task.

It uses manual acknowledgments to control when messages are removed from the queue.

**SQLite Status Store (`storage.py`)**

SQLite stores job IDs, descriptions, processing states, retry counts, results, errors, and timestamps.

Both FastAPI and the worker access the same database.

**HTML Dashboard (`index.html`)**

The dashboard provides a job submission form and polls the API every second to display updated job statuses.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Displays the job dashboard |
| POST | `/api/jobs` | Validates and queues a new job |
| GET | `/api/jobs/{job_id}` | Returns the current job status |
| GET | `/docs` | Displays FastAPI documentation |

### Job Statuses

| Status | Meaning |
|---|---|
| `queued` | Job accepted and awaiting processing |
| `processing` | Worker is currently processing the job |
| `completed` | Job successfully processed |
| `failed` | Job failed permanently or could not be published |

### Example Job Submission

**Request:**

```http
POST /api/jobs
Content-Type: application/json

{
  "task": "Generate weekly report"
}
```

**Response:**

```json
{
  "job_id": "generated-uuid",
  "status": "queued",
  "status_url": "/api/jobs/generated-uuid"
}
```

HTTP Status: `202 Accepted`

The API also provides a `Location` header pointing to the job's status endpoint.

The client can use the returned Job ID to poll the API until the job reaches a terminal state.

## Installation and Setup

### Prerequisites

- Python 3
- Docker Desktop
- GitHub Desktop (optional, for source control)
- A web browser

### 1. Download the Repository

Clone the repository using GitHub Desktop or download it from:

https://github.com/cuwilson/AD371-F26-Asynchronous-Integration

Open the project folder in VS Code.

### 2. Start Docker Desktop

Make sure Docker Desktop is running.

Open a VS Code PowerShell terminal in the project folder and execute:

```powershell
docker compose up -d
```

This starts RabbitMQ and its management interface.

RabbitMQ Management Dashboard:

http://localhost:15672

Local development credentials:

- Username: `guest`
- Password: `guest`

These credentials are intended for local testing only.

### 3. Create a Python Virtual Environment

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the required dependencies:

```powershell
python -m pip install -r requirements.txt
```

### 4. Start FastAPI

In the first VS Code terminal:

```powershell
python -m uvicorn app:app --reload
```

Open the application:

http://127.0.0.1:8000

FastAPI documentation:

http://127.0.0.1:8000/docs

### 5. Start the Background Worker

Open a second VS Code terminal.

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Start the worker:

```powershell
python worker.py
```

Expected output:

```text
Worker listening for jobs (Ctrl+C to stop)
```

The application is now ready to accept and process jobs.

### 6. Submit a Test Job

In the web dashboard, enter:

```text
Generate weekly report
```

Click **Submit job**.

Expected behavior:

1. FastAPI accepts the request.
2. RabbitMQ receives the message.
3. The dashboard displays `queued` or `processing`.
4. The worker processes the job for approximately four seconds.
5. The dashboard updates to `completed`.

### Stopping the Application

Press `Ctrl+C` in the FastAPI and worker terminals.

Stop RabbitMQ using:

```powershell
docker compose down
```

The Docker named volume preserves RabbitMQ data.

Avoid using `docker compose down -v` unless intentionally deleting the broker's stored data.

## AI Disclosure and Prompt Log

### AI Tool

**ChatGPT – OpenAI**

ChatGPT generated the initial project implementation, including:

- FastAPI producer
- RabbitMQ integration
- Background worker
- SQLite job status store
- HTML dashboard
- Docker Compose configuration
- Setup documentation

The initial code was committed to GitHub before corrections were made.

Additional AI assistance was used to audit the architecture, correct identified issues, optimize RabbitMQ connections, and prepare QA testing procedures.

### Original AI Prompt

The assignment-provided sample prompt was used to generate the initial implementation, selecting Python/FastAPI and RabbitMQ as the framework and broker.

> Act as a senior distributed systems architect. Build a decoupled, event-driven service demonstrating synchronous REST ingestion and asynchronous message queue processing using Python/FastAPI and RabbitMQ.
>
> The project must include:
>
> **Ingress REST API (Producer):**
>
> - POST /api/jobs (or /orders): Validates input, generates a unique Job ID, pushes the payload onto a durable message queue, and IMMEDIATELY returns an HTTP 202 Accepted response with the Job ID.
> - GET /api/jobs/:id: Returns the current job status (e.g., 'queued', 'processing', 'completed', 'failed').
>
> **Message Broker:**
>
> - A running broker instance (e.g., configured via Docker Compose for RabbitMQ or Redis).
>
> **Worker Service (Consumer):**
>
> - Continuously listens on the queue.
> - Simulates work (e.g., a 3-5 second processing delay).
> - Updates the job status store upon completion.
> - Implements explicit message acknowledgments (ACK upon success, NACK/requeue on transient failure).
>
> **A lightweight frontend (or Postman collection / HTML dashboard) showing:**
>
> - A button/form to submit jobs.
> - A live polling status indicator updating from 'queued' to 'processing' to 'completed'.
>
> Provide the API code, worker consumer code, Docker Compose file for the broker, and step-by-step setup commands.


## AI-Generated Code Audit

The original code was reviewed against the assignment's messaging architecture checklist.

### 1. True Asynchronous Decoupling — Passed

The original implementation used RabbitMQ as an external message broker rather than an in-memory array or background task inside the API.

The API and worker run as separate processes.

**Verification:**

The worker was stopped while FastAPI remained running. Two jobs were submitted successfully and remained queued in RabbitMQ.

After restarting the worker, both jobs completed.

This confirmed that the API could continue accepting jobs without an active worker.

### 2. Immediate HTTP 202 Response — Improved

The original implementation correctly returned HTTP 202 after publishing to RabbitMQ instead of waiting for job processing to finish.

However, the producer established and closed a new RabbitMQ connection for every submitted job.

This caused additional request latency.

**Correction:**

A reusable RabbitMQ connection helper was added using Python's thread-local storage.

Connections can now be reused by subsequent requests handled by the same thread.

The implementation retains publisher confirmations, durable queues, and persistent messages.

**Verification:**

Before optimization, the average of five requests was 117.87 ms.

After optimization, four of five requests completed in under 100 ms. The first request required additional connection setup time.

### 3. Message Acknowledgments — Passed

The original worker already used explicit manual acknowledgment handling.

- `basic_ack` is called after successfully recording completion.
- `basic_nack(requeue=True)` is used for retryable processing failures.
- `basic_nack(requeue=False)` rejects malformed messages.
- Terminally failed jobs are recorded as failed and acknowledged.

The worker uses:

```python
auto_ack=False
```

This avoids acknowledging messages immediately upon delivery.

### 4. Durable Messaging — Passed Code Review

The application uses durable RabbitMQ queues and persistent messages.

The producer also enables publisher confirmations to verify that RabbitMQ accepted a published message.

Docker Compose uses a named volume for RabbitMQ data.

These mechanisms improve resilience but do not provide an absolute guarantee against every possible failure.

### 5. Dead-Letter Queue — Corrected

**Problem identified:**

The original worker rejected malformed messages using:

```python
ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
```

However, the original queue did not specify a dead-letter destination.

Consequently, rejected messages could be discarded without being preserved for investigation.

**Correction:**

A durable `jobs.dead` queue was added.

The main `jobs` queue now includes:

```python
arguments={
    'x-dead-letter-exchange': '',
    'x-dead-letter-routing-key': 'jobs.dead'
}
```

Both the producer and worker declare the queue with matching settings.

**Verification:**

An intentionally malformed message was manually published to the main queue.

The worker rejected the payload, and RabbitMQ transferred it to `jobs.dead`.

The management dashboard confirmed that the dead-letter queue contained one message.

### 6. Idempotency — Partially Implemented

The worker checks whether a job is already completed or permanently failed before processing it.

Messages associated with terminal jobs are acknowledged without repeating the simulated work.

This provides basic protection against duplicate deliveries.

However, the implementation does not guarantee exactly-once processing or transactional coordination between the SQLite status store and RabbitMQ.

More comprehensive idempotency controls would be required for production systems involving payments or other non-repeatable operations.

### 7. Retry Handling — Passed

The worker tracks processing attempts and supports up to three attempts per job.

A transient failure causes the message to be requeued.

After the maximum number of attempts, the worker records the job as failed and acknowledges it to prevent an infinite retry loop.

**Verification:**

A job beginning with `retry:` failed twice and completed on its third attempt.

A job beginning with `fail:` failed after three attempts and stopped retrying.

## Quality Assurance Testing

Testing was performed locally using the dashboard, PowerShell, RabbitMQ Management, and worker terminal logs.

### Test Results

| Test ID | Test | Actual Result | Status |
|---|---|---|---|
| QA-001 | Submit a normal job | Job processed and completed | Pass |
| QA-002 | Return HTTP 202 | API accepted job without waiting for processing | Pass |
| QA-003 | Poll job status | Dashboard updated to completed | Pass |
| QA-004 | Five-job burst test | Five jobs completed, queue drained | Pass |
| QA-005 | Stop worker and enqueue jobs | Two jobs remained queued | Pass |
| QA-006 | Restart worker | Both queued jobs completed | Pass |
| QA-007 | ACK successful processing | Main queue returned to zero | Pass |
| QA-008 | NACK and transient retry | Job completed after three attempts | Pass |
| QA-009 | Permanent processing failure | Job marked failed after three attempts | Pass |
| QA-010 | Reject malformed message | Message routed to `jobs.dead` | Pass |
| QA-011 | Response time under 100 ms | Four of five optimized requests met target | Partial pass |
| QA-012 | Worker crash during active processing | Not explicitly tested | Not tested |

### Response-Time Measurements

PowerShell's `Measure-Command` was used to measure request duration.

| Test | Before Optimization | After Optimization |
|---|---:|---:|
| 1 | 131.26 ms | 144.86 ms |
| 2 | 116.71 ms | 68.75 ms |
| 3 | 113.60 ms | 60.37 ms |
| 4 | 115.07 ms | 59.02 ms |
| 5 | 112.73 ms | 59.55 ms |
| **Average** | **117.87 ms** | **78.51 ms** |

The first optimized request exceeded 100 ms due to connection setup overhead.

The remaining four requests averaged approximately **61.92 ms**.

This demonstrated that reusing RabbitMQ connections improved response times significantly.

### Burst Traffic Test

Five jobs were submitted rapidly using PowerShell:

```powershell
1..5 | ForEach-Object { $n = $_; Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/jobs" -ContentType "application/json" -Body "{`"task`":`"Burst Test Job $n`"}" }
```

RabbitMQ buffered the messages and the worker processed them sequentially.

The worker completed all five jobs, and the main queue returned to zero.

### Worker Recovery Test

The worker process was stopped while FastAPI and RabbitMQ continued running.

Two additional jobs were submitted.

RabbitMQ Management displayed:

```text
jobs queue:
Ready:   2
Unacked: 0
Total:   2
```

After restarting the worker:

- Both jobs were processed successfully.
- Both statuses transitioned to completed.
- The main RabbitMQ queue returned to zero.

This verified queued-message persistence during a worker outage.

A separate test involving termination during an actively unacknowledged job would be needed to demonstrate redelivery after an in-progress worker crash.

### Browser and Terminal Verification

The following tools were used to inspect application behavior:

**Browser Developer Tools**

- Verified API request timing.
- Confirmed that requests returned before the four-second processing task finished.

**RabbitMQ Management Dashboard**

- Observed queued and unacknowledged message counts.
- Confirmed that queues drained after successful processing.
- Verified that a rejected malformed message entered `jobs.dead`.

**Worker Terminal**

- Observed job consumption.
- Verified successful processing.
- Confirmed retry attempts and terminal failures.

## Architectural Trade-Offs

### Benefits of Asynchronous Messaging

**Reduced Temporal Coupling**

The API does not need the background worker to be available when a request is submitted.

**Burst Traffic Handling**

RabbitMQ buffers incoming jobs so the worker can process them at a controlled rate.

**Failure Isolation**

If the worker stops, new jobs can remain queued rather than immediately failing.

**Independent Scaling**

Additional workers can be introduced without redesigning the API.

### Costs and Limitations

**Eventual Consistency**

Job completion is not immediate. Clients must poll the API to determine when processing finishes.

**Additional Infrastructure**

RabbitMQ introduces broker configuration, message monitoring, and operational responsibilities.

**Duplicate Delivery**

RabbitMQ provides at-least-once delivery behavior under appropriate acknowledgment and durability configurations. Workers must be designed to tolerate repeated messages.

**Retry Complexity**

Immediate requeueing can create excessive retries under real outages. Production applications should use delayed retries and backoff strategies.

**Local SQLite Storage**

The shared SQLite database is suitable for this local demonstration but not ideal for independently deployed services or horizontally scaled workers.

**Connection Management**

Thread-local RabbitMQ connections improve warm-request performance but still require connection setup on the first request handled by a thread.

## Future Improvements

Potential improvements for a production environment include:

- PostgreSQL or another shared database for distributed deployment.
- Delayed retries with exponential backoff.
- Improved idempotency for external side effects.
- Transactional outbox/inbox patterns.
- Automated integration and crash-recovery tests.
- Monitoring and alerting for growing queues.
- Explicit handling of stale or lost publisher connections.
- Stronger coordination between message publication and status persistence.

## Deployment

This project was developed and tested locally using Docker Compose.

A public live URL is not currently provided.

The architecture requires a continuously running RabbitMQ broker and background worker, which are not naturally supported by a basic serverless web deployment.

A production deployment would require suitable hosting for the API, persistent broker, worker, and shared database.

## Conclusion

This assignment demonstrated how an asynchronous message broker can separate an API from time-consuming background processing.

The initial AI-generated application already implemented several important distributed messaging practices, including a real RabbitMQ broker, persistent messages, manual ACK/NACK handling, bounded retries, and status polling.

However, reviewing the code identified a missing Dead-Letter Queue and unnecessary connection overhead in the producer.

Adding the DLQ improved malformed-message handling, while reusing RabbitMQ connections significantly reduced API response times.

Testing also demonstrated that the API could continue accepting jobs while the worker was offline, that RabbitMQ buffered bursts of work, and that queued jobs completed after the worker restarted.

The main takeaway is that AI-generated systems can provide a functional foundation, but distributed architectures require careful review of failure handling, message durability, acknowledgment behavior, performance, and operational trade-offs.

**This readme was edited with the use of AI**