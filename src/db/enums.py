from enum import Enum

class AuthProvider(str, Enum):
    email_otp = "email_otp"
    google = "google"
    apple = "apple"

class MessageRole(str, Enum):
    system = "system"
    user = "user"
    assistant = "assistant"
    tool = "tool"