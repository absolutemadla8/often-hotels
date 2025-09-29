# Celery Background Tasks - Complete Deep Dive

This document provides an in-depth explanation of how Celery background task processing works in the Often Hotels application.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │  Redis Broker   │    │ Celery Workers  │    │   PostgreSQL    │
│                 │───▶│                 │───▶│                 │───▶│                 │
│ 1. Create Task  │    │ 2. Queue Task   │    │ 3. Execute Task │    │ 4. Store Status │
│ 4. Check Status │◀───│ 5. Get Results  │◀───│ 6. Update DB    │◀───│ 5. Task Results │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
         │                                              │
         └─────────────── Direct DB Access ─────────────┘
                        (Task Status & Progress)
```

## 🔧 Core Components Breakdown

### 1. Redis - The Message Broker & Result Backend

**File:** Uses Redis service in `docker-compose.yml`

**Role:**
- **Message Broker**: Stores task queues and distributes tasks to workers
- **Result Backend**: Stores task results and intermediate states
- **Pub/Sub**: Handles real-time communication between components

**How it works:**
```bash
# Redis stores tasks as serialized JSON messages in lists (queues)
redis:127.0.0.1:6379> LLEN celery        # Main queue length
redis:127.0.0.1:6379> LLEN email         # Email queue length
redis:127.0.0.1:6379> LLEN hotel_processing  # Hotel queue length

# Results are stored as key-value pairs
redis:127.0.0.1:6379> GET celery-task-meta-<task_id>  # Task result
```

**Queue Structure:**
- `celery` - Default queue
- `email` - Email sending tasks
- `hotel_processing` - Hotel search/sync tasks  
- `notifications` - Push notifications
- `maintenance` - Cleanup tasks

### 2. Celery Configuration (`app/core/celery_app.py`)

**Purpose:** Central configuration for the entire Celery ecosystem

```python
celery_app = Celery(
    "often-hotels",           # App name
    broker=settings.REDIS_URL,    # Where to send tasks
    backend=settings.REDIS_URL,   # Where to store results
    include=[...]                 # Task modules to load
)
```

**Key Configuration Sections:**

#### Task Serialization
```python
task_serializer="json",      # How tasks are encoded
accept_content=["json"],     # What content types to accept
result_serializer="json",    # How results are encoded
```

#### Task Routing
```python
task_routes={
    "app.tasks.email_tasks.*": {"queue": "email"},
    "app.tasks.hotel_tasks.*": {"queue": "hotel_processing"},
    # ... routes tasks to specific queues based on module
}
```

#### Periodic Tasks (Beat Schedule)
```python
beat_schedule={
    "cleanup-expired-tokens": {
        "task": "app.tasks.cleanup_tasks.cleanup_expired_refresh_tokens",
        "schedule": 60.0 * 60.0,  # Every hour
    },
    # ... scheduled tasks that run automatically
}
```

### 3. Task Models (`app/models/models.py`)

**TaskStatus Enum:**
```python
class TaskStatus(str, Enum):
    PENDING = "pending"    # Task created, waiting to be picked up
    STARTED = "started"    # Worker is processing the task
    SUCCESS = "success"    # Task completed successfully
    FAILURE = "failure"    # Task failed with error
    RETRY = "retry"        # Task is being retried
    REVOKED = "revoked"    # Task was cancelled
```

**Task Model Fields Explained:**
```python
class Task(Model):
    # Identity
    task_id = fields.CharField(max_length=255, unique=True)  # Celery UUID
    task_name = fields.CharField(max_length=255)             # Function name
    task_type = fields.CharField(max_length=100)             # Category
    
    # Execution tracking
    started_at = fields.DatetimeField(null=True)             # When worker started
    completed_at = fields.DatetimeField(null=True)           # When finished
    execution_time_seconds = fields.FloatField(null=True)    # Duration
    
    # Data & Results
    task_args = fields.JSONField(null=True)                  # Function arguments
    task_kwargs = fields.JSONField(null=True)                # Keyword arguments
    result = fields.JSONField(null=True)                     # Success result
    error_message = fields.TextField(null=True)              # Error details
    
    # Progress tracking
    progress_current = fields.IntField(default=0)            # Current step
    progress_total = fields.IntField(default=100)            # Total steps
    progress_message = fields.CharField(max_length=500)      # Status message
    
    # Queue management
    queue_name = fields.CharField(max_length=100)            # Which queue
    priority = fields.IntField(default=0)                    # Task priority
