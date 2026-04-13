"""
Task Sender Client
Submits tasks to the task manager server and retrieves results.
"""

import socket
import time
from protocol import Message, MessageType, TaskType, create_task


class TaskSenderClient:
    """Client for submitting tasks and getting results"""
    
    def __init__(self, server_host="localhost", server_port=5000):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.submitted_tasks = {}  # task_id -> task_info
    
    def connect(self) -> bool:
        """Connect to task manager server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            print(f"[SENDER] Connected to server at {self.server_host}:{self.server_port}")
            return True
        except Exception as e:
            print(f"[ERROR] Connection failed: {e}")
            return False
    
    def submit_task(self, task_type: TaskType, params: dict) -> str:
        """Submit a task and return task_id"""
        if not self.socket:
            if not self.connect():
                return None
        
        try:
            # Send task submission
            msg = Message(MessageType.SUBMIT_TASK, {
                "task_type": task_type.value,
                "params": params
            })
            
            self.socket.sendall(msg.to_json().encode('utf-8'))
            
            # Receive task_id from server
            data = self.socket.recv(4096)
            response = Message.from_json(data.decode('utf-8'))
            
            if response.msg_type == MessageType.SERVER_ACK:
                task_id = response.data.get("task_id")
                self.submitted_tasks[task_id] = {
                    "task_type": task_type.value,
                    "params": params,
                    "submitted_at": time.time(),
                    "result": None
                }
                print(f"[SENDER] Task submitted: {task_id}")
                return task_id
            else:
                print("[ERROR] Failed to submit task")
                return None
        
        except Exception as e:
            print(f"[ERROR] Submit error: {e}")
            self.socket = None  # Reset socket on error
            return None
    
    def get_result(self, task_id: str, timeout=30) -> dict:
        """Get result of a task (with polling)"""
        if not self.socket:
            print("[ERROR] Not connected to server")
            return None
        
        start_time = time.time()
        poll_interval = 0.5
        
        while time.time() - start_time < timeout:
            try:
                # Request result from server
                msg = Message(MessageType.GET_RESULT, {"task_id": task_id})
                self.socket.sendall(msg.to_json().encode('utf-8'))
                
                # Receive response
                data = self.socket.recv(4096)
                response = Message.from_json(data.decode('utf-8'))
                
                if response.msg_type == MessageType.RESULT_RESPONSE:
                    result = response.data
                    
                    # Check if result is ready
                    if result.get("success") is not None:
                        print(f"[SENDER] Result for {task_id}: {result}")
                        return result
                    elif result.get("status") == "pending":
                        print(f"[SENDER] Task {task_id} still pending... ({int(time.time() - start_time)}s)")
                        time.sleep(poll_interval)
                    else:
                        print(f"[SENDER] Result: {result}")
                        return result
            
            except Exception as e:
                print(f"[ERROR] Get result error: {e}")
                self.socket = None
                return None
        
        print(f"[SENDER] Timeout waiting for result of {task_id}")
        return None
    
    def submit_and_wait(self, task_type: TaskType, params: dict, timeout=30) -> dict:
        """Submit a task and wait for result"""
        task_id = self.submit_task(task_type, params)
        if not task_id:
            return None
        
        time.sleep(0.5)  # Give server time to process
        return self.get_result(task_id, timeout=timeout)
    
    def list_submitted_tasks(self):
        """List all submitted tasks"""
        print("\n[SENDER] Submitted Tasks:")
        print("-" * 70)
        for task_id, info in self.submitted_tasks.items():
            status = "Completed" if info["result"] else "Pending"
            print(f"  ID: {task_id}")
            print(f"  Type: {info['task_type']}")
            print(f"  Params: {info['params']}")
            print(f"  Status: {status}")
            if info["result"]:
                print(f"  Result: {info['result']}")
            print()
    
    def disconnect(self):
        """Disconnect from server"""
        if self.socket:
            self.socket.close()
        print("[SENDER] Disconnected")


def interactive_mode():
    """Interactive task submission mode"""
    client = TaskSenderClient()
    if not client.connect():
        return
    
    print("\n[SENDER] Interactive Mode")
    print("Available task types:")
    print("  1. square <value>")
    print("  2. reverse_string <text>")
    print("  3. uppercase <text>")
    print("  4. fibonacci <n>")
    print("  5. list")
    print("  6. exit")
    print()
    
    try:
        while True:
            try:
                command = input("> ").strip()
                
                if not command:
                    continue
                
                parts = command.split(maxsplit=1)
                cmd = parts[0].lower()
                
                if cmd == "exit":
                    break
                elif cmd == "list":
                    client.list_submitted_tasks()
                elif cmd == "square":
                    if len(parts) < 2:
                        print("Usage: square <value>")
                        continue
                    value = float(parts[1])
                    result = client.submit_and_wait(TaskType.SQUARE, {"value": value})
                
                elif cmd == "reverse_string":
                    if len(parts) < 2:
                        print("Usage: reverse_string <text>")
                        continue
                    text = parts[1]
                    result = client.submit_and_wait(TaskType.REVERSE_STRING, {"text": text})
                
                elif cmd == "uppercase":
                    if len(parts) < 2:
                        print("Usage: uppercase <text>")
                        continue
                    text = parts[1]
                    result = client.submit_and_wait(TaskType.UPPERCASE, {"text": text})
                
                elif cmd == "fibonacci":
                    if len(parts) < 2:
                        print("Usage: fibonacci <n>")
                        continue
                    n = int(parts[1])
                    result = client.submit_and_wait(TaskType.FIBONACCI, {"n": n})
                
                else:
                    print("Unknown command")
            
            except ValueError as e:
                print(f"Invalid input: {e}")
            except Exception as e:
                print(f"Error: {e}")
    
    except KeyboardInterrupt:
        print("\n[SENDER] Exiting...")
    
    finally:
        client.disconnect()


def demo_mode():
    """Demo mode with sample tasks"""
    client = TaskSenderClient()
    if not client.connect():
        return
    
    print("\n[SENDER] Demo Mode - Submitting sample tasks...")
    
    tasks = [
        (TaskType.SQUARE, {"value": 5}, "Square of 5"),
        (TaskType.REVERSE_STRING, {"text": "Hello World"}, "Reverse 'Hello World'"),
        (TaskType.UPPERCASE, {"text": "hello"}, "Uppercase 'hello'"),
        (TaskType.FIBONACCI, {"n": 10}, "Fibonacci(10)"),
        (TaskType.SQUARE, {"value": 12}, "Square of 12"),
    ]
    
    print("\nSubmitting tasks...\n")
    for task_type, params, description in tasks:
        print(f"Submitting: {description}")
        task_id = client.submit_task(task_type, params)
        time.sleep(0.5)
    
    print("\n" + "="*70)
    print("Waiting for results...\n")
    
    for task_id in client.submitted_tasks.keys():
        result = client.get_result(task_id, timeout=30)
        if result and result.get("success"):
            print(f"✓ {task_id}: {result.get('result')}")
        elif result and result.get("error"):
            print(f"✗ {task_id}: ERROR - {result.get('error')}")
        time.sleep(0.3)
    
    print("\n" + "="*70)
    client.list_submitted_tasks()
    client.disconnect()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo_mode()
    else:
        interactive_mode()
