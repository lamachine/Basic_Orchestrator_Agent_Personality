# This particular agent template is using structed output data
# Imports




# Cofiguration
model= get_model()

class Key_Info_Data_Structure(BaseModel):
    key: str
    value: str
    user: str
    appointment_datetime: str = Field(description="The date and time of the appointment in xyz format")
    # THIS IS YOUR VALIDATOR
    complete: bool = Field(default=False, description="Whether all information is complete")

system_prompt = """" \
You are a key information agent that helps users ensure important information
and options are covered for some particular request.
You will take the information provided in your prompt and store it in the
Key_Info_Data_Structure format. 
If all information is complete, you will set the complete flag to True and 
return it for further processing.
If any information is missing, you will set the complete flag to False and
prompt the user for the missing information.
"""

input_query_template_agent = Agent(
    model,
    results_type=Key_Info_Data_Structure,
    system_prompt=system_prompt,
    retries=2
)