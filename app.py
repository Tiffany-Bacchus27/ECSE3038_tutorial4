from fastapi import FastAPI, HTTPException
import motor.motor_asyncio
from pydantic import BaseModel, BeforeValidator, Field
from typing import Annotated, List
from bson import ObjectId
from dotenv import load_dotenv
import os


load_dotenv()
app = FastAPI()

# MongoDB Connection
connection = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("MONGODB_URL"))
people_database = connection.people

# Custom Type for MongoDB ObjectId
PyObjectID = Annotated[str, BeforeValidator(str)]  

# Person Models
class Person(BaseModel):
    id: PyObjectID | None = Field(default=None, alias="_id")
    name: str
    occupation: str
    address: str

class PersonCollection(BaseModel):
    persons: List[Person]

class PersonUpdate(BaseModel):
    name: str | None = None
    occupation: str | None = None
    address: str | None = None

# Create Person
@app.post("/person")
async def create_person(person_request: Person):
    person_dictionary = person_request.model_dump()
    created_person = await people_database["group"].insert_one(person_dictionary)
    person = await people_database["group"].find_one({"_id": created_person.inserted_id})
    return Person(**person)

# Get All Persons
@app.get("/person")
async def get_persons():
    person_collection = await people_database["group"].find().to_list(999)
    return PersonCollection(persons=person_collection)

# Update Person (PATCH)
@app.patch("/persons/{person_id}")
async def update_person(person_id: str, person_update: PersonUpdate):
    if not ObjectId.is_valid(person_id):
        raise HTTPException(status_code=400, detail="Invalid person_id")

    object_id = ObjectId(person_id)

    # ✅ Check if person exists BEFORE updating
    existing_person = await people_database["group"].find_one({"_id": object_id})
    if not existing_person:
        raise HTTPException(status_code=404, detail="Person not found.")

    update_data = {key: value for key, value in person_update.model_dump().items() if value is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update.")

    await people_database["group"].update_one({"_id": object_id}, {"$set": update_data})
    updated_person = await people_database["group"].find_one({"_id": object_id})

    return {"message": "Person updated successfully", "person": updated_person}

# Delete Person
@app.delete("/persons/{person_id}")
async def delete_person(person_id: str):
    if not ObjectId.is_valid(person_id):
        raise HTTPException(status_code=400, detail="Invalid person_id.") 

    object_id = ObjectId(person_id)

    deleted_response = await people_database["group"].delete_one({"_id": object_id})

    if not deleted_response.deleted_count:
        raise HTTPException(status_code=404, detail="Person not found.")

    return {"message": "Person deleted successfully!"}
