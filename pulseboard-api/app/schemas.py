from pydantic import BaseModel, Field
class Credentials(BaseModel): email:str; password:str
class ProjectIn(BaseModel): name:str=Field(min_length=2,max_length=180); description:str=""
class TaskIn(BaseModel): project_id:int; title:str=Field(min_length=2,max_length=240)
class WebhookIn(BaseModel): event:str; external_id:str
