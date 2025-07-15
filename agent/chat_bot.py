import requests
import json, sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag.knowledge_retriever import retrieve_relevant_knowledge

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
    

class ChatRAG:
    def __init__(self):
        self.memory = []
        self.base_system_message = (
            "You are a chat assistant with a Retrieval-Augmented Generation (RAG) System that supports both Arabic and English.\n"
            "Your goal is to help the user extract relevant policy or contract terms based on the information they provide.\n"
            "Respond clearly and concisely based on the user's context.\n"
        )
        self.init_conversation()

    def init_conversation(self):
        self.memory.append({"role": "system", "content": self.base_system_message})
        print("✅ System message initialized.")

    def chat(self, is_licensed, license_type, service_type, regulations, user_question, max_new_tokens=1000):
        # 🧠 Step 1: Construct full context from user answers
        context_input = f"""
        استعلام المستخدم: {user_question}
        هل الشركة مرخصة؟ → {is_licensed}
        نوع الترخيص → {license_type}
        نوع الخدمة → {service_type}
        التنظيمات → {regulations}
        """

        print("📥 Constructed context:")
        print(context_input)

        # 🔍 Step 2: Retrieve relevant knowledge using FAISS
        try:
            rag_context = retrieve_relevant_knowledge(
                user_question=user_question,
                is_licensed=is_licensed,
                license_type=license_type,
                service_type=service_type,
                regulations=regulations
            )
            print("📄 RAG context retrieved successfully.")
        except Exception as e:
            rag_context = "⚠️ Could not retrieve relevant knowledge due to error: " + str(e)
            print("❌ RAG retrieval error:", e)

        # 🔗 Step 3: Build user message to include context + RAG
        combined_user_message = (
            f"User Context:\n{context_input}\n\n"
            f"Retrieved Terms:\n{rag_context}\n"
        )

        # 🧾 Step 4: Add to memory
        self.memory.append({"role": "user", "content": combined_user_message})
        if len(self.memory) > 1:
            self.memory = [self.memory[0]] + self.memory[-20:]

        # 🔁 Step 5: Send to model endpoint
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

            if response.status_code == 200:
                try:
                    raw = json.loads(response.text).get("response", "")
                except Exception:
                    raw = response.text

                # ✨ Step 6: Parse structured output
                summary = {}
                terms = []
                in_summary = True
                for line in raw.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    if "**النقاط الرئيسية من الوثائق المراجعة:**" in line:
                        in_summary = False
                        continue
                    if in_summary:
                        if ":" in line:
                            key, val = line.split(":", 1)
                            summary[key.strip("١.٢.٣.٤.٥.* ").strip()] = val.strip().strip("* ")
                    else:
                        if line.startswith("-"):
                            line = line.lstrip("-").strip()
                            if line:
                                terms.append(line)

                bot_reply = {
                    "summary": summary,
                    "extracted_terms": terms
                }

                # fallback لو التحليل فشل
                if not summary and not terms:
                    bot_reply = {"raw_response": raw}

            else:
                bot_reply = {
                    "error": f"❌ Error: {response.status_code}",
                    "raw_response": response.text
                }

        except Exception as e:
            bot_reply = {
                "error": f"❌ Exception occurred: {str(e)}"
            }

        # 💾 Save assistant response
        self.memory.append({"role": "assistant", "content": str(bot_reply)})
        if len(self.memory) > 1:
            self.memory = [self.memory[0]] + self.memory[-20:]

        return bot_reply


