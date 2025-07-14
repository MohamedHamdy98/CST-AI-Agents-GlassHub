import json
import re, os, uuid, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image
import io
from urllib.parse import urlparse
from pydantic import ValidationError
from utils.schemas import LLMComplianceResult
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from pathlib import Path
import importlib.util


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


def upload_to_azure_blob(file_path: str, container_name: str, blob_name: str, connection_string: str) -> str:
    """
    Uploads a file to Azure Blob Storage and returns the blob URL.

    :param file_path: Local path to the file to upload.
    :param container_name: Azure Blob container name.
    :param blob_name: Desired name for the blob (e.g., merged_controls.py).
    :param connection_string: Azure Blob Storage connection string.
    :return: Public blob URL (if container is public).
    """
    try:
        # Connect to Azure Blob Storage
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)

        # Ensure the container exists
        if not container_client.exists():
            container_client.create_container()

        # Upload the file
        with open(file_path, "rb") as data:
            blob_client = container_client.get_blob_client(blob_name)
            blob_client.upload_blob(data, overwrite=True)

        blob_url = blob_client.url
        print(f"✅ Uploaded to Azure Blob Storage: {blob_url}")
        return blob_url

    except Exception as e:
        print(f"❌ Azure upload failed: {e}")
        raise


def download_blob_from_url(blob_url: str, destination_path: str, connection_string: str):
    """
    Downloads a blob from Azure Blob Storage given its public/private URL.

    :param blob_url: Full blob URL (e.g., https://account.blob.core.windows.net/container/blob_name)
    :param destination_path: Where to save the file locally.
    :param connection_string: Azure Storage connection string (used for private blobs).
    """
    try:
        # Parse container and blob name from URL
        parsed = urlparse(blob_url)
        path_parts = parsed.path.lstrip("/").split("/", 1)

        if len(path_parts) != 2:
            raise ValueError("Invalid blob URL format.")

        container_name, blob_name = path_parts
        print(f"📦 Container: {container_name}")
        print(f"📄 Blob name: {blob_name}")

        # Connect to blob storage
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

        # Download the blob
        with open(destination_path, "wb") as file:
            download_stream = blob_client.download_blob()
            file.write(download_stream.readall())

        print(f"✅ Blob downloaded to: {destination_path}")
        return destination_path

    except Exception as e:
        print(f"❌ Failed to download blob: {e}")
        raise


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
    

