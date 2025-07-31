import requests
import json, os, sys
from typing import List
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pathlib import Path
from langchain.chat_models.base import BaseChatModel
from langchain.schema import HumanMessage, AIMessage
from langchain.schema.messages import BaseMessage
from langchain.schema.output import ChatResult, ChatGeneration


class MyCustomMultiImageChatLLM(BaseChatModel):
    endpoint_url: str

    @property
    def _llm_type(self) -> str:
        return "my_custom_multi_image_chat_model"

    def _generate(self, messages: List[BaseMessage], **kwargs) -> ChatResult:
        # Expect only one prompt message
        if not messages:
            raise ValueError("No messages provided.")
        prompt = messages[-1].content  # Use the last message as the prompt

        # Extract max_new_tokens
        max_new_tokens = kwargs.get("max_new_tokens", 4000)

        # Get image paths
        image_paths = kwargs.get("image_paths")
        if not image_paths or not isinstance(image_paths, (list, tuple)):
            raise ValueError("You must provide 'image_paths' keyword argument as a list of image file paths")

        # Prepare multipart form-data payload
        files = [
            ("prompt", (None, prompt)),
            ("max_new_tokens", (None, str(max_new_tokens))),
        ]

        for image_path in image_paths:
            path_obj = Path(image_path)
            files.append(
                ("images", (path_obj.name, open(path_obj, "rb"), "image/jpeg"))
            )

        # Send request
        response = requests.post(self.endpoint_url, files=files)
        response.raise_for_status()

        data = response.json()
        generated_text = data.get("response", "")

        generation = ChatGeneration(message=AIMessage(content=generated_text))
        return ChatResult(generations=[generation])

'''
class MyCustomMultiImageChatLLM(BaseChatModel):
    endpoint_url: str

    @property
    def _llm_type(self) -> str:
        return "my_custom_multi_image_chat_model"

    def _generate(self, messages: list[BaseMessage], **kwargs) -> ChatResult:
        messages_payload = json.dumps([m.content for m in messages])

        image_paths = kwargs.get("image_paths")
        if not image_paths or not isinstance(image_paths, (list, tuple)):
            raise ValueError("You must provide 'image_paths' keyword argument as a list of image file paths")

        # Prepare files dict with messages and max_new_tokens as before
        files = [
    ("messages", (None, messages_payload)),
    ("max_new_tokens", (None, f"{max_new_tokens}")),
    ]
        for image_path in image_paths:
            path_obj = Path(image_path)
            files.append(("files", (path_obj.name, open(path_obj, "rb"), "image/png")))


        response = requests.post(self.endpoint_url, files=files)
        response.raise_for_status()
        data = response.json()
        #print("API response:", data)  # Debug

        generated_text = data.get("response", "")

        generation = ChatGeneration(message=AIMessage(content=generated_text))
        return ChatResult(generations=[generation])
'''

