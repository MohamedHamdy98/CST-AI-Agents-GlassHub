import re, os, uuid, sys, fitz, shutil, json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image
import io, requests, oss2, httpx
from fastapi import UploadFile
from docx2pdf import convert
from langchain_community.document_loaders import UnstructuredFileLoader  
from pydantic import ValidationError
from utils.schemas import LLMComplianceResult
from utils.create_instructions import process_parsed_response
from pathlib import Path
import importlib.util
from typing import List
import urllib.parse
from collections import defaultdict
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()

QWEN3_ENDPOINT_CHAT = os.getenv('QWEN3_ENDPOINT_CHAT')


def create_path_directory(path: str) -> str:
    directory = os.path.join(os.getcwd(), path)
    os.makedirs(directory, exist_ok=True)
    return directory

DOCX_DIRECTORY = create_path_directory("./database/glasshub_files")


def load_python_module(file_path):
    # Extract a safe module name based on the file name and a unique ID
    base_name = os.path.basename(file_path)
    module_name = os.path.splitext(base_name)[0]
    unique_module_name = f"{module_name}_{uuid.uuid4().hex}"

    spec = importlib.util.spec_from_file_location(unique_module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[unique_module_name] = module
    spec.loader.exec_module(module)

    return module


def parse_llm_response(response_content, original_report):
    try:
        if isinstance(response_content, str):
            # Remove triple backtick formatting
            response_content = re.sub(r"^```(?:json)?|```$", "", response_content.strip(), flags=re.IGNORECASE).strip()

            # Fix illegal unescaped newlines inside string values
            # This regex replaces line breaks that occur inside quoted strings
            def escape_newlines_inside_strings(text):
                in_string = False
                escaped = False
                result = ''
                for i, c in enumerate(text):
                    if c == '"' and not escaped:
                        in_string = not in_string
                    if c == '\n' and in_string:
                        result += '\\n'
                    else:
                        result += c
                    escaped = (c == '\\') and not escaped
                return result

            cleaned = escape_newlines_inside_strings(response_content)
            print("\nCleaned content:\n", cleaned)

            # Now safely parse
            parsed_dict = json.loads(cleaned)

        else:
            parsed_dict = response_content

        compliance = parsed_dict.get("compliance_status", ""),
        flags = parsed_dict.get("flags", [])
        needs_review = parsed_dict.get("needs_human_review", False)
        brief_report = parsed_dict.get("Brief_report", "")
        print(compliance, flags, needs_review, brief_report)
        return {
            "compliance_status": compliance,
            "flags": flags,
            "needs_human_review": needs_review,
            "Brief_report": brief_report,
            "report": original_report
        }

    except Exception as e:
        print("\nError parsing response:", e)
        return {"Error in parsing response": str(e)}


def parse_llm_response_pydantic(response_content, original_report):
    """
    Parses the LLM response using Pydantic and handles formatting issues (e.g., markdown-style output).
    """
    
    def escape_newlines_inside_strings(text):
        in_string = False
        escaped = False
        result = ''
        for c in text:
            if c == '"' and not escaped:
                in_string = not in_string
            if c == '\n' and in_string:
                result += '\\n'
            else:
                result += c
            escaped = (c == '\\') and not escaped
        return result

    try:
        if isinstance(response_content, str):
            # Remove ```json or ``` markdown formatting
            response_content = re.sub(r"^```(?:json)?|```$", "", response_content.strip(), flags=re.IGNORECASE).strip()

            # Fix unescaped line breaks inside string values
            cleaned = escape_newlines_inside_strings(response_content)
            print("[DEBUG] Cleaned response content:", cleaned)

            parsed_model = LLMComplianceResult.model_validate_json(cleaned)
        else:
            # If already a dict
            parsed_model = LLMComplianceResult(**response_content)

        return parsed_model.model_dump()

    except (json.JSONDecodeError, ValidationError, Exception) as e:
        print(f"[ERROR] Failed to parse LLM response: {e}")
        return {
            "compliance_status": "INDECISIVE",
            "flags": [],
            "needs_human_review": True,
            "Brief_report": original_report[:150] + "...",
            "report": original_report
        }


def compress_image(input_path, output_path=None, quality=70):
    """
    Compresses an image by reducing quality and optionally resizing it.

    Args:
        input_path (str): Path to the original image.
        output_path (str): Path to save the compressed image. If None, overwrites the input image.
        quality (int): Quality level (1-100). Lower means more compression.
        max_width (int): Maximum width of the resized image (optional).
        max_height (int): Maximum height of the resized image (optional).

    Returns:
        str: Path to the compressed image.
    """
    img = Image.open(input_path)

    ext = os.path.splitext(input_path)[1]
    temp_dir = os.path.join("temp_uploads", str(uuid.uuid4()))
    os.makedirs(temp_dir, exist_ok=True)
    temp_filename = f"{uuid.uuid4()}{ext}"
    temp_path = os.path.join(temp_dir, temp_filename)

    # Ensure output path is defined
    if output_path is None:
        output_path = temp_path

    # Save with reduced quality, but same dimensions
    img.save(output_path, optimize=True, quality=quality)

    return output_path


def compress_image_to_max_size(input_path, output_path=None, max_size=1_048_576):
    """
    Compress an image to be under max_size bytes without changing dimensions.

    Args:
        input_path (str): Path to the input image.
        output_path (str): Path to save the compressed image. If None, input_path will be used.
        max_size (int): Maximum allowed file size in bytes. Default is 1 MB.

    Returns:
        str: Path to the compressed image.
    """
    img = Image.open(input_path)

    # 🔁 Convert RGBA or LA (with transparency) to RGB
    if img.mode in ("RGBA", "LA"):
        background = Image.new("RGB", img.size, (255, 255, 255))  # white background
        background.paste(img, mask=img.split()[-1])  # paste using alpha as mask
        img = background
    else:
        img = img.convert("RGB")  # Ensure RGB for JPEG

    if output_path is None:
        base, _ = os.path.splitext(input_path)
        output_path = base + ".jpg"

    quality = 95
    min_quality = 10
    buffer = io.BytesIO()

    while quality >= min_quality:
        buffer.seek(0)
        buffer.truncate()
        img.save(buffer, format="JPEG", optimize=True, quality=quality)
        size = buffer.tell()

        if size <= max_size:
            with open(output_path, 'wb') as f:
                f.write(buffer.getvalue())
            return output_path

        quality -= 5

    raise ValueError("Could not compress image below max size with acceptable quality.")


def delete_files(folder_path: str):
    folder_path = Path(folder_path)
    for file in folder_path.iterdir():
        if file.is_file():
            try:
                file.unlink()
                print(f"✅ Deleted: {file}")
            except Exception as e:
                print(f"❌ Failed to delete {file}: {e}")


async def download_image_gathering(client, url, temp_dir):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        response = await client.get(url, headers=headers, follow_redirects=True)
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}")

        ext = os.path.splitext(url)[1] or ".jpg"
        temp_filename = f"{uuid.uuid4()}{ext}"
        temp_path = os.path.join(temp_dir, temp_filename)

        with open(temp_path, "wb") as f:
            f.write(response.content)

        return compress_image_to_max_size(temp_path)

    except Exception as e:
        raise Warning(f"Failed to download {url}: {e}")
    

def parse_retrieved_text_to_json(text: str) -> dict:
    results = defaultdict(list)
    current_file = None
    current_content = []

    for line in text.strip().splitlines():
        match = re.match(r"📄 \*\*(?:من الملف:|From file:)\*\* (.+)", line.strip())
        if match:
            
            if current_file and current_content:
                results[current_file].append("\n".join(current_content).strip())

            current_file = match.group(1).strip()
            current_content = []
        else:
            if current_file:
                current_content.append(line)

    if current_file and current_content:
        results[current_file].append("\n".join(current_content).strip())

    return {"documents": results}



def flatten_clauses(data_json, source, page="Page not specified"):
    all_clauses = []
    clause_counter = 1

    for item in data_json:
        clauses = item.get("clauses", [])
        for clause in clauses:
            all_clauses.append({
                "title": f"البند {clause_counter}",
                "description": clause.get("description", "").strip(),
                "source": source, # clause.get("source", "").strip(),
                "page": page
            })
            clause_counter += 1

    return all_clauses


def extract_json_objects(text):
    json_objects = []
    brace_level = 0
    start_idx = None

    for idx, char in enumerate(text):
        if char == '{':
            if brace_level == 0:
                start_idx = idx
            brace_level += 1
        elif char == '}':
            brace_level -= 1
            if brace_level == 0 and start_idx is not None:
                json_str = text[start_idx:idx + 1]
                json_objects.append(json_str)
                start_idx = None

    return json_objects


