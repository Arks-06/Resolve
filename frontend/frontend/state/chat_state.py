import asyncio
import httpx
import uuid
import reflex as rx
from .base_state import AppState

class ChatState(AppState):
    chat_history: list[dict[str, str]] = []
    current_input: str = ""
    is_processing: bool = False
    current_task_id: str = ""
    is_paused: bool = False

    def set_current_input(self, text: str):
        """Explicit setter to bypass Reflex auto-generation bugs."""
        self.current_input = text

    def handle_key_down(self, key: str):
        """Triggers send_message if the Enter key is pressed."""
        if key == "Enter":
            return ChatState.send_message
        
    async def send_message(self):
        self.is_paused = False 
        
        if not self.current_input.strip():
            return

        user_message = self.current_input
        self.chat_history.append({"role": "user", "content": user_message})
        self.current_input = ""
        self.is_processing = True
        yield
    
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.chat_endpoint,
                    json={"user_query": user_message} 
                )
                
                if response.status_code == 202:
                    data = response.json()
                    self.current_task_id = data["task_id"]
                    yield ChatState.poll_task_status
                else:
                    self.chat_history.append({"role": "system", "content": f"Error: {response.text}"})
                    self.is_processing = False
                    yield
            except Exception as e:
                self.chat_history.append({"role": "system", "content": f"Connection Error: {str(e)}"})
                self.is_processing = False
                yield

    @rx.event(background=True)
    async def poll_task_status(self):
        async with httpx.AsyncClient() as client:
            while True:
                async with self:
                    if not self.is_processing:
                        break
                    try:
                        response = await client.get(f"{self.status_endpoint}/{self.current_task_id}")
                        data = response.json()

                        task_result = data.get("result") or {}
                        inner_status = task_result.get("status")

                        if inner_status == "COMPLETED":
                            self.chat_history.append({
                                "role": "agent", 
                                "content": task_result.get("response", "Workflow Complete.") 
                            })
                            self.is_processing = False
                            self.is_paused = False
                            break
                        
                        elif inner_status == "PAUSED_FOR_HUMAN_AUDIT":
                            if not self.is_paused:
                                self.chat_history.append({
                                    "role": "agent", 
                                    "content": "Let me double-check that information for you. Transferring this to a human specialist..."
                                })
                                self.is_paused = True

                        elif data.get("status") in ["FAILURE", "FAILED"]:
                            self.chat_history.append({"role": "system", "content": "Workflow Failed."})
                            self.is_processing = False
                            self.is_paused = False
                            break
                            
                    except Exception as e:
                        print(f"Polling error: {e}")
                
                await asyncio.sleep(2)

    async def resume_workflow(self):
        """Hits the backend to cross the LangGraph interrupt boundary."""
        self.is_paused = False
        self.is_processing = True
        self.chat_history.append({"role": "system", "content": "🚀 Admin approved. Resuming workflow..."})
        yield

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.api_url}/api/v1/chat/resume/{self.current_task_id}?tenant_id={self.current_tenant}"
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    self.current_task_id = data.get("task_id", self.current_task_id)
                    
                    yield ChatState.poll_task_status
                else:
                    self.chat_history.append({"role": "system", "content": f"Failed to resume: {response.text}"})
                    self.is_processing = False
                    yield
            except Exception as e:
                self.chat_history.append({"role": "system", "content": f"Connection Error: {str(e)}"})
                self.is_processing = False
                yield