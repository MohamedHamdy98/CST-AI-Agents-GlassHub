from fastapi import Form
from typing import List
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def generate_compliance_prompt(
    control_number: str,
    control_name: str,
    control_statement: str,
    control_guidelines: str,
    classification: list,
    expert_type: str,
    standard_type: str
) -> str:
    # Auto-generate the control instruction based on the provided inputs
    control_instruction = f"""
Your task is to assess the provided image as evidence for the following control: **{control_name}**.
You should confirm the following:
- That the control objective is being met as described: "{control_statement.strip()}"
- That the evidence supports the listed guidelines, including:
{control_guidelines.strip()}
- That the evidence clearly supports the control classification areas: {", ".join(classification)}.
Be sure the image shows adequate proof of the above. If any part is unclear, missing, or unsupported, consider the control as NON-COMPLIANT and explain why.
""".strip()
    return f"""
You are an expert in {expert_type} compliance. Your task is to review the provided image and determine if it meets the requirements of the specified control.
The control is part of a {expert_type} audit based on {standard_type} standards.
### 📋 Control Metadata
**1. Control Number**  
A unique identifier for the control under review.  
➡️ `{control_number}`
**2. Control Name**  
The title or label describing the area of focus for the control.  
➡️ `{control_name}`
**3. Control Statement**  
A description of what is required or expected for compliance.  
➡️ `{control_statement.strip()}`
**4. Control Guidelines**  
Detailed expectations or types of acceptable evidence.  
➡️ {control_guidelines.strip()}
**5. Classification**  
Categories or domains the control applies to.  
➡️ {", ".join(classification)}
---
### 🔍 Control Instruction:
{control_instruction}
---
### 🖼️ Provided Evidence:
You are given an image (e.g., screenshot, scanned document, policy file). Analyze the content in the image to assess whether it supports compliance with the control metadata and instruction.
---
### 📌 Final Compliance Decision:
Based on the above review, determine:
- **COMPLIANT**: If segmentation is implemented, inter-subnet traffic is restricted by firewall rules, and monitoring is confirmed.
- **NON-COMPLIANT**: If servers and workstations share the same subnet, if traffic is unrestricted, or if monitoring is absent or unclear.
- **INDECISIVE**: If the report does not provide enough confidence to determine compliance.
If any component is missing, incomplete, or unclear in the evidence, mark the control as **NON-COMPLIANT** and describe what additional proof is needed.
"""


def save_control_prompt(control_number: str, prompt: str, save_dir: str = "./database/saved_controls") -> str:
    """
    Save the generated control prompt to a .py file as a valid Python variable.

    Args:
        control_number (str): The unique control number, e.g. "CT-01"
        prompt (str): The generated compliance prompt to be saved.
        save_dir (str): Directory where the .py files will be stored.

    Returns:
        str: Full path to the saved file.
    """
    # Ensure the directory exists
    os.makedirs(save_dir, exist_ok=True)

    # Normalize control number to be a valid Python variable name (e.g., CT-01 -> control_01)
    control_display_number = control_number.split("-")[-1].replace(".", "_")
    variable_name = f"control_{control_number}"

    # Create the Python content with triple-quoted string
    formatted_content = f'{variable_name} = """\n{prompt}\n"""'

    # Save as a Python file
    file_path = os.path.join(save_dir, f"{variable_name}.py")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(formatted_content)

    return file_path


def merge_all_controls(save_dir: str = "./database/saved_controls") -> str:
    """
    Merge all saved .py control files into a single Python file.

    Args:
        save_dir (str): Directory where the .py control files are stored.

    Returns:
        str: Path to the merged Python file.
    """
    merged_content = "# Auto-generated merged control prompts\n\n"
    for filename in sorted(os.listdir(save_dir)):
        if filename.endswith(".py") and filename != "merged_controls.py":
            file_path = os.path.join(save_dir, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                merged_content += f"# From: {filename}\n" + f.read() + "\n\n"

    merged_file_path = os.path.join(save_dir, "merged_controls.py")
    with open(merged_file_path, "w", encoding="utf-8") as f:
        f.write(merged_content)

    return merged_file_path


def parse_classification(classification: str = Form(...)) -> List[str]:
    return [item.strip() for item in classification.split(",")]