import requests
import json, sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

max_new_tokens = 500
url = "https://qwen-vlm-a100.delightfulsky-f308bdb7.westus3.azurecontainerapps.io/qwen/generate_pdf"

class ChatBotMain:
    def __init__(self, control_content, report):#system_message
        self.memory = []
        # Combine system message, report, and control number
        self.system_message = (
            "You are chat assistant (Arabic and English), help user on his questions about the report and the controls.\n"
            f"Control Instructions are: {control_content}\n"
            f"The Report  that was created is: {report}\n"
            "Take these instructions, understand them, see the Report result understand it and start answering the client's questions regarding this report. .\n"
            #"Keep your answers short if the user doesn't ask for details.\n"
            #f"System Message: {system_message}\n"

        )
        self.init_conversation()
        #print("DEBUG: System message initialized.", self.system_message)

    def init_conversation(self):
        # Start with the combined system message
        self.memory.append({"role": "system", "content": self.system_message})
        print("DEBUG: Combined system message added to memory.")

    def chat(self, user_message):
        # Add user message to memory
        self.memory.append({"role": "user", "content": user_message})
        # Trim memory to keep system + last 20 user/assistant messages
        if len(self.memory) > 1:
            self.memory = [self.memory[0]] + self.memory[-20:]
        # Debug print for memory length
        #print("DEBUG: Memory length after user message:", len(self.memory))
        # Prepare messages for the model
        messages = self.memory
        json_payload = json.dumps([m["content"] for m in messages])
        try:
            response = requests.post(
                url,
                data={
                    'messages': json_payload,
                    'max_new_tokens': str(max_new_tokens),
                }
            )
            bot_reply = response.text if response.status_code == 200 else f"Error: {response.status_code}"
        except Exception as e:
            bot_reply = f"Exception: {str(e)}"
        # Add bot reply to memory
        self.memory.append({"role": "assistant", "content": bot_reply})
        # Trim memory again after assistant reply
        if len(self.memory) > 1:
            self.memory = [self.memory[0]] + self.memory[-20:]
        # Debug print for memory length
        return bot_reply
    

class ChatBotGeneral:
    def __init__(self, control_content, report ):#system_message
        self.memory = []
        # Combine system message, report, and control number
        self.system_message = (
            "You are chat assistant, help user on his questions about the report and the controls.\n"
            f"Control Instructions are: {control_content}\n"
            f"The Report  that was created is: {report}\n"
            "Take these instructions, understand them, see the Report result understand it and start answering the client's questions regarding this report. .\n"
            #"Keep your answers short if the user doesn't ask for details.\n"
            #f"System Message: {system_message}\n"

        )
        self.init_conversation()
        #print("DEBUG: System message initialized.", self.system_message)

    def init_conversation(self):
        # Start with the combined system message
        self.memory.append({"role": "system", "content": self.system_message})
        print("DEBUG: Combined system message added to memory.")

    def chat(self, user_message):
        # Add user message to memory
        self.memory.append({"role": "user", "content": user_message})
        # Trim memory to keep system + last 20 user/assistant messages
        if len(self.memory) > 1:
            self.memory = [self.memory[0]] + self.memory[-20:]
        # Debug print for memory length
        #print("DEBUG: Memory length after user message:", len(self.memory))
        # Prepare messages for the model
        messages = self.memory
        json_payload = json.dumps([m["content"] for m in messages])
        try:
            response = requests.post(
                url,
                data={
                    'messages': json_payload,
                    'max_new_tokens': str(max_new_tokens),
                }
            )
            bot_reply = response.text if response.status_code == 200 else f"Error: {response.status_code}"
        except Exception as e:
            bot_reply = f"Exception: {str(e)}"
        # Add bot reply to memory
        self.memory.append({"role": "assistant", "content": bot_reply})
        # Trim memory again after assistant reply
        if len(self.memory) > 1:
            self.memory = [self.memory[0]] + self.memory[-20:]
        # Debug print for memory length
        return bot_reply