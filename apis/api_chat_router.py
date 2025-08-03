import sys
import os, json
from turtle import up
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi import APIRouter, Form, HTTPException, File, UploadFile
from agent.chat_bot import ChatBotNotCompliance, ChatBotGeneral, ChatFilterGeneral, ChatFilterNonCompliance
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
    handler.stream.reconfigure(encoding='utf-8') 
    logger.addHandler(handler)

router = APIRouter(prefix="/api/v1", tags=["chat"])

REFUSAL_MESSAGE = (
    "عذرًا، يمكنني فقط الإجابة عن الأسئلة المتعلقة بمحتوى التدقيق المرفق.\n"
    "Sorry, I can only answer questions related to the provided audit content."
)

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
        # 1️⃣ Get response from the bot
        chatbot = ChatBotNotCompliance(
            description_control=description_control,
            requirements_control=requirements_control,
            report=report
        )
        response = chatbot.chat(user_message)

        # 2️⃣ Filter response using ChatFilterNonCompliance
        is_allowed = ChatFilterNonCompliance(
            user_input=user_message,
            model_response=response,
            description_control=description_control,
            requirements_control=requirements_control,
            report=report
        ).chat()

        if is_allowed:
            logger.info("Chatbot response is within allowed data.")
            return {"response": response}
        else:
            logger.info("Chatbot response is unrelated. Returning REFUSAL_MESSAGE.")
            return {"response": REFUSAL_MESSAGE}

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
        # 1️⃣ Read and parse the uploaded JSON
        contents = await file.read()
        json_data = json.loads(contents)
        adapter = TypeAdapter(List[GeneralChat])
        parsed_chats = adapter.validate_python(json_data["results"])

        if not parsed_chats:
            raise HTTPException(status_code=400, detail="No parsed_response data found.")

        # 2️⃣ Get the chatbot response
        chatbot = ChatBotGeneral(results=parsed_chats)
        response = chatbot.chat(user_message)
        
        # 3️⃣ Pass the response through the ChatFilter
        is_allowed = ChatFilterGeneral(parsed_chats, user_message, response).chat()

        if is_allowed:
            logger.info("Chatbot response is within allowed data.")
            return {"response": response}
        else:
            logger.info("Chatbot response is unrelated. Returning REFUSAL_MESSAGE.")
            return {"response": REFUSAL_MESSAGE}

    except Exception as e:
        logger.exception("Chatbot failed to respond.")
        raise HTTPException(status_code=500, detail=str(e))


