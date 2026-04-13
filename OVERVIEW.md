# Distributed Task Processing System - Project Overview

## Project Context

This is a **TCP/IP-based distributed computing system** where:
- A **central server** distributes work to multiple machines
- **Worker clients** process tasks in parallel
- **Task senders** submit jobs and get results back

It's like a job scheduler - similar to how cloud services distribute tasks across multiple servers.

---

## What Each Component Does

### **1. `protocol.py`** - The Communication Standard

This defines how all components talk to each other:

- **Message Types**: WORKER_REGISTER, TASK_ASSIGN, WORKER_RESULT, SUBMIT_TASK, GET_RESULT
- **Task Types**: SQUARE, REVERSE_STRING, UPPERCASE, FIBONACCI
- **Message Format**: JSON-based messages with type and data

**Example message:**
```json
{
  "type": "task_assign",
  "data": {
    "task": {
      "task_id": "task_1",
      "task_type": "square",
      "params": {"value": 5}
    }
  }
}
```

**Key Classes:**
- `Message` - Wraps JSON messages
- `TaskType` - Enum of available task types
- `MessageType` - Enum of message types
- Helper functions for creating tasks and results

---

### **2. `task_manager_server.py`** - The Central Hub

The server that coordinates everything.

**Key Classes:**

- **TaskQueue**: Stores pending tasks and completed results
  - Thread-safe using locks
  - Maintains task counter and completed_tasks dictionary
  
- **WorkerTracker**: Keeps track of connected workers
  - Lists registered workers with their status (ready/busy)
  - Finds idle workers for task assignment
  
- **TaskManagerServer**: Main server implementation
  - Listens on port 5000 for connections
  - Spawns handler threads for each client
  - Runs a dispatcher thread for task distribution

**What It Does:**

1. Listens on port 5000 for connections
2. Workers register themselves → gets unique worker ID
3. Task senders submit jobs → gets task ID
4. Continuously finds idle workers and assigns them pending tasks
5. Collects results from workers and stores them
6. Task senders poll to retrieve their results

**Workflow:**
```
Task Sender submits "square(5)"
           ↓
Server queues task → Dispatcher thread finds idle worker
           ↓
Server sends task to Worker 1 → Worker processes it
           ↓
Worker sends back result = 25
           ↓
Server stores result → Task Sender retrieves it
```

**Threading Model:**
- Main thread: Accepts connections
- Worker handler threads: Listen for results from workers
- Sender handler threads: Receive task submissions and result queries
- Dispatcher thread: Continuously assigns queued tasks to idle workers

---

### **3. `worker_client.py`** - The Processor

Workers that do the actual work.

**Key Classes:**

- **TaskProcessor**: Contains the actual task implementations
  - `process_square(value)` → returns value²
  - `process_reverse_string(text)` → returns reversed text
  - `process_uppercase(text)` → returns uppercase text
  - `process_fibonacci(n)` → returns nth Fibonacci number
  
- **WorkerClient**: Manages server connection and task processing loop

**What It Does:**

1. Connects to server and registers (gets unique worker ID)
2. Waits for server to send task assignments
3. When task arrives, processes it based on type
4. Sends result back to server
5. Goes back to waiting for next task

**You can run multiple workers** to process tasks in parallel:
```bash
python worker_client.py --name "worker_1"  # Processes tasks in parallel
python worker_client.py --name "worker_2"  # Processes tasks in parallel
python worker_client.py --name "worker_3"  # Processes tasks in parallel
```

**Task Processing Flow:**
1. Receive task from server
2. Extract task type and parameters
3. Call appropriate processor method
4. Capture result or error
5. Send result message back to server
6. Wait for next task

---

### **4. `task_sender.py`** - The Job Submitter

Client that submits jobs to the system.

**Key Class:**
- **TaskSenderClient**: Submits tasks and retrieves results

**Two Modes:**

**Interactive Mode:** You type commands
```bash
$ python task_sender.py
> square 5
[SENDER] Task submitted: task_1
[SENDER] Result: 25
> reverse_string hello
[SENDER] Result: olleh
> fibonacci 10
[SENDER] Result: 55
> list
> exit
```

**Demo Mode:** Automatically submits sample tasks
```bash
python task_sender.py demo
```

**What It Does:**

1. Connects to server
2. Submits a task with parameters
3. Gets back a task ID
4. Polls the server asking "is result ready?"
5. Once ready, displays the result

**Usage Patterns:**
- `submit_task()` - Fire and forget
- `get_result()` - Poll for result
- `submit_and_wait()` - Synchronous (submit + wait)

---

### **5. `README.md`** - User Documentation

Complete guide on:
- How to start the system
- System architecture overview
- Task types and examples
- Configuration options
- Troubleshooting

---

### **6. `requirements.txt`** - Dependencies

Lists what you need to install. 

**Note:** This project uses **zero external dependencies** - only Python's standard library:
- `socket` - TCP/IP networking
- `threading` - Multi-threading
- `json` - Message serialization
- `queue` - Thread-safe task queue
- `uuid` - Unique IDs
- `time` - Timestamps
- `enum` - Task type definitions

---

## Complete Data Flow Example

