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
        '''
        self.system_message = (
            "You are an intelligent assistant that can communicate in both Arabic and English. "
            "Your sole task is to help the user understand the audit report results and their compliance "
            "with the mentioned controls and requirements.\n\n"

            "أنت مساعد ذكي تتحدث العربية والإنجليزية، ومهمتك الوحيدة هي مساعدة المستخدم في فهم "
            "نتائج تقرير التدقيق ومدى التزامه بالضوابط والمتطلبات المذكورة.\n\n"

            "🚫 You are strictly forbidden from answering questions unrelated to the audit content.\n"
            "🚫 يُمنع عليك الإجابة عن أي سؤال لا يتعلّق بمحتوى التدقيق.\n\n"

            "📌 **Audit Content:**\n"
            f"- Requirements / المتطلبات:\n{requirements_control}\n\n"
            f"- Controls & Instructions / الضوابط والتعليمات:\n{description_control}\n\n"
            f"- Audit Report / تقرير التدقيق:\n{report}\n\n"

            "💡 When the user asks a question:\n"
            "- If it is about compliance, even indirectly (like 'why am I non-compliant?'), analyze and answer using the audit content.\n"
            "- إذا كان السؤال يتعلق بالامتثال ولو بشكل غير مباشر (مثل: لماذا أنا غير ممتثل؟) فأجب باستخدام محتوى التدقيق.\n"
            "- If it is clearly unrelated, respond with:\n"
            "\"عذرًا، يمكنني فقط الإجابة عن الأسئلة المتعلقة بتفاصيل التدقيق والضوابط المذكورة أعلاه.\"\n"
            "\"Sorry, I can only answer questions related to the audit details and mentioned controls.\"\n"
        )'''
        self.system_message = (
            "أنت مساعد ذكي تتحدث العربية والإنجليزية، ومهمتك هي مساعدة المستخدم في فهم نتائج تقرير التدقيق ومدى التزامه بالضوابط والمتطلبات.\n"
            "ستُعرض عليك أسئلة تتعلق بتقرير تدقيق معين، ويجب أن تبني إجابتك استنادًا إلى التالي:\n\n"
            "📌 **تفاصيل المتطلبات:**\n"
            f"{requirements_control}\n\n"
            "📌 **الضوابط والتعليمات الخاصة بالتطبيق:**\n"
            f"{description_control}\n\n"
            "📌 **ملخص تقرير التدقيق:**\n"
            f"{report}\n\n"
            "عند الرد على استفسارات المستخدم، استخدم أسلوبًا تحليليًا واضحًا ومرتبًا. لا تذكر أسماء الأقسام أو العناوين أعلاه في ردودك (مثل: 'تفاصيل المتطلبات' أو 'الضوابط والتعليمات' أو غيرها).\n"
            "ركّز فقط على تقديم إجابة مباشرة مدعومة بالأدلة من محتوى التقرير، دون ذكر العناوين أو المصطلحات التقنية.\n"
            "إذا كانت هناك نقطة عدم امتثال، فسّر السبب بناءً على التباين بين المطلوب والمذكور فعليًا في التقرير.\n"
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
        if len(self.history) > 20:
            self.history = self.history[-20:]

        return bot_reply


class ChatBotGeneral:
    def __init__(self, results: list):
        self.history = []
        '''
        self.system_message = (
            "You are an intelligent assistant specialized in explaining regulatory rules and requirements.\n"
            "You will be given a set of regulatory items. Your task is to discuss these items in detail with the user "
            "and answer any questions related to them only.\n"
            "🚫 You are not allowed to answer any questions unrelated to these items.\n"
            "If the user asks a question outside this context, respond with: "
            "\"عذرًا، يمكنني فقط الإجابة عن الأسئلة المتعلقة بالبُنود التنظيمية المذكورة.\" / "
            "\"Sorry, I can only answer questions related to the mentioned regulatory items.\"\n\n"
            "You can understand and respond in both Arabic and English depending on the user's language.\n"
        )'''
        self.system_message = (
            "أنت مساعد ذكي متخصص في شرح الضوابط والمتطلبات التنظيمية.\n"
            "سيتم إعطاؤك مجموعة من البنود التنظيمية، ومهمتك هي مناقشة هذه البنود بالتفصيل مع المستخدم والإجابة عن أي استفسارات تتعلق بها.\n\n"
        )
        titles = []
        descriptions = []
        audits = []
        # دمج كل البنود داخل system prompt
        for result in results:
            titles.append(result.title)
            descriptions.append(result.clause_instruction.description_control)
            audit_steps = result.clause_instruction.requirements_control.Audit_Instructions
            audits.extend(audit_steps)

        title = " | ".join(titles)
        description_control = "\n".join(descriptions)
        audit_text = "\n".join([f"• {step}" for step in audits])

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
        if len(self.history) > 20:
            self.history = self.history[-20:]

        return bot_reply


class ChatFilterGeneral:
    def __init__(self, results: list, user_input: str, model_response: str):
        titles = []
        descriptions = []
        audits = []

        for result in results:
            titles.append(result.title)
            descriptions.append(result.clause_instruction.description_control)
            audit_steps = result.clause_instruction.requirements_control.Audit_Instructions
            audits.extend(audit_steps)

        title_text = " | ".join(titles)
        description_control = "\n".join(descriptions)
        audit_text = "\n".join([f"• {step}" for step in audits])

        self.system_message = f"""
            هل هذا الرد التالي اعتمد فقط على البيانات المرفقة أم على معرفة خارجية؟
            العنوان:
            {title_text}
            البيانات:
            {description_control}
            {audit_text}
            سؤال المستخدم:
            {user_input}
            رد النموذج:
            {model_response}
            أجب بكلمة واحدة فقط: نعم أو لا
            او yes or no based on the language of text
            """

    def chat(self, max_tokens=512, thinking=False):
        data = {
            'prompt': self.system_message,
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
                bot_reply = result.get("response", "").strip().lower()
                if "نعم" in bot_reply or "yes" in bot_reply:
                    return True
                return False
            else:
                print(f"❌ Error {response.status_code}: {response.text}")
                return False
        except Exception as e:
            print(f"Exception: {str(e)}")
            return False


class ChatFilterNonCompliance:
    def __init__(self, user_input: str, model_response: str, 
                 description_control: str, requirements_control: str, report: str):
        
        self.system_message = f"""
هل هذا الرد التالي اعتمد فقط على البيانات المرفقة أم على معرفة خارجية؟

البيانات:
- الضوابط والتعليمات:
{description_control}

- المتطلبات:
{requirements_control}

- تقرير التدقيق:
{report}

سؤال المستخدم:
{user_input}

رد النموذج:
{model_response}

أجب بكلمة واحدة فقط: نعم أو لا
او yes or no based on the language of text
"""

    def chat(self, max_tokens=512, thinking=False) -> bool:
        data = {
            'prompt': self.system_message,
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
                bot_reply = result.get("response", "").strip().lower()
                
                if "نعم" in bot_reply or "yes" in bot_reply:
                    return True
                return False
            else:
                print(f"❌ Error {response.status_code}: {response.text}")
                return False
        except Exception as e:
            print(f"Exception: {str(e)}")
            return False