def upload_to_alibaba_oss_static(bucket, local_file_path, object_name, bucket_name="glasshub-files-staging", endpoint="oss-me-central-1.aliyuncs.com"):
    try:
        with open(local_file_path, 'rb') as file:
            bucket.put_object(object_name, file)

        encoded_object_name = quote(object_name)

        # بناء الرابط النهائي الثابت
        url = f"https://{bucket_name}.{endpoint}/{encoded_object_name}"
        print(f"✅ Uploaded with static URL: {url}")
        return url

    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return None


def upload_files_to_alibaba_oss_static(bucket, local_file_path, object_name, bucket_name="glasshub-files-staging", endpoint="oss-me-central-1.aliyuncs.com"):
    try:
        # Upload the file from local path to OSS object
        bucket.put_object_from_file(object_name, local_file_path)

        # Encode object name for URL safety
        encoded_object_name = quote(object_name)

        # Build the final static URL
        url = f"https://{bucket_name}.{endpoint}/{encoded_object_name}"
        print(f"✅ Uploaded with static URL: {url}")
        return url

    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return None


def download_from_alibaba_oss(url, local_path):
    try:
        response = requests.get(url)
        response.raise_for_status()

        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        with open(local_path, 'wb') as f:
            f.write(response.content)

        print(f"✅ Downloaded from URL: {url} → {local_path}")
        return True

    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False


def init_oss_bucket(access_key_id, access_key_secret, endpoint, bucket_name):
    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, endpoint, bucket_name)
    return bucket


def extract_clauses_with_system_message(QWEN3_ENDPOINT: str, prompt: str, max_tokens: int = 512, thinking: bool = False):
    system_message = """
    أنت مساعد ذكي مخصص لاستخراج البنود القانونية والتنظيمية من النصوص.
    📌 المطلوب:
    قم باستخراج التعليمات الصريحة أو الالتزامات أو القيود من مستندات مكتوبة بالعربية أو الإنجليزية (مثل السياسات أو العقود)، وأرجعها ككائن JSON بالهيكل التالي تحت المفتاح `flattened`:

    {
    "flattened": [
        {
        "title": "البند 1",
        "description": "نص البند...",
        "source": "اسم الملف.docx",
        "page": "Page not specified"
        },
        ...
    ]
    }

    📎 التعليمات الإلزامية:
    1. يجب أن تكون **كل نتيجة عبارة عن عنصر منفصل** في القائمة.
    2. لا تدمج أكثر من بند داخل `description` واحد.
    3. لا تكرر البنود.
    4. لا تُرجع أي محتوى خارج الـ JSON (مثل شروحات، مقدمات، أو نصوص خارجية).
    5. كل بند يجب أن يحتوي على:
    - `title` باسم مثل: "البند 1"، "البند 2"، ...
    - `description`: صياغة واضحة للبند المستخرج.
    - `source`: اسم الملف كما تم تمريره لك.
    - `page`: دائمًا "Page not specified".

    ✅ مثال واضح:
    {
    "flattened": [
        {
        "title": "البند 1",
        "description": "يجب على مقدم الخدمة حماية البيانات الشخصية.",
        "source": "مثال_raw_response.docx",
        "page": "Page not specified"
        },
        {
        "title": "البند 2",
        "description": "يُحظر على مقدم الخدمة مشاركة البيانات دون موافقة المستخدم.",
        "source": "مثال_raw_response.docx",
        "page": "Page not specified"
        }
    ]
    }

    🔒 لا تخرج عن هذا التنسيق أبدًا. فقط أرجع الكائن JSON أعلاه بدون أي تعليقات أو تنسيقات إضافية.
    """

    # Combine system + user message
    full_prompt = f"{system_message}\n\nUSER:\n{prompt}"

    headers = {
        "accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "prompt": full_prompt,
        "max_tokens": str(max_tokens),
        "thinking": str(thinking).lower()
    }

    response = httpx.post(QWEN3_ENDPOINT, headers=headers, data=data, timeout=240)
    if response.status_code != 200:
        raise Exception(f"❌ LLM Error: {response.status_code} - {response.text}")

    return response.json()