```
TERMINAL 1: Start Server
$ python task_manager_server.py
[SERVER] Started on 0.0.0.0:5000
[SERVER] Waiting for connections...

TERMINAL 2: Start Worker 1
$ python worker_client.py --name "worker_1"
[WORKER] Connected with ID: worker_abc123
[WORKER] Waiting for tasks...

TERMINAL 3: Start Worker 2
$ python worker_client.py --name "worker_2"
[WORKER] Connected with ID: worker_def456
[WORKER] Waiting for tasks...

TERMINAL 4: Submit Tasks
$ python task_sender.py
> square 5
[SENDER] Task submitted: task_1_timestamp
[SENDER] Task task_1_timestamp still pending...
[SENDER] Result: 25  ✓

> fibonacci 10
[SENDER] Task submitted: task_2_timestamp
[SENDER] Result: 55  ✓
```

**What's happening:**
1. Server starts and waits for connections on port 5000
2. Worker 1 connects and registers
3. Worker 2 connects and registers
4. Task sender submits "square 5" 
5. Server receives it, queues it
6. Dispatcher finds idle worker (worker 1)
7. Server sends task to worker 1
8. Worker 1 calculates 5² = 25
9. Worker 1 sends result back
10. Server stores result
11. Task sender polls and gets result: 25
12. Same process for fibonacci task (worker 2 picks it up)

---

## Why This Architecture?

1. **Scalability** - Add more workers to process more tasks
2. **Parallelism** - Multiple workers process tasks simultaneously
3. **Separation of Concerns** - Each component has one clear job
4. **Network-Based** - Works across different machines/networks
5. **Robust** - If one worker crashes, others keep processing
6. **Asynchronous** - Task senders don't wait; they submit and poll

---

## Real-World Analogy

Think of it like a **restaurant**:

- **Server** = Cashier/Manager who takes orders and assigns to chefs
- **Workers** = Chefs who cook the food
- **Task Sender** = Customer who orders food

```
Customer orders "square(5)"
           ↓
Cashier receives order, writes it down
           ↓
Cashier sees Chef 1 is free, hands task to Chef 1
           ↓
Chef 1 cooks it: 5 × 5 = 25
           ↓
Chef 1 hands result back to Cashier
           ↓
Cashier gives result to Customer: "Your order is done, result is 25"
```

---

## Thread Safety & Concurrency

The server uses **multiple threads** to handle many connections simultaneously:

- **Main thread** - Accepts new connections
- **Worker handler threads** - One per connected worker
  - Listen for completed tasks
  - Update worker status
  
- **Sender handler threads** - One per task sender
  - Receive task submissions
  - Return task results
  
- **Dispatcher thread** - Continuously assigns tasks
  - Gets pending tasks from queue
  - Finds idle workers
  - Sends task assignments

**Thread Safety Mechanisms:**
- `queue.Queue` for task queue (inherently thread-safe)
- `threading.Lock` for worker tracker
- Atomic status updates for worker states
- No shared mutable state between handler threads

---

## Key Technologies Demonstrated

This project is a practical demonstration of:

✅ **TCP/IP Networking** - Socket programming, client-server communication  
✅ **Distributed Systems** - Distributed task processing, coordination  
✅ **Multi-threading** - Concurrent connection handling  
✅ **Task Queuing** - Producer-consumer pattern  
✅ **Asynchronous Message Passing** - JSON-based protocol  
✅ **Thread Safety** - Locks, queues, atomic operations  

---

## How to Run

**Step 1: Start Server**
```bash
python task_manager_server.py
```

**Step 2: Start Workers (in separate terminals)**
```bash
python worker_client.py --name "worker_1"
python worker_client.py --name "worker_2"
```

**Step 3: Submit Tasks (in another terminal)**
```bash
# Interactive mode
python task_sender.py

# Or demo mode
python task_sender.py demo
```

---

## System Performance

**Throughput:**
- Limited by worker processing capacity
- Typical: 100-1000 tasks/second per worker (task-dependent)

**Latency (end-to-end):**
- Network transmission: 1-10ms
- Server dispatch: 1-5ms
- Task processing: 1ms - seconds (depends on task)
- Result retrieval: 1-10ms
- **Total: 5ms to seconds+ (depends on task complexity)**

**Scalability:**
- **Horizontal** - Add more workers
- **Vertical** - Faster hardware
- **Bottleneck** - Central server (mitigated by async dispatch)

---

## Extending the System

### Adding a New Task Type

**Example: Add a "CUBE" task**

**Step 1: Add to protocol.py**
```python
class TaskType(Enum):
    CUBE = "cube"  # New task type
```

**Step 2: Add processor in worker_client.py**
```python
@staticmethod
def process_cube(value: float) -> float:
    return value ** 3
```

**Step 3: Add to process() method**
```python
elif task_type == TaskType.CUBE.value:
    result = TaskProcessor.process_cube(params.get("value"))
```

**Step 4: Use in task_sender.py**
```python
client.submit_task(TaskType.CUBE, {"value": 3})  # Returns 27
```

---

## Security Note

This is an **educational project**. For production use, add:
- SSL/TLS encryption
- Authentication (tokens/certificates)
- Input validation
- Rate limiting
- Audit logging

---

## File Structure

```
project/
├── protocol.py              # Shared protocol definitions
├── task_manager_server.py   # Main server
├── worker_client.py         # Worker implementation
├── task_sender.py           # Task submission client
├── README.md                # User documentation
├── requirements.txt         # Dependencies (none!)
└── OVERVIEW.md             # This file
```

---

## Summary

This is a complete, working **distributed computing system** built with:
- Pure Python (no external libraries)
- TCP/IP networking
- Multi-threading
- JSON-based protocol
- ~1000 lines of code total

It demonstrates core concepts of distributed systems, networking, and concurrent programming - perfect for learning or as a foundation for more advanced systems.
