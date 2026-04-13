"""
Task Manager Server
Coordinates task distribution among worker clients.
Maintains task queue and tracks worker status.
"""

import socket
import threading
import queue
import uuid
import time
from datetime import datetime
from typing import Dict, Optional, Tuple
from collections import defaultdict

from protocol import Message, MessageType, TaskType, create_task, create_result


class TaskQueue:
    """Thread-safe task queue"""
    
    def __init__(self):
        self.queue = queue.Queue()
        self.lock = threading.Lock()
        self.completed_tasks = {}  # task_id -> result
        self.task_counter = 0
    
    def add_task(self, task_type: TaskType, params: dict) -> str:
        """Add a task to the queue and return task_id"""
        self.task_counter += 1
        task_id = f"task_{self.task_counter}_{int(time.time() * 1000)}"
        task = create_task(task_id, task_type, params)
        self.queue.put(task)
        print(f"[QUEUE] Task added: {task_id} ({task_type.value})")
        return task_id
    
    def get_task(self, timeout=10) -> Optional[dict]:
        """Get a task from the queue"""
        try:
            return self.queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def mark_complete(self, task_id: str, result: dict):
        """Mark task as complete with result"""
        with self.lock:
            self.completed_tasks[task_id] = result
            print(f"[QUEUE] Task completed: {task_id}")
    
    def get_result(self, task_id: str) -> Optional[dict]:
        """Get result of completed task"""
        with self.lock:
            return self.completed_tasks.get(task_id)
    
    def queue_size(self) -> int:
        """Get current queue size"""
        return self.queue.qsize()


class WorkerTracker:
    """Tracks connected workers and their status"""
    
    def __init__(self):
        self.workers = {}  # worker_id -> {"socket": socket, "addr": addr, "status": "ready"}
        self.lock = threading.Lock()
    
    def register_worker(self, worker_id: str, sock: socket.socket, addr: Tuple[str, int]):
        """Register a new worker"""
        with self.lock:
            self.workers[worker_id] = {
                "socket": sock,
                "addr": addr,
                "status": "ready",
                "connected_at": datetime.now()
            }
            print(f"[WORKERS] Worker registered: {worker_id} from {addr}")
    
    def get_ready_worker(self) -> Optional[Tuple[str, socket.socket]]:
        """Get a ready worker"""
        with self.lock:
            for worker_id, info in self.workers.items():
                if info["status"] == "ready":
                    info["status"] = "busy"
                    return worker_id, info["socket"]
        return None
    
    def mark_ready(self, worker_id: str):
        """Mark worker as ready"""
        with self.lock:
            if worker_id in self.workers:
                self.workers[worker_id]["status"] = "ready"
    
    def remove_worker(self, worker_id: str):
        """Remove a disconnected worker"""
        with self.lock:
            if worker_id in self.workers:
                del self.workers[worker_id]
                print(f"[WORKERS] Worker removed: {worker_id}")
    
    def get_status(self) -> dict:
        """Get current status of all workers"""
        with self.lock:
            return {
                "total_workers": len(self.workers),
                "ready_workers": sum(1 for w in self.workers.values() if w["status"] == "ready"),
                "busy_workers": sum(1 for w in self.workers.values() if w["status"] == "busy"),
                "workers": {
                    worker_id: {
                        "status": info["status"],
                        "address": f"{info['addr'][0]}:{info['addr'][1]}"
                    }
                    for worker_id, info in self.workers.items()
                }
            }


