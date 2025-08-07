results = {
  "results": [
    {
      "id": 0,
      "image_name": "test.jpg",
      "compliance": "NON-COMPLIANT",
      "flags": [
        "The image shows a 'Change Password' window and a Command Prompt window, which are unrelated to SMS service terms and conditions.",
        "The presence of a 'User Account Control Panel' message indicating password policy requirements suggests a potential non-compliance with security policies."
      ],
      "needs_review": 'true',
      "Brief_report": "The image displays a Windows interface with a 'Change Password' window and a Command Prompt showing a hostname command, which are not relevant to SMS service terms and conditions. Additionally, the password policy message indicates potential non-compliance.",
      "report": "The image does not appear to be directly related to the audit instructions provided for checking the SMS service terms and conditions. The image shows a Windows operating system interface with a \"Change Password\" window open, along with a Command Prompt window displaying a hostname command. It seems to be unrelated to the audit process described in the instructions.\n\nIf you need assistance with the audit instructions, please provide more details or clarify if there is a specific part of the instructions you would like help with."
    },
    {
      "id": 1,
      "image_name": "WhatsApp Image 2025-06-23 at 12.17.26 PM.jpeg",
      "compliance": "NON-COMPLIANT",
      "flags": [
        "The image contains email addresses and passwords for different roles within a system called GlassHub, which is unrelated to the control number \"بالمد 5\" or the audit instructions for SMS service terms and conditions."
      ],
      "needs_review": 'true',
      "Brief_report": "The image is unrelated to the control number \"بالمد 5\" or the audit instructions for SMS service terms and conditions.",
      "report": "The image provided does not contain any information related to the control number \"بالمد 5\" or the audit instructions for SMS service terms and conditions. The image appears to be a table with email addresses and passwords for different roles within a system called GlassHub, along with URLs for platform and admin access. It seems unrelated to the description and audit instructions you've provided. If you need assistance with the audit instructions or the content of the image, please clarify your request."
    }
  ]
}

for r in results["results"]:
    print(r["id"])
