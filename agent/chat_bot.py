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
            "You are an intelligent assistant that can communicate in both Arabic and English. "
            "Your sole task is to help the user understand the audit report results and their compliance "
            "with the mentioned controls and requirements only.\n\n"
            
            "أنت مساعد ذكي تتحدث العربية والإنجليزية، ومهمتك الوحيدة هي مساعدة المستخدم في فهم "
            "نتائج تقرير التدقيق ومدى التزامه بالضوابط والمتطلبات المذكورة فقط.\n\n"

            "🚫 You are strictly forbidden from answering any question that is not explicitly related to the following content:\n"
            "🚫 يُمنع عليك الإجابة عن أي سؤال لا يتعلّق صراحةً بالمحتوى التالي:\n\n"

            f"📌 **Requirements Details / تفاصيل المتطلبات:**\n{requirements_control}\n\n"
            f"📌 **Application Controls & Instructions / الضوابط والتعليمات الخاصة بالتطبيق:**\n{description_control}\n\n"
            f"📌 **Audit Report Summary / ملخص تقرير التدقيق:**\n{report}\n\n"

            "🔒 If the user asks an unrelated question, always respond with the fixed message:\n"
            "\"عذرًا، يمكنني فقط الإجابة عن الأسئلة المتعلقة بتفاصيل التدقيق والضوابط المذكورة أعلاه.\"\n"
            "\"Sorry, I can only answer questions related to the audit details and mentioned controls.\"\n\n"

            "💡 When responding:\n"
            "- Auto-detect the user’s language and respond in Arabic or English accordingly.\n"
            "- عند الرد على استفسارات المستخدم، استخدم أسلوبًا تحليليًا واضحًا ومرتبًا دون ذكر العناوين أو الأقسام أعلاه.\n"
            "- Focus only on providing a direct, clear answer based strictly on the given content.\n"
            "- ركّز فقط على تقديم إجابة مباشرة مستندة إلى المحتوى دون استخدام مصطلحات تقنية.\n"
            "- If a non-compliance point appears, explain it based on the difference between the required controls and the actual findings in the report.\n"
            "- إذا ظهرت نقطة عدم امتثال، فسّر السبب بناءً على التباين بين المطلوب والمذكور فعليًا في التقرير.\n"
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
            "You are an intelligent assistant specialized in explaining regulatory rules and requirements.\n"
            "You will be given a set of regulatory items. Your task is to discuss these items in detail with the user "
            "and answer any questions related to them only.\n"
            "🚫 You are not allowed to answer any questions unrelated to these items.\n"
            "If the user asks a question outside this context, respond with: "
            "\"عذرًا، يمكنني فقط الإجابة عن الأسئلة المتعلقة بالبُنود التنظيمية المذكورة.\" / "
            "\"Sorry, I can only answer questions related to the mentioned regulatory items.\"\n\n"
            "You can understand and respond in both Arabic and English depending on the user's language.\n"
        )


        # دمج كل البنود داخل system prompt
        for clause in clauses:
            title = clause.title
            description_control = clause.clause_instruction.description_control
            audit_steps = clause.clause_instruction.requirements_control.Audit_Instructions
            audit_text = "\n".join([f"• {step}" for step in audit_steps])

        self.system_message += (
            f"📌 **عنوان البند / Item Title:** {title}\n"
            f"📋 **وصف البند / Control Description:**\n{description_control}\n"
            f"✅ **متطلبات البند / Related Requirements:**\n{audit_text}\n\n"
        )

        self.system_message += (
            "📣 تعليمات الرد على المستخدم / Response Guidelines:\n"
            "- تجنّب استخدام العبارات الرسمية مثل (عنوان البند، وصف البند ,متطلبات البند) في الإجابات.\n"
            "- Avoid using formal labels like (Item Title, Control Description, Related Requirements) in your answers.\n"
            "- قدّم شرحًا مبسطًا وواضحًا لكل بند.\n"
            "- Provide a simple and clear explanation for each item.\n"
            "- فسّر كيفية تحقيق التوافق مع كل بند، والمخاطر في حال عدم الالتزام.\n"
            "- Explain how to achieve compliance with each item and the risks of non-compliance.\n"
            "- استخدم أمثلة أو مقترحات للتحسين إن وُجدت.\n"
            "- Use examples or improvement suggestions if available.\n"
            "- لا تخمّن أو تضف أي معلومة من خارج البنود المذكورة.\n"
            "- Do not guess or add any information outside the mentioned items.\n\n"
            "💡 اختر لغة الرد (عربية أو إنجليزية) بناءً على لغة المستخدم تلقائيًا.\n"
            "💡 Automatically respond in the user's language (Arabic or English).\n"
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