class TaskManagerServer:
    """Main server that coordinates task distribution"""
    
    def __init__(self, host="localhost", port=5000):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.task_queue = TaskQueue()
        self.worker_tracker = WorkerTracker()
        self.task_dispatcher = None
        self.task_dispatcher_thread = None
    
    def start(self):
        """Start the server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        
        self.running = True
        print(f"[SERVER] Started on {self.host}:{self.port}")
        print(f"[SERVER] Waiting for connections...")
        
        # Start task dispatcher thread
        self.task_dispatcher_thread = threading.Thread(target=self._dispatch_tasks, daemon=True)
        self.task_dispatcher_thread.start()
        
        try:
            while self.running:
                try:
                    client_socket, addr = self.server_socket.accept()
                    print(f"[SERVER] New connection from {addr}")
                    
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, addr),
                        daemon=True
                    )
                    client_thread.start()
                except Exception as e:
                    if self.running:
                        print(f"[ERROR] Accept error: {e}")
        except KeyboardInterrupt:
            print("\n[SERVER] Shutting down...")
            self.stop()
    
    def _handle_client(self, client_socket: socket.socket, addr: Tuple[str, int]):
        """Handle a client connection (worker or task sender)"""
        worker_id = None
        sender_id = None
        
        try:
            # Receive first message to identify client type
            data = client_socket.recv(4096)
            if not data:
                return
            
            msg = Message.from_json(data.decode('utf-8'))
            
            if msg.msg_type == MessageType.WORKER_REGISTER:
                # Handle worker registration
                worker_id = f"worker_{uuid.uuid4().hex[:8]}"
                self.worker_tracker.register_worker(worker_id, client_socket, addr)
                
                # Send acknowledgment
                ack = Message(MessageType.SERVER_ACK, {"worker_id": worker_id})
                client_socket.sendall(ack.to_json().encode('utf-8'))
                
                # Keep worker connected and listening for results
                self._handle_worker(worker_id, client_socket)
            
            elif msg.msg_type == MessageType.SUBMIT_TASK:
                # Handle task submission
                sender_id = f"sender_{uuid.uuid4().hex[:8]}"
                task_type = TaskType(msg.data["task_type"])
                params = msg.data.get("params", {})
                
                task_id = self.task_queue.add_task(task_type, params)
                
                # Send task_id back
                response = Message(MessageType.SERVER_ACK, {"task_id": task_id})
                client_socket.sendall(response.to_json().encode('utf-8'))
                
                # Handle result requests
                self._handle_task_sender(client_socket)
            
            else:
                print(f"[ERROR] Unknown message type from {addr}")
                client_socket.close()
        
        except Exception as e:
            print(f"[ERROR] Client handler error ({addr}): {e}")
        
        finally:
            if worker_id:
                self.worker_tracker.remove_worker(worker_id)
            client_socket.close()
    
    def _handle_worker(self, worker_id: str, worker_socket: socket.socket):
        """Handle worker connection"""
        while self.running:
            try:
                data = worker_socket.recv(4096)
                if not data:
                    break
                
                msg = Message.from_json(data.decode('utf-8'))
                
                if msg.msg_type == MessageType.WORKER_RESULT:
                    # Receive task result from worker
                    result = msg.data["result"]
                    self.task_queue.mark_complete(result["task_id"], result)
                    self.worker_tracker.mark_ready(worker_id)
                    print(f"[WORKER] {worker_id} completed task: {result['task_id']}")
                
                elif msg.msg_type == MessageType.WORKER_READY:
                    # Worker is ready for more tasks
                    self.worker_tracker.mark_ready(worker_id)
            
            except Exception as e:
                print(f"[ERROR] Worker handler error ({worker_id}): {e}")
                break
    
    def _handle_task_sender(self, sender_socket: socket.socket):
        """Handle task sender requests"""
        while self.running:
            try:
                data = sender_socket.recv(4096)
                if not data:
                    break
                
                msg = Message.from_json(data.decode('utf-8'))
                
                if msg.msg_type == MessageType.GET_RESULT:
                    # Client requesting task result
                    task_id = msg.data.get("task_id")
                    result = self.task_queue.get_result(task_id)
                    
                    if result:
                        response = Message(MessageType.RESULT_RESPONSE, result)
                    else:
                        response = Message(MessageType.RESULT_RESPONSE, {
                            "task_id": task_id,
                            "result": None,
                            "status": "pending"
                        })
                    
                    sender_socket.sendall(response.to_json().encode('utf-8'))
                
                elif msg.msg_type == MessageType.SUBMIT_TASK:
                    # Submit another task
                    task_type = TaskType(msg.data["task_type"])
                    params = msg.data.get("params", {})
                    task_id = self.task_queue.add_task(task_type, params)
                    
                    response = Message(MessageType.SERVER_ACK, {"task_id": task_id})
                    sender_socket.sendall(response.to_json().encode('utf-8'))
            
            except Exception as e:
                print(f"[ERROR] Task sender handler error: {e}")
                break
    
    def _dispatch_tasks(self):
        """Continuously dispatch tasks to available workers"""
        while self.running:
            try:
                # Get a task from queue
                task = self.task_queue.get_task(timeout=2)
                
                if task:
                    # Get a ready worker
                    worker_result = self.worker_tracker.get_ready_worker()
                    
                    if worker_result:
                        worker_id, worker_socket = worker_result
                        
                        # Send task to worker
                        msg = Message(MessageType.TASK_ASSIGN, {"task": task})
                        worker_socket.sendall(msg.to_json().encode('utf-8'))
                        print(f"[DISPATCH] Assigned {task['task_id']} to {worker_id}")
                    else:
                        # Put task back in queue if no workers available
                        self.task_queue.queue.put(task)
                        time.sleep(0.5)
            
            except Exception as e:
                print(f"[ERROR] Dispatch error: {e}")
                time.sleep(1)
    
    def stop(self):
        """Stop the server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("[SERVER] Stopped")
    
    def get_status(self) -> dict:
        """Get server status"""
        return {
            "server": f"{self.host}:{self.port}",
            "running": self.running,
            "queue_size": self.task_queue.queue_size(),
            "workers": self.worker_tracker.get_status()
        }


if __name__ == "__main__":
    server = TaskManagerServer(host="0.0.0.0", port=5000)
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
