import requests
import json
import re

def generate_text(prompt, max_tokens=5000, thinking=False):
    """
    Sends a request to the open-source LLM endpoint with the given prompt.
    """
    url = "https://qwen-3-llm.delightfulsky-f308bdb7.westus3.azurecontainerapps.io/api/chat_llm"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "prompt": prompt,
        "max_tokens": max_tokens,
        "thinking": str(thinking).lower()
    }
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error making request to LLM: {e}")
        return None


def generate_clause_instruction(clause: str) -> str:
    prompt_english = """
You are a legal compliance expert. Your task is to transform a given legal or regulatory clause into a clear set of measurable instructions that can be used by a language model to audit documents for compliance.

Follow these steps:
1. Identify the responsible party (Who is obligated or restricted?)
2. Identify the required or prohibited action.
3. Extract any conditions or exceptions (When or under what circumstances is it allowed or not allowed?)
4. Translate the clause into a descriptive paragraph in description_control.
5. Translate the clause into step-by-step executable audit instructions.

Make sure the instructions are:
- Specific
- Actionable
- Measurable within the context of document analysis

### Language Policy:
- Respond in the **same language** as the clause.
  - If the clause is in **Arabic**, your entire response (including field labels and steps) must be in **Arabic**.
  - If the clause is in **English**, respond entirely in **English**.

### Expected Output Format:
Respond ONLY in the following JSON format:
```json
{
  "description_control": "",
  "requirements_control": {
    "Audit_Instructions": [
      "Step 1...",
      "Step 2...",
      "... etc"
    ]
  }
}

### Arabic Example Output:
{
  "description_control":"يلتزم مقدم الخدمة بتطوير وتنفيذ برنامج للمحافظة على خصوصية البيانات الشخصية للمستخدمين على ان يشمل ذلك تطوير وتوثيق وتنفيذ السياسات والاجراءات المتعلقة بالمحافظة على خصوصية البيانات الشخصية للمستخدمين ومتابعة الالتزام بها وان يتم اعتماد البرنامج من قبل المسؤول الاول لدى مقدم الخدمة او من يفوضه كما يلتزم مقدم الخدمة برفع خطة البرنامج للهيئة قبل اعتماده والرفع بشكل دوري للهيئة عن نشاطات البرنامج بعد اعتماده وللهيئة الحق بطلب اجراء اي تعديلات تراها مناسبة",
  "requirements_control": {
    "Audit_Instructions": [
      "Step 1: تحقق من أن المستخدم هو الجهة المُسجّلة في المستند.",
      "Step 2: تأكد من أن خدمات الاتصال أو تقنية المعلومات المُستخدمة تُنتمي إلى شخص طبيعي أو اعتباري.",
      "Step 3: تحقق من أن لا توجد إشارة إلى استخدام خدمات تابعة لجهة غير شخصية (مثل جهات حكومية أو جماعية) في المستند.",
      "Step 4: تأكد من أن التصريح أو الإشارة إلى استخدام هذه الخدمات يُذكر بشكل واضح في المستند."
    ]
  }
}

### English Example Output:
{
  "description_control": "The service provider is committed to developing and implementing a program to maintain the privacy of users’ personal data, provided that this includes developing, documenting, and implementing policies and procedures related to maintaining the privacy of users’ personal data and monitoring compliance with them. The program must be approved by the service provider’s senior official or his delegate. The service provider is also committed to submitting the program plan to the Authority before its approval and submitting periodically to the Authority about the program’s activities after its approval. The Authority has the right to request any amendments it deems appropriate.",
  "requirements_control": {
    "Audit_Instructions": [
      "Step 1: Identify all services related to communication or information technology mentioned in the document.",
      "Step 2: For each identified service, determine the provider's legal status (natural person or legal entity).",
      "Step 3: Check if all providers of communication or information technology services are either natural persons or legal entities.",
      "Step 4: Flag any service provided by a non-natural and non-legal entity as non-compliant."
    ]
  }
}

"""
    
    full_prompt_english = prompt_english + f"### Clause to Transform:{clause}"

    response = generate_text(full_prompt_english)
    
    raw_response = response['response']
    cleaned_json_str = re.sub(r"```json|```", "", raw_response).strip()
    parsed_data = json.loads(cleaned_json_str)
    result_final = json.dumps(parsed_data, indent=2, ensure_ascii=False)
    return result_final


