from apis.api_main_process_router import save_edit_controls


""" 
# save and edit controls endpoint pipeline.
1- take the json file from backend.
2- parse the json file to extract control data.
3- generate a prompt for each control.
4- save the prompt to a file.
5- merge all control prompts into a single file.
6- upload the merged file to Azure Blob Storage.
7- return the results with file paths URL.
8- backend team will download the merged file from url and save it to the database to be used later.

# generate report endpoint pipeline (single control).
1- take the merged file from backend that created from (Azure Blob Storage).
2- take the number of control from user.
3- take the images from user.
4- generate the report and get the results from agent.
5- return the json format of the results.

# generate report endpoint pipeline ( single / multiple controls ).
1- take the merged file from backend that created from (Azure Blob Storage).
2- take json file has number of controls and their images from backend.
3- loop through each control in the json file to pass it to the agent.
4- generate the report and get the results from agent.
5- return the json format of each control's results.

"""

def pipeline(data):
    pass
