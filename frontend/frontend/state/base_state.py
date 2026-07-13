import os
import reflex as rx
from dotenv import load_dotenv

load_dotenv()

class AppState(rx.State):
    """The foundational state class for the entire app."""
    
    # Read the environment toggle automatically
    api_url: str = os.getenv("API_BASE_URL", "http://localhost:10000")
    current_tenant: str = os.getenv("DEFAULT_TENANT_ID", "default-tenant")

    @rx.var
    def chat_endpoint(self) -> str:
        return f"{self.api_url}/api/v1/chat/{self.current_tenant}"

    @rx.var
    def status_endpoint(self) -> str:
        return f"{self.api_url}/api/v1/chat/status"