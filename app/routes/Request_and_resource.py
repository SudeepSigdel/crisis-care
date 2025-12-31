from . import confirm
from ..models import Request
from ..utils import find_best_match
from fastapi import BackgroundTasks, APIRouter, Depends, HTTPException, status
from typing import List, Optional
from .. import models, schemas, utils, database, oauth2
from sqlmodel import select

router = APIRouter(
    tags=["Requests and Resources"]
)

# templates = Jinja2Templates(directory=config.TEMPLATE_FOLDER)
# try:
#     templates.get_template('email_template.html')
#     print("Template loaded successfully!")
# except Exception as e:
#     print(f"Error loading template: {str(e)}")

# Add a new victim request
@router.post("/requests", response_model=schemas.RequestResponse)
async def add_request(request: schemas.RequestCreate, db: database.SessionLocal, current_user = Depends(oauth2.get_current_user)):
    # Verify user from token
    user = db.exec(select(models.User).where(models.User.email == current_user.email)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create and add request to the database
    db_request = models.Request(
        title=request.title,
        description=request.description,
        request_type=request.request_type,
        location_lat=request.location_lat,
        location_lon=request.location_lon,
        user_id=current_user.id,
    )
    db.add(db_request)
    db.commit()
    db.refresh(db_request)


    # Get all volunteers in the database
    volunteers = db.exec(select(models.User).where(models.User.role == "volunteer")).all()
    # Notify volunteers about the new request
    if volunteers:
        for volunteer in volunteers:
            if volunteer.id == None:
                continue
            await confirm.send_confirmation_email(volunteer.id, db_request, db)

    return db_request


# Get all active victim requests
@router.get("/requests", response_model=List[schemas.RequestResponse])
def get_all_requests(db: database.SessionLocal):
    return db.exec(select(models.Request).where(models.Request.is_confirmed == False)).all()

# Add a new resource (donor)
@router.post("/resources", response_model=schemas.ResourceResponse)
async def add_resource(resource: schemas.ResourceCreate, db: database.SessionLocal, current_user=Depends(oauth2.get_current_user)):
    user = db.exec(select(models.User).filter(models.User.email == current_user.email)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    db_resource = models.Resource(
        resource_type=resource.resource_type,
        location_lat=resource.location_lat,
        location_lon=resource.location_lon,
        user_id=current_user.id
    )
    
    db.add(db_resource)
    db.commit()
    db.refresh(db_resource)



    return db_resource

# Get all available resources
@router.get("/resources", response_model=List[schemas.ResourceResponse])
def get_all_resources(db: database.SessionLocal):
    return db.exec(select(models.Resource)).all()

@router.put("/requests/{request_id}/status")
def update_request_status(request_id: int, statuscon: str, db: database.SessionLocal, current_user= Depends(oauth2.get_current_user)):
    user = db.exec(select(models.User).where(models.User.email == current_user.email)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    request = db.exec(select(models.Request).where(models.Request.id == request_id)).first()
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    if status not in ["pending", "in-progress", "resolved"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")

    request.status = statuscon
    db.add(request)
    db.commit()
    return {"message": "Status updated", "new_status": statuscon}

@router.get("/requests", response_model=List[schemas.RequestResponse])
def get_requests(db: database.SessionLocal, request_type: Optional[str] = None):
    query = db.exec(select(models.Request).where(models.Request.is_confirmed == False))
    if request_type:
        query = db.exec(select(models.Request).where(models.Request.is_confirmed == False, models.Request.request_type == request_type))
    return query.all()

@router.get("/resources", response_model=List[schemas.ResourceResponse])
def get_resources(db: database.SessionLocal, resource_type: Optional[str] = None):
    query = db.exec(select(models.Resource))
    if resource_type:
        query = db.exec(select(models.Resource).where(models.Resource.resource_type == resource_type))
    return query.all()


@router.get("/requests/{request_id}/nearest_resources", response_model=List[schemas.ResourceResponse])
def get_nearest_resources(db: database.SessionLocal, request_id: int, radius: Optional[float] = 50, resource_type: Optional[str] = None):
    # Get the victim request from the database
    request = db.exec(select(models.Request).where(models.Request.id == request_id)).first()
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    
    # Get all available resources
    resources = db.exec(select(models.Resource))
    if resource_type:
        resources = db.exec(select(models.Resource).where(models.Resource.resource_type == resource_type))
    resources = resources.all()
    
    # Filter resources based on distance
    nearby_resources = []
    for resource in resources:
        distance = utils.calculate_distance(request.location_lat, request.location_lon, resource.location_lat, resource.location_lon)
        if distance <= radius:
            nearby_resources.append((resource, distance))
    
    # Sort by distance (ascending)
    nearby_resources.sort(key=lambda x: x[1])
    
    # Only return resources, not the distance
    return [resource for resource, _ in nearby_resources]

@router.post("/match/{request_id}")
def match_request(request_id: int, background_tasks: BackgroundTasks, db: database.SessionLocal):
    request = db.exec(select(models.Request).where(Request.id == request_id, Request.is_confirmed == False)).first()
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found or already matched")

    best_match = find_best_match(request_id, db)

    if not best_match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No matching resources available")

    request.is_confirmed = True
    best_match.is_available = False
    db.add(request)
    db.commit()

    return {
        "message": "Match found!",
        "request_id": request.id,
        "resource_id": best_match.id,
        "donor_id": best_match.user_id,
        "location": {"lat": best_match.location_lat, "lon": best_match.location_lon}
    }