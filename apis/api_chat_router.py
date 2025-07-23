import sys
import os, json
from turtle import up
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi import APIRouter, Form, HTTPException, File, UploadFile
from agent.chat_bot import ChatBotNotCompliance, ChatBotGeneral
from utils.schemas import GeneralChat
from dotenv import load_dotenv
import logging
from pydantic import TypeAdapter
from typing import List

# Load environment variables from .env file
load_dotenv()

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ✅ prevent adding multiple handlers
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/non_compliance_chat")
async def non_compliance_chat(
    user_message: str = Form(...),
    description_control: str = Form(...),
    requirements_control: str = Form(...),
    report: str = Form(...)
):
    """
    Endpoint to chat with the bot using a control number and report.
    """
    logger.info(f"Chat initiated! with message: {user_message}")

    try:
        chatbot = ChatBotNotCompliance(description_control=description_control, requirements_control=requirements_control, report=report)
        response = chatbot.chat(user_message)
        logger.info("Chatbot responded successfully.")
        return {"response": response}

    except Exception as e:
        logger.exception("Chatbot failed to respond.")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/general_chat")
async def general_chat(
    user_message: str = Form(...),
    file: UploadFile = File(..., description="JSON file containing parsed_response: List[GeneralChat]")
):
    """
    Endpoint to chat with the bot using parsed_response from uploaded JSON.
    """
    logger.info(f"Chat initiated! with message: {user_message}")

    try:
        contents = await file.read()
        json_data = json.loads(contents)
        adapter = TypeAdapter(List[GeneralChat])
        parsed_chats = adapter.validate_python(json_data["parsed_response"])

        if not parsed_chats:
            raise HTTPException(status_code=400, detail="No parsed_response data found.")

        chatbot = ChatBotGeneral(clauses=parsed_chats)
        response = chatbot.chat(user_message)
        logger.info("Chatbot responded successfully.")
        return {"response": response}

    except Exception as e:
        logger.exception("Chatbot failed to respond.")
        raise HTTPException(status_code=500, detail=str(e))

