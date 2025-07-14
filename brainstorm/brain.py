# control_number *
# string
# 1
# control_name *
# string
# Policies, Processes, and Procedures (GV.PO)
# control_statement *
# string
# Information security management Suppliers must have defined policies for information security, approved by their management, and communicated to the people with access to their information systems.
# control_guidelines *
# string
# - Provide evidence of the supplier Cybersecurity Policies and Standards. - Provide evidence of communicating Cybersecurity Policies to employees. - Provide evidence where policies should be version-controlled
# expert_type *
# string
# Security
# standard_type *
# string
# Aramco Security
# classification *
# string
# - General Requirements   - Network Connectivity NC   - Cloud Computing Services CCS   - Outsourcing and Managed Services OMS   - Consultancy Services CS   - Software Management SM   - OT/ICS Products and Services OT

# --------------------------------------------------------------------------------------------------------------------------
# @router.post("/save_edit_controls")
# async def save_edit_controls(
#     control_number: str = Form(...),
#     control_name: str = Form(...),
#     control_statement: str = Form(...),
#     control_guidelines: str = Form(...),
#     classification: List[str] = Depends(parse_classification),
#     expert_type: str = Form(...),
#     standard_type: str = Form(...)
# ):
#     """
#     Endpoint to generate compliance prompt based on control data.
#     """
#     logger.info(f"Received request for control data with number: {control_number}")

#     try:
#         prompt = generate_compliance_prompt(
#             control_number,
#             control_name,
#             control_statement,
#             control_guidelines,
#             classification,
#             expert_type,
#             standard_type
#         )
#         # 2. Save the prompt
#         file_path = save_control_prompt(control_number, prompt)
#         logger.info(f"Control prompt saved at: {file_path}")
#         # 3. Merge all controls into a single file
#         merge_all_controls()
#         logger.info("All control prompts merged successfully.")
#         # 4. Return the generated prompt and file path
#         return {"prompt": prompt, "file_path": file_path}

#     except Exception as e:
#         logger.exception("Failed to generate compliance prompt.")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/get_controls")
# async def get_controls():
#     """
#     Endpoint to retrieve all saved control prompts (.py files).
#     Returns a dictionary with control ID and content.
#     """
#     save_dir = "./database/saved_controls"
#     controls = []

#     for filename in sorted(os.listdir(save_dir)):
#         if filename.endswith(".py") and filename != "merged_controls.py":
#             file_path = os.path.join(save_dir, filename)
#             with open(file_path, "r", encoding="utf-8") as f:
#                 content = f.read()

#             controls.append({
#                 "control_id": filename.replace(".py", ""),  # e.g. control_01
#                 "content": content
#             })

#     return {"controls": controls}


# @router.post("/generate_dynamic_report")
# async def generate_dynamic_report(
#     control_number: str = Form(...),
#     control_file: UploadFile = File(...),
#     images: List[UploadFile] = File(...)
# ):
#     """
#     Generate a compliance report from uploaded merged_controls.py and a control number.
#     """
#     temp_dir = os.path.join("temp_uploads", str(uuid.uuid4()))
#     os.makedirs(temp_dir, exist_ok=True)
#     image_paths = []

#     try:
#         logger.info(f"Generating report for control_number: {control_number}")

#         if not control_file.filename.endswith(".py"):
#             raise HTTPException(status_code=400, detail="Control file must be a .py file")
        
#         # ✅ Step 1: Read .py file content
#         content = await control_file.read()
#         content_str = content.decode("utf-8")

#         # ✅ Step 2: Save and compress uploaded images
#         for upload in images:
#             ext = os.path.splitext(upload.filename)[1]
#             temp_filename = f"{uuid.uuid4()}{ext}"
#             temp_path = os.path.join(temp_dir, temp_filename)

#             with open(temp_path, "wb") as buffer:
#                 shutil.copyfileobj(upload.file, buffer)

#             compressed_path = compress_image_to_max_size(temp_path)
#             image_paths.append(compressed_path)

#         # ✅ Step 3: Pass to report generator (it handles control parsing)
#         report_generator = Reports(
#             control_number=control_number, 
#             list_image_paths=image_paths, 
#             controls_content=content_str
#         )
#         result = report_generator.final_output_handling_parsing()

#         logger.info("Report generated successfully.")
#         return result

#     except Exception as e:
#         logger.exception("Failed to generate report.")
#         raise HTTPException(status_code=500, detail=str(e))

#     finally:
#         shutil.rmtree(temp_dir, ignore_errors=True)
#         logger.info(f"Temp directory exists: {os.path.exists(temp_dir)}")
#         logger.info(f"Cleaned up temp directory: {temp_dir}")


# --------------------------------------------------------------------------------------------------------------------------
    # def final_output(self):

    #     report_text = self.Images_report()  # FIX: Call the instance method, not the class

    #     # Prompt for extracting compliance information
    #     prompt = """
    #     You are a highly accurate information extraction system. Given a compliance report, extract the following information and return it in a JSON object with the fields: "compliance_status", "flags", "full_report", "needs_human_review", and "indecisive_areas". Follow these guidelines:

    #     compliance_status: Extract the final compliance decision, either "COMPLIANT", "NON-COMPLIANT", or "INDECISIVE". Use "INDECISIVE" if the report does not provide enough evidence to confidently determine compliance or non-compliance. If not explicitly stated, infer from the report's conclusion. Format as a string, all uppercase.

    #     flags: Identify any issues, missing items, or additional requirements mentioned in the report (e.g., "Missing documents", "Additional proof needed"). Return as a list of strings. If none are mentioned, return an empty list.

    #     Brief_report: Provide a concise summary of the report’s findings, including the compliance decision and key evidence. Limit to 150 words. If the report exceeds this, summarize without losing critical details.

    #     needs_human_review: Determine if the report indicates a need for human review (e.g., mentions "additional proof needed", "requires review", or incomplete evidence). Return a boolean (true if review is needed, false otherwise).

    #     Important Note: If the agent cannot 100% judge whether the report is COMPLIANT or NON-COMPLIANT, set compliance_status to "INDECISIVE".

    #     Return the result as a JSON object with the exact field names above. If any field cannot be determined, use null for strings or false for booleans, and an empty list for flags. Ensure the output is valid JSON.

    #     Report: {REPORT_TEXT}

    #     Output Format: { "compliance_status": "COMPLIANT", "flags": ["Missing "x" document"], "Brief_report": "Summary of findings...", "needs_human_review": false }
    #     """

    #     # Combine prompt with report text
    #     full_prompt = prompt.replace("{REPORT_TEXT}", report_text)
    #     messages_list = [{"content": full_prompt}]
    #     messages_json_str = json.dumps(messages_list)
        
    #     json_payload = json.dumps([messages_json_str])

    #     #messages_json_str = json.dumps(messages_list)


    #     # Make the POST request with error handling
    #     try:
    #         response = requests.post(
    #             self.endpoint_url,
    #             data={
    #                 'messages': json_payload,
    #                 'max_new_tokens': str(max_new_tokens),
    #             }
    #         )
    #         final_response = response.json()
    #         print(f"final_response: {final_response}")
    #         final_result = parse_llm_response(final_response, report_text)
    #         return final_result
    #         #print("DEBUG: Status Code:", response.status_code)
    #         #print("DEBUG: Response:", response.text)
    #     except Exception as e:
    #         print(" Exception:", str(e))
    #         return {f"Error in final_output function: {str(e)}"}
        

