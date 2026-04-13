"""
Shared protocol and message structures for the distributed task system.
Defines the communication format between server, workers, and task senders.
"""

import json
from enum import Enum
from typing import Any, Dict


class MessageType(Enum):
    """Message types used in the system"""
    # Worker messages
    WORKER_REGISTER = "worker_register"          # Worker registers with server
    WORKER_READY = "worker_ready"                # Worker is ready for tasks
    WORKER_RESULT = "worker_result"              # Worker sends task result
    
    # Server messages
    TASK_ASSIGN = "task_assign"                  # Server assigns task to worker
    TASK_COMPLETE = "task_complete"              # Server confirms task completion
    SERVER_ACK = "server_ack"                    # General server acknowledgment
    
    # Task Sender messages
    SUBMIT_TASK = "submit_task"                  # Client submits a new task
    GET_RESULT = "get_result"                    # Client requests task result
    RESULT_RESPONSE = "result_response"          # Server returns result to client
    ERROR = "error"                              # Error message


class TaskType(Enum):
    """Available task types"""
    SQUARE = "square"                            # Compute square of a number
    REVERSE_STRING = "reverse_string"            # Reverse a string
    UPPERCASE = "uppercase"                      # Convert string to uppercase
    FIBONACCI = "fibonacci"                      # Compute fibonacci number


class Message:
    """Encapsulates a message with type and data"""
    
    def __init__(self, msg_type: MessageType, data: Dict[str, Any] = None):
        self.msg_type = msg_type
        self.data = data or {}
    
    def to_json(self) -> str:
        """Convert message to JSON string"""
        return json.dumps({
            "type": self.msg_type.value,
            "data": self.data
        })
    
    @staticmethod
    def from_json(json_str: str) -> 'Message':
        """Create message from JSON string"""
        try:
            obj = json.loads(json_str)
            msg_type = MessageType(obj["type"])
            data = obj.get("data", {})
            return Message(msg_type, data)
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Invalid message format: {e}")


def create_task(task_id: str, task_type: TaskType, params: Dict[str, Any]) -> Dict[str, Any]:
    """Create a task dictionary"""
    return {
        "task_id": task_id,
        "task_type": task_type.value,
        "params": params
    }


def create_result(task_id: str, result: Any, error: str = None) -> Dict[str, Any]:
    """Create a result dictionary"""
    return {
        "task_id": task_id,
        "result": result,
        "error": error,
        "success": error is None
    }