def download_from_url(url, local_path):
    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(local_path, 'wb') as f:
            f.write(response.content)
        print(f"✅ Downloaded from URL: {url} → {local_path}")
        return True
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False
    

def convert_docx_to_pdf(docx_path, pdf_path):
    convert(docx_path, pdf_path)


def extract_pages_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    pages = [doc.load_page(i).get_text() for i in range(len(doc))]
    return pages


def estimate_chunk_size(pages: list[str], max_tokens: int = 2000) -> int:
    page_lengths = [len(page) for page in pages]
    avg_chars = sum(page_lengths) / len(page_lengths)
    avg_tokens = avg_chars / 4  
    return max(1, int(max_tokens / avg_tokens)) 


def chunk_pages(pages: list[str], chunk_size: int = 2) -> list[str]:
    return ["\n".join(pages[i:i+chunk_size]) for i in range(0, len(pages), chunk_size)]


def save_temp_file(uploaded_file: UploadFile, save_path: str):
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(uploaded_file.file, buffer)
    return save_path


def download_files_from_cloud_storage(json_data: List[str], download_dir="./database/glasshub_files"):
    os.makedirs(download_dir, exist_ok=True)

    for url in json_data:
        filename = urllib.parse.unquote(os.path.basename(url))
        local_path = os.path.join(download_dir, filename)
        download_from_url(url, local_path)

def load_documents():
    documents = []
    for filename in os.listdir(DOCX_DIRECTORY):
        if filename.endswith(".docx"):
            file_path = os.path.join(DOCX_DIRECTORY, filename)
            loader = UnstructuredFileLoader(file_path)
            pages = loader.load()

            for i, doc in enumerate(pages):
                doc.metadata["source"] = filename  # Set real file name as source
                doc.metadata["page_number"] = i + 1
                documents.append(doc)
    return documents


def retrieve_full_knowledge_from_docx(documents):
    formatted_results = []
    for doc in documents:
        source = doc.metadata.get("source", "Unknown source")
        page = doc.metadata.get("page", "Page not specified")
        content = doc.page_content.strip()

        formatted_results.append({
            "source": source,  
            "page": page,
            "content": content
        })

    return formatted_results

def process_all_formatted_results(formatted_results):
    all_parsed_responses = []

    for item in formatted_results:
        content = item['content']
        source = item['source']
        page = item.get('page', "Page not specified")

        json_blocks = extract_json_objects(content)

        data_js = []
        for block in json_blocks:
            try:
                data_js.append(json.loads(block))
            except Exception as e:
                print(f"Error loading block from {source}, page {page}: {e}")

        if not data_js:
            print(f"No valid JSON blocks found in {source}, page {page}")
            continue

        flattened = flatten_clauses(data_js, source, page)
        terms = extract_clauses_with_system_message(QWEN3_ENDPOINT_CHAT, flattened, 6000, False)

        if isinstance(terms, dict):
            terms = terms.get('response', '')

        try:
            terms_dict = json.loads(terms)
            flattened_terms = terms_dict.get("flattened", [])
            parsed_response = [
                item for item in flattened_terms
                if len(item.get("description", "")) >= 50
            ]
            json_parsed_response = process_parsed_response(parsed_response)
            all_parsed_responses.append(json_parsed_response)
        except Exception as e:
            print(f"Error processing terms from {source}, page {page}: {e}")
    
    return all_parsed_responses
