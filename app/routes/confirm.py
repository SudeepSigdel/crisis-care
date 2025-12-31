import logging
from fastapi import APIRouter,HTTPException, status
from sqlmodel import select
from ..models import User, Request
from ..database import SessionLocal
from ..config import settings
from mailjet_rest import Client

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/confirm_request/{request_id}/{volunteer_id}")
async def confirm_request(request_id: int, volunteer_id: int, db: SessionLocal):
    logger.info(f"Received volunteer_id: {volunteer_id}")

    request = db.exec(select(Request).where(Request.id == request_id)).first()
    logger.info(f"Request: {request}")
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    
    volunteer = db.exec(select(User).where(User.id == volunteer_id, User.role == "volunteer")).first()
    if not volunteer:
        raise HTTPException(status_code=404, detail="Volunteer not found")
    
    if request.is_confirmed:
        return {"message": "This request has already been confirmed."}

    request.is_confirmed = True
    request.volunteer_id = volunteer_id
    db.add(request)
    db.commit()
    if request.id is not None:
        await notify_victim(request.id, db)
    if volunteer.id is not None:
        await send_confirmation_email(volunteer.id, request, db)

    return {"message": "You have successfully confirmed the request!"}

async def send_confirmation_email(volunteer_id: int, request: Request, db: SessionLocal):
    volunteer = db.exec(select(User).where(User.id == volunteer_id)).first()
    if not volunteer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Volunteer not found")

    confirmation_link = f"{settings.url}/confirm_request/{request.id}/{volunteer.id}"

    subject = "New Volunteer Request - Confirm Participation"
    body = f"""
    Hello {volunteer.firstname},\n
    \n
    You have been assigned to a new request titled "{request.title}".\n
    Please click the link below to confirm your participation:\n
    \n
    Request details:\n
        \t- Title: {request.title}
        \t- Description: {request.description}
        \t- Location: {request.location_lat}, {request.location_lon}\n
    \n
    ✅ [Confirm Request]({confirmation_link})\n
    \n
    If you are unable to help, you may ignore this email.\n
    \n
    Best,\n
    CrisisCare Team
    """

    # Send email using Mailjet
    send_email(volunteer.email, subject, body)

async def notify_victim(request_id: int, db: SessionLocal):
    request = db.exec(select(Request).where(Request.id == request_id)).first()
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    
    # Notify the victim first
    victim = db.exec(select(User).where(User.id == request.user_id)).first()
    if not victim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Victim not found")

    volunteer = db.exec(select(User).where(User.id == request.volunteer_id)).first()
    if not volunteer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Volunteer not found")

    # Notify the victim with the details
    subject = "Help is on the way!"
    body = f"""
    Hello {victim.firstname},\n
    A volunteer has confirmed your request: "{request.title}".\n
    Volunteer details:\n
    - Name: {volunteer.firstname}\n
    - Contact: {volunteer.email}\n
    \n
    Stay safe!\n
    CrisisCare Team
    """
    
    send_email(victim.email, subject, body)
    
    # Now notify all volunteers
    volunteers = db.exec(select(User).where(User.role == "volunteer")).all()  # Get all volunteers
    if not volunteers:
        raise HTTPException(status_code=404, detail="No volunteers found")

# Helper function to send emails using Mailjet API
def send_email(to_email: str, subject: str, body: str):
    api_key = settings.mailjet_api_key  # Your Mailjet API Key
    api_secret = settings.mailjet_api_secret  # Your Mailjet API Secret
    mailjet = Client(auth=(api_key, api_secret), version='v3.1')

    data = {
        'Messages': [
            {
                'From': {
                    'Email': settings.mail_from,  # Your 'from' email address
                    'Name': "CrisisCare Team"
                },
                'To': [
                    {
                        'Email': to_email
                    }
                ],
                'Subject': subject,
                'TextPart': body,
                'HTMLPart': f"<h3>{body}</h3>"
            }
        ]
    }

    result = mailjet.send.create(data=data)
    
    if result.status_code == 200:
        print(f"Email sent successfully to {to_email}")
    else:
        print(f"Error sending email: {result.status_code} - {result.text}")
        raise HTTPException(status_code=500, detail="Error sending email with Mailjet")
