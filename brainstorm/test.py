# Example data to test the function
test_data = [
    {"compliance": "COMPLIANT", "flags": ["No sensitive content detected"], "Brief_report": "Image passed all checks.", "report": "Detailed check shows no issues.", "needs_review": False},
    {"compliance": "NON_COMPLIANT", "flags": ["Detected prohibited content"], "Brief_report": "Image failed due to policy violation.", "report": "Found explicit content in region (120, 220).", "needs_review": True},
    {"compliance": "INDECISIVE", "flags": ["Low confidence in classification"], "Brief_report": "Unclear result, manual review recommended.", "report": "AI model detected possible violation but not certain.", "needs_review": False}
]


# Example usage
class Dummy:
    def combine_image_results(self, data):
        combined_flags = []
        combined_brief = []
        combined_report = []
        overall_status = "COMPLIANT"
        needs_review = False

        for item in data:
            status = str(item["compliance"])
            if "NON_COMPLIANT" in status:
                overall_status = "NON-COMPLIANT"
            elif "INDECISIVE" in status and overall_status != "NON-COMPLIANT":
                overall_status = "INDECISIVE"

            combined_flags.extend(item.get("flags", []))
            combined_brief.append(item.get("Brief_report", ""))
            combined_report.append(item.get("report", ""))
            if item.get("needs_review"):
                needs_review = True

        return {
            "compliance": overall_status,
            "flags": combined_flags,
            "Brief_report": "\n".join(combined_brief),
            "needs_review": needs_review,
            "report": "\n".join(combined_report)
        }

# Test
dummy = Dummy()
result = dummy.combine_image_results(test_data)
print(result)