```

### 4. Base Task Class (`app/tasks/base.py`)

**Purpose:** Provides database integration for all tasks

**Key Method - `update_task_status`:**
```python
async def update_task_status(
    self,
    task_id: str,
    status: TaskStatus,
    progress_current: Optional[int] = None,
    progress_message: Optional[str] = None,
    result: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None
):
```

**What it does:**
1. Finds task record in PostgreSQL by `task_id`
2. Updates status, progress, timestamps
3. Calculates execution time automatically
4. Stores results or error messages
5. Provides real-time progress tracking

**Lifecycle Hooks:**
```python
def on_success(self, retval, task_id, args, kwargs):
    # Called when task completes successfully
    
def on_failure(self, exc, task_id, args, kwargs, einfo):
    # Called when task fails
    
def on_retry(self, exc, task_id, args, kwargs, einfo):
    # Called when task is retried
```

## 📝 How to Create and Add Jobs

### 1. Creating a New Task Type

**Step 1: Create the task function**
```python
# app/tasks/my_new_tasks.py
@celery_app.task(bind=True, base=BaseTask)
def process_payment(self, user_id: int, payment_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process user payment in background"""
    return asyncio.run(_process_payment_async(self, user_id, payment_data))

async def _process_payment_async(task_instance, user_id: int, payment_data: Dict[str, Any]):
    task_id = task_instance.request.id
    
    try:
        # 1. Initialize database connection
        if not Tortoise._get_db(None):
            from tortoise_config import TORTOISE_ORM
            await Tortoise.init(config=TORTOISE_ORM)
        
        # 2. Mark task as started
        await task_instance.update_task_status(task_id, TaskStatus.STARTED)
        
        # 3. Validate payment data
        await task_instance.update_task_status(
            task_id,
            TaskStatus.STARTED,
            progress_current=20,
            progress_message="Validating payment information"
        )
        
        # 4. Process payment with external service
        await task_instance.update_task_status(
            task_id,
            TaskStatus.STARTED,
            progress_current=60,
            progress_message="Processing payment with payment gateway"
        )
        
        # Simulate payment processing
        await asyncio.sleep(2)
        
        # 5. Update user account
        await task_instance.update_task_status(
            task_id,
            TaskStatus.STARTED,
            progress_current=90,
            progress_message="Updating user account"
        )
        
        # 6. Return success result
        result = {
            "success": True,
            "user_id": user_id,
            "transaction_id": "txn_123456",
            "amount": payment_data.get("amount"),
            "currency": payment_data.get("currency", "USD"),
            "processed_at": datetime.utcnow().isoformat()
        }
        
        await task_instance.update_task_status(task_id, TaskStatus.SUCCESS, result=result)
        return result
        
    except Exception as e:
        error_msg = f"Payment processing failed: {str(e)}"
        await task_instance.update_task_status(task_id, TaskStatus.FAILURE, error_message=error_msg)
        raise
```

**Step 2: Add to Celery configuration**
```python
# app/core/celery_app.py
celery_app = Celery(
    "often-hotels",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.email_tasks",
        "app.tasks.hotel_tasks", 
        "app.tasks.notification_tasks",
        "app.tasks.cleanup_tasks",
        "app.tasks.my_new_tasks"  # Add your new module
    ]
)

# Add routing
task_routes={
    "app.tasks.my_new_tasks.*": {"queue": "payments"},  # New queue
    # ... existing routes
}
```

**Step 3: Create API endpoint**
```python
# app/api/v1/endpoints/tasks.py
class PaymentRequest(BaseModel):
    user_id: int
    amount: float
    currency: str = "USD"
    payment_method: str
    billing_address: Dict[str, Any]

@router.post("/payment", response_model=Dict[str, str])
async def create_payment_task(
    request: PaymentRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Create payment processing task"""
    try:
        from app.tasks.my_new_tasks import process_payment
        
        payment_data = {
            "amount": request.amount,
            "currency": request.currency,
            "payment_method": request.payment_method,
            "billing_address": request.billing_address
        }
        
        # Queue the task
        celery_task = process_payment.delay(request.user_id, payment_data)
        
        # Create database record
        await Task.create(
            task_id=celery_task.id,
            task_name="process_payment",
            task_type="payment",
            user=current_user,
            task_args=[request.user_id],
            task_kwargs={"payment_data": payment_data},
            queue_name="payments"
        )
        
        return {
            "task_id": celery_task.id,
            "status": "queued",
            "message": "Payment processing started"
        }
        
    except Exception as e:
        logger.error(f"Error creating payment task: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### 2. Task Execution Flow

**When a task is created:**

1. **API Request** → FastAPI endpoint receives request
2. **Task Creation** → `task.delay()` creates task in Redis queue
3. **Database Record** → Task record created in PostgreSQL
4. **Worker Pickup** → Available worker pulls task from Redis
5. **Execution** → Worker runs task function
6. **Progress Updates** → Task updates status in PostgreSQL
7. **Completion** → Final result stored in both Redis and PostgreSQL

**Detailed execution:**
```python
# 1. Client calls API
POST /api/v1/tasks/email
{
    "user_id": 123,
    "email_type": "welcome"
}

# 2. FastAPI creates Celery task
celery_task = send_welcome_email.delay(123)

# 3. Task queued in Redis
REDIS: LPUSH email '{"id": "task-uuid", "task": "send_welcome_email", "args": [123]}'

# 4. Worker picks up task
WORKER: task = redis.brpop("email")

# 5. Worker executes task
WORKER: result = send_welcome_email(123)

# 6. Updates database during execution
DATABASE: UPDATE tasks SET status='started', progress_current=30 WHERE task_id='task-uuid'

# 7. Stores final result
REDIS: SET "celery-task-meta-task-uuid" '{"status": "SUCCESS", "result": {...}}'
DATABASE: UPDATE tasks SET status='success', result='{...}' WHERE task_id='task-uuid'
```

## 📊 Task Processing Deep Dive

### Queue Management

**How queues work:**
- Each queue is a Redis list
- Tasks are pushed to the left (`LPUSH`)
- Workers pop from the right (`BRPOP` - blocking operation)
- Multiple workers can consume from the same queue
- Tasks are distributed round-robin among workers

**Queue prioritization:**
```python
# High priority queue processed first
celery_app.conf.task_routes = {
    "urgent_tasks.*": {"queue": "urgent", "priority": 9},
    "normal_tasks.*": {"queue": "normal", "priority": 5},
    "low_tasks.*": {"queue": "low", "priority": 1},
}
```

### Worker Concurrency

**How workers handle multiple tasks:**
```bash
# Each worker can handle multiple tasks simultaneously
celery -A app.core.celery_app:celery_app worker --concurrency=4
```

**Concurrency models:**
- **Prefork (default)**: Separate processes for each task
- **Eventlet**: Async I/O for many concurrent tasks
- **Gevent**: Similar to eventlet
- **Solo**: Single process (development only)

### Error Handling & Retries

**Automatic retries:**
```python
@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3})
def reliable_task(self):
    # Task will automatically retry up to 3 times on any exception
    pass
```

**Custom retry logic:**
```python
@celery_app.task(bind=True)
def custom_retry_task(self):
    try:
        # Task logic here
        pass
    except SomeSpecificError as exc:
        # Custom retry with exponential backoff
        raise self.retry(exc=exc, countdown=60, max_retries=3)
```

## 🔍 Real-time Monitoring & Status

### Database Status Tracking

**How to check task status:**
```python
# Via database
task = await Task.get(task_id="uuid-here")
print(f"Status: {task.status}")
print(f"Progress: {task.progress_percentage}%")
print(f"Message: {task.progress_message}")

# Via Celery
from app.core.celery_app import celery_app
result = celery_app.AsyncResult("uuid-here")
print(f"State: {result.state}")
print(f"Info: {result.info}")
```

**Task lifecycle in database:**
```sql
-- Task creation
INSERT INTO tasks (task_id, task_name, status) VALUES ('uuid', 'send_email', 'pending');

-- Worker starts processing
UPDATE tasks SET status='started', started_at=NOW() WHERE task_id='uuid';

-- Progress updates
UPDATE tasks SET progress_current=50, progress_message='Sending email' WHERE task_id='uuid';

-- Task completion
UPDATE tasks SET status='success', completed_at=NOW(), execution_time_seconds=2.5 WHERE task_id='uuid';
```

### Flower Monitoring Dashboard

**Access:** http://localhost:5555

**What Flower shows:**
- **Active tasks**: Currently running tasks
- **Task history**: Past task executions
- **Worker status**: Which workers are online
- **Queue lengths**: How many tasks are waiting
- **Task details**: Arguments, results, tracebacks
- **Broker monitoring**: Redis connection status

## 🚀 Advanced Features

### Task Chaining

**Sequential task execution:**
```python
from celery import chain

# Execute tasks in sequence
workflow = chain(
    validate_payment.s(payment_data),
    process_payment.s(),
    send_confirmation_email.s()
)
result = workflow.apply_async()
```

### Task Groups

**Parallel task execution:**
```python
from celery import group

# Execute tasks in parallel
job = group([
    send_email.s(user_id) for user_id in user_ids
])
result = job.apply_async()
```

### Canvas Workflows

**Complex workflows:**
```python
from celery import chord

# Run tasks in parallel, then run callback
callback = send_summary_email.s()
job = chord([
    process_hotel_data.s(hotel_id) for hotel_id in hotel_ids
])(callback)
```

### Custom Task Classes

**Specialized task behavior:**
```python
class DatabaseTask(BaseTask):
    """Task that ensures database connection"""
    
    def __call__(self, *args, **kwargs):
        # Setup database connection
        return super().__call__(*args, **kwargs)

@celery_app.task(base=DatabaseTask)
def db_intensive_task():
    # Task that needs special database handling
    pass
```

## 🏃‍♂️ Running the System

### Development Mode
```bash
# Start all services locally
./scripts/start_celery.sh

# Or start individually
celery -A app.core.celery_app:celery_app worker --loglevel=info
celery -A app.core.celery_app:celery_app beat --loglevel=info
celery -A app.core.celery_app:celery_app flower --port=5555
```

### Production Mode (Docker)
```bash
# Start all services including workers
docker-compose up -d

# Scale workers
docker-compose up --scale celery-worker=3

# View logs
docker-compose logs -f celery-worker
docker-compose logs -f celery-beat
docker-compose logs -f celery-flower
```

### Environment Configuration

**Required environment variables:**
```bash
# Database connection
DATABASE_URL=postgres://user:pass@host:port/db

# Redis connection  
REDIS_URL=redis://host:port/db

# API keys (for external services)
SECRET_KEY=your-secret-key
SERP_API_KEY=your-serp-key
TRAVCLAN_API_KEY=your-travclan-key
```

## 🐛 Debugging & Troubleshooting

### Common Issues

**1. Tasks not executing**
```bash
# Check worker status
celery -A app.core.celery_app:celery_app inspect active

# Check queue length
redis-cli LLEN email

# Check worker logs
docker-compose logs celery-worker
```

**2. Database connection issues**
```python
# Task fails with "Database not initialized"
# Solution: Ensure Tortoise.init() is called in async tasks
if not Tortoise._get_db(None):
    from tortoise_config import TORTOISE_ORM
    await Tortoise.init(config=TORTOISE_ORM)
```

**3. Memory leaks**
```bash
# Restart workers periodically
celery -A app.core.celery_app:celery_app worker --max-tasks-per-child=1000
```

### Performance Monitoring

**Key metrics to track:**
- Task execution time
- Queue lengths
- Worker memory usage
- Error rates
- Throughput (tasks/second)

**Monitoring queries:**
```sql
-- Average execution time by task type
SELECT task_type, AVG(execution_time_seconds) 
FROM tasks 
WHERE completed_at > NOW() - INTERVAL '1 day'
GROUP BY task_type;

-- Failed tasks in last hour
SELECT COUNT(*) 
FROM tasks 
WHERE status = 'failure' 
AND created_at > NOW() - INTERVAL '1 hour';

-- Queue backlog
SELECT task_type, COUNT(*) 
FROM tasks 
WHERE status = 'pending'
GROUP BY task_type;
```

## 🔐 Security Considerations

### Task Data Security
- Sensitive data should not be passed as task arguments
- Use references (IDs) instead of sensitive data
- Encrypt sensitive task results

### Queue Security
- Redis should be behind firewall
- Use Redis AUTH if needed
- Consider Redis TLS for production

### Worker Security  
- Run workers with minimal privileges
- Validate all task inputs
- Sanitize data before processing

This system provides a robust, scalable background task processing solution that can handle everything from simple email sending to complex multi-step workflows with full monitoring and error handling capabilities.