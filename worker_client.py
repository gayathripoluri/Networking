"""
Worker Client
Connects to task manager server and processes assigned tasks.
"""

import socket
import threading
import time
import sys
from protocol import Message, MessageType, TaskType, create_result


class TaskProcessor:
    """Processes different types of tasks"""
    
    @staticmethod
    def process_square(value: float) -> float:
        """Compute square of a number"""
        return value ** 2
    
    @staticmethod
    def process_reverse_string(text: str) -> str:
        """Reverse a string"""
        return text[::-1]
    
    @staticmethod
    def process_uppercase(text: str) -> str:
        """Convert string to uppercase"""
        return text.upper()
    
    @staticmethod
    def process_fibonacci(n: int) -> int:
        """Compute fibonacci number"""
        if n <= 0:
            return 0
        elif n == 1:
            return 1
        else:
            a, b = 0, 1
            for _ in range(2, n + 1):
                a, b = b, a + b
            return b
    
    @staticmethod
    def process(task_type: str, params: dict):
        """Process a task based on type"""
        try:
            if task_type == TaskType.SQUARE.value:
                result = TaskProcessor.process_square(params.get("value", 0))
            elif task_type == TaskType.REVERSE_STRING.value:
                result = TaskProcessor.process_reverse_string(params.get("text", ""))
            elif task_type == TaskType.UPPERCASE.value:
                result = TaskProcessor.process_uppercase(params.get("text", ""))
            elif task_type == TaskType.FIBONACCI.value:
                result = TaskProcessor.process_fibonacci(params.get("n", 0))
            else:
                raise ValueError(f"Unknown task type: {task_type}")
            
            return result, None
        except Exception as e:
            return None, str(e)


class WorkerClient:
    """Worker client that processes tasks"""
    
    def __init__(self, server_host="localhost", server_port=5000, worker_name=None):
        self.server_host = server_host
        self.server_port = server_port
        self.worker_name = worker_name or f"worker_{int(time.time())}"
        self.socket = None
        self.running = False
        self.worker_id = None
        self.task_processor = TaskProcessor()
    
    def connect(self) -> bool:
        """Connect to task manager server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            
            # Register with server
            msg = Message(MessageType.WORKER_REGISTER, {"name": self.worker_name})
            self.socket.sendall(msg.to_json().encode('utf-8'))
            
            # Receive worker_id
            data = self.socket.recv(4096)
            response = Message.from_json(data.decode('utf-8'))
            
            if response.msg_type == MessageType.SERVER_ACK:
                self.worker_id = response.data.get("worker_id")
                print(f"[WORKER] Connected with ID: {self.worker_id}")
                return True
            else:
                print("[ERROR] Failed to register with server")
                return False
        
        except Exception as e:
            print(f"[ERROR] Connection failed: {e}")
            return False
    
    def start(self):
        """Start processing tasks"""
        if not self.connect():
            return
        
        self.running = True
        print(f"[WORKER] {self.worker_name} started and waiting for tasks...")
        
        try:
            while self.running:
                # Receive task from server
                data = self.socket.recv(4096)
                if not data:
                    print("[WORKER] Server closed connection")
                    break
                
                msg = Message.from_json(data.decode('utf-8'))
                
                if msg.msg_type == MessageType.TASK_ASSIGN:
                    # Process the assigned task
                    task = msg.data.get("task")
                    self._process_task(task)
                else:
                    print(f"[WORKER] Unknown message type: {msg.msg_type}")
        
        except Exception as e:
            print(f"[ERROR] Worker error: {e}")
        
        finally:
            self.stop()
    
    def _process_task(self, task: dict):
        """Process a single task and send result back"""
        task_id = task.get("task_id")
        task_type = task.get("task_type")
        params = task.get("params", {})
        
        print(f"[WORKER] Processing task {task_id} ({task_type})...")
        
        # Process the task
        result, error = self.task_processor.process(task_type, params)
        
        # Create result
        result_dict = create_result(task_id, result, error)
        
        # Send result back to server
        msg = Message(MessageType.WORKER_RESULT, {"result": result_dict})
        self.socket.sendall(msg.to_json().encode('utf-8'))
        
        if error:
            print(f"[WORKER] Task {task_id} failed: {error}")
        else:
            print(f"[WORKER] Task {task_id} completed: {result}")
    
    def stop(self):
        """Stop the worker"""
        self.running = False
        if self.socket:
            self.socket.close()
        print(f"[WORKER] {self.worker_name} stopped")


def main():
    """Run worker client"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Worker Client")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=5000, help="Server port")
    parser.add_argument("--name", default=None, help="Worker name")
    
    args = parser.parse_args()
    
    worker = WorkerClient(
        server_host=args.host,
        server_port=args.port,
        worker_name=args.name
    )
    
    try:
        worker.start()
    except KeyboardInterrupt:
        print("\n[WORKER] Shutting down...")
        worker.stop()


if __name__ == "__main__":
    main()