def build_clause_audit_instruction(clause_instruction: str) -> str:
    return f"""
You are a legal and regulatory compliance expert.

Your task is to review the provided image (e.g., a screenshot, scanned policy, or official document) and determine whether it demonstrates compliance with the following clause requirement.

The clause is defined using structured, measurable elements, and includes the responsible party, required action, applicable conditions, and a detailed list of audit instructions.

---
### 📜 Clause Instruction:
{clause_instruction.strip()}
---

### 🔍 Your Evaluation Task:

You must analyze the image and confirm whether it fulfills the clause requirements as follows:

1. **Responsible Party**  
   Verify that the party mentioned in the image matches the responsible entity stated in the clause.

2. **Required Action**  
   Ensure that the expected action (e.g., prohibition, obligation, or condition) is clearly addressed or implemented in the evidence.

3. **Condition (if applicable)**  
   If any conditions are specified, check that they are satisfied explicitly within the content of the image.

4. **Audit Instructions**  
   Follow the list of audit steps included in the clause. These steps define exactly what to look for to determine compliance.

---

### ✅ Final Compliance Decision:

Please provide your conclusion using one of the following decisions:

- **COMPLIANT**: The image clearly demonstrates full adherence to the clause requirements and satisfies all audit instructions.
- **NON-COMPLIANT**: One or more clause elements are not satisfied, unclear, or missing in the image.
- **INDECISIVE**: The image lacks enough detail to assess compliance with confidence.

If NON-COMPLIANT or INDECISIVE, explain briefly which parts are missing or unsupported and what evidence would be needed to confirm compliance.
""".strip()


def process_parsed_response(data: list) -> dict:
    """
    Processes each clause description in the parsed_response list
    to generate and attach clause instructions and audit instructions.
    """
    processed_items = []

    # for item in data.get("parsed_response", []):
    for item in data:
        description = item.get("description", "").strip()

        if not description:
            print(f"Skipping item due to missing description: {item.get('title', 'No Title')}")
            continue

        try:
            # Generate clause instruction (JSON string)
            clause_instruction_json_str = generate_clause_instruction(description)

            # Parse it to dict
            clause_instruction_obj = json.loads(clause_instruction_json_str)

            # Generate audit instruction
            clause_audit_text = build_clause_audit_instruction(clause_instruction_json_str)

            # Add results to the item
            item["clause_instruction"] = clause_instruction_obj
            item["clause_audit_instruction"] = clause_audit_text

        except Exception as e:
            print(f"Error processing '{item.get('title', 'No Title')}': {e}")
            continue

        processed_items.append(item)

    return {"parsed_response": processed_items}

# test generate_text function
if __name__ == "__main__":
    #test_clause =  "يُحظر على مقدم الخدمة مشاركة البيانات دون موافقة المستخدم"
    #result = generate_clause_instruction(test_clause)
    #print(result)
    #print("\n\nGenerated Clause Instruction:\n")
    #print(build_clause_audit_instruction(result))
    # Example JSON data to process
    dictt = {
  "parsed_response": [
    {
      "title": "البند 2",
      "description": "يُحظر على مقدم الخدمة مشاركة البيانات دون موافقة المستخدم.",
      "source": "مثال_raw_response.docx",
      "page": "Page not specified"
    },
    {
      "title": "البند 5",
      "description": "يجب على مقدم الخدمة تقديم خدمات التصالت بين الجهزة والمعدات الثابتة أو المتنقلة أو محدودة التنقل.",
      "source": "مثال_raw_response.docx",
      "page": "Page not specified"
    },
    {
      "title": "البند 6",
      "description": "يجب على المستخ دم استخدام خدمات التصالت أو تقنية المعلومات من شخص طبيعية أو اعتبارية.",
      "source": "مثال_raw_response.docx",
      "page": "Page not specified"
    }
  ]
}

    processed_data = process_parsed_response(dictt)
    print(json.dumps(processed_data, indent=2, ensure_ascii=False))
