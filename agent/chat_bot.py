import requests
import json, sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv


load_dotenv()

max_new_tokens = 500
QWEN3_ENDPOINT_CHAT = os.getenv('QWEN3_ENDPOINT_CHAT')


class ChatBotNotCompliance:
    def __init__(self, description_control, requirements_control, report):
        self.history = []
        self.system_message = (
            "أنت مساعد ذكي تتحدث العربية والإنجليزية، ومهمتك الوحيدة هي مساعدة المستخدم في فهم نتائج تقرير التدقيق ومدى التزامه بالضوابط والمتطلبات المذكورة فقط.\n"
            "يُمنع عليك الإجابة عن أي سؤال لا يتعلّق صراحةً بالمحتوى التالي:\n\n"
            "📌 **تفاصيل المتطلبات:**\n"
            f"{requirements_control}\n\n"
            "📌 **الضوابط والتعليمات الخاصة بالتطبيق:**\n"
            f"{description_control}\n\n"
            "📌 **ملخص تقرير التدقيق:**\n"
            f"{report}\n\n"
            "🔒 **تنبيه هام:** إذا طرح المستخدم سؤالًا لا يتعلّق بهذه المعلومات، يجب أن ترد برسالة ثابتة تقول: \"عذرًا، يمكنني فقط الإجابة عن الأسئلة المتعلقة بتفاصيل التدقيق والضوابط المذكورة أعلاه.\"\n\n"
            "عند الرد على استفسارات المستخدم، استخدم أسلوبًا تحليليًا واضحًا ومرتبًا دون ذكر العناوين أو الأقسام أعلاه.\n"
            "ركّز فقط على تقديم إجابة مباشرة مستندة إلى المحتوى دون استخدام مصطلحات تقنية.\n"
            "إذا ظهرت نقطة عدم امتثال، فسّر السبب بناءً على التباين بين المطلوب والمذكور فعليًا في التقرير.\n"
        )


        print("DEBUG: System message initialized.")
    
    def build_prompt(self, user_message):
        prompt_parts = [self.system_message]
        for item in self.history:
            prompt_parts.append(f"User: {item['user']}")
            prompt_parts.append(f"Assistant: {item['assistant']}")
        prompt_parts.append(f"User: {user_message}")
        return "\n".join(prompt_parts)

    def chat(self, user_message, max_tokens=1024, thinking=False):
        prompt = self.build_prompt(user_message)
        data = {
            'prompt': prompt,
            'max_tokens': str(max_tokens),
            'thinking': str(thinking).lower()
        }
        try:
            response = requests.post(
                QWEN3_ENDPOINT_CHAT,
                headers={
                    'accept': 'application/json',
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                data=data
            )
            if response.status_code == 200:
                result = response.json()
                bot_reply = result.get("response", "⚠️ No response field in JSON.")
            else:
                bot_reply = f"❌ Error {response.status_code}: {response.text}"
        except Exception as e:
            bot_reply = f"Exception: {str(e)}"

        # Save to history
        self.history.append({'user': user_message, 'assistant': bot_reply})
        # Keep only last 10 turns
        if len(self.history) > 10:
            self.history = self.history[-10:]

        return bot_reply


class ChatBotGeneral:
    def __init__(self, clauses: list):
        self.history = []
        self.system_message = (
            "أنت مساعد ذكي متخصص في شرح الضوابط والمتطلبات التنظيمية.\n"
            "سيتم إعطاؤك مجموعة من البنود التنظيمية، ومهمتك هي مناقشة هذه البنود بالتفصيل مع المستخدم والإجابة عن أي استفسارات تتعلق بها فقط.\n"
            "🚫 لا يُسمح لك بالإجابة على أي سؤال لا يتعلّق بهذه البنود.\n"
            "إذا طرح المستخدم سؤالاً خارج هذا السياق، يجب أن ترد برسالة تقول: \"عذرًا، يمكنني فقط الإجابة عن الأسئلة المتعلقة بالبُنود التنظيمية المذكورة.\"\n\n"
        )

        # دمج كل البنود داخل system prompt
        for clause in clauses:
            title = clause.title
            description_control = clause.clause_instruction.description_control
            audit_steps = clause.clause_instruction.requirements_control.Audit_Instructions
            audit_text = "\n".join([f"• {step}" for step in audit_steps])

            self.system_message += (
                f"📌 **عنوان البند:** {title}\n"
                f"📋 **وصف الضابط:**\n{description_control}\n"
                f"✅ **المتطلبات المرتبطة:**\n{audit_text}\n\n"
            )

        self.system_message += (
            "📣 عند الرد على المستخدم:\n"
            "- تجنّب استخدام عبارات مثل (عنوان البند، وصف الضابط، المتطلبات المرتبطة) في الإجابات.\n"
            "- قدّم شرحًا مبسطًا وواضحًا لكل بند.\n"
            "- فسّر كيف يمكن تحقيق التوافق مع كل بند، وما هي المخاطر في حال عدم الالتزام به.\n"
            "- استخدم أمثلة أو مقترحات للتحسين إن وُجدت.\n"
            "- لا تخمّن أو تضيف أي معلومة من خارج البنود المذكورة.\n"
        )


        print("DEBUG: System message initialized.")

    def build_prompt(self, user_message):
        prompt_parts = [self.system_message]
        for item in self.history:
            prompt_parts.append(f"User: {item['user']}")
            prompt_parts.append(f"Assistant: {item['assistant']}")
        prompt_parts.append(f"User: {user_message}")
        return "\n".join(prompt_parts)

    def chat(self, user_message, max_tokens=1024, thinking=False):
        prompt = self.build_prompt(user_message)
        data = {
            'prompt': prompt,
            'max_tokens': str(max_tokens),
            'thinking': str(thinking).lower()
        }
        try:
            response = requests.post(
                QWEN3_ENDPOINT_CHAT,
                headers={
                    'accept': 'application/json',
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                data=data
            )
            if response.status_code == 200:
                result = response.json()
                bot_reply = result.get("response", "⚠️ No response field in JSON.")
            else:
                bot_reply = f"❌ Error {response.status_code}: {response.text}"
        except Exception as e:
            bot_reply = f"Exception: {str(e)}"

        self.history.append({'user': user_message, 'assistant': bot_reply})
        if len(self.history) > 10:
            self.history = self.history[-10:]

        return bot_reply
