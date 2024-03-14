from fastapi import Depends, HTTPException, Path, APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from typing import Annotated, Optional, Union
from pydantic import BaseModel, Field, ValidationError, validators,validator
from sqlalchemy.orm import Session
import models
from starlette import status
from models import Urls
from db import engine, session
from .auth import get_current_user
import random
import string
import qrcode
import os


url_router = APIRouter(
    tags=['url_shortener']
)

models.Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory='templates')

def get_db():
    db = session()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[models.Users, Depends(get_current_user)]

class UrlsValidator(BaseModel):
    original_url: str = Field(max_length=1000)
    custom_path: Optional[str] = Field(max_length=20)


def generate_short_code():
    # Generate a random short code consisting of alphanumeric characters
    characters = string.ascii_letters + string.digits
    short_code = ''.join(random.choices(characters, k=6))  # Adjust the length as needed
    return short_code

def check_uniqueness(db: Session, short_code: str):
    # Check if the short code already exists in the database
    return db.query(Urls).filter(Urls.shortened_url == short_code).first() is None


# @url_router.get('/')
# def get_home(request: Request):
#     return "hello world"

@url_router.post("/url/shorten", response_model=UrlsValidator, status_code=status.HTTP_201_CREATED)
def shorten_url(original_url: str, request: Request, db: Session = Depends(get_db), current_user: models.Users = Depends(get_current_user), custom_path: Optional[str] = None):
    if original_url is None or original_url == '':
        raise HTTPException(status_code=400, detail="original_url is required")
    if request.headers.get('host') is None:
        raise HTTPException(status_code=400, detail="Host header is required")
    # Generate a unique short code
    while True:
        short_code = generate_short_code()
        print(f"short_code after generation: {short_code}")
        if check_uniqueness(db, short_code):
            print(f"shortened_url: {shortened_url}")
            shortened_url = short_code
            print(f"shortened_url after assignment: {shortened_url}")
            break
        
    if shortened_url is None:
        raise HTTPException(status_code=500, detail="Failed to generate a unique short code")

    # Construct the full shortened URL
    full_shortened_url = f"http://{request.headers['host']}/{shortened_url}"
    if custom_path:
        full_shortened_url = f"http://{request.headers['host']}/{custom_path}/{shortened_url}"
        
    if full_shortened_url is None:
        raise HTTPException(status_code=500, detail="Failed to construct shortened URL")
        
    print('this is full_shortened_url', full_shortened_url)

    # Save the mapping in the database
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(full_shortened_url)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')
    
    if not os.path.exists('qrcodes'):
        os.makedirs('qrcodes')

    # Save the QR code image to a file
    qr_code_path = f"qrcodes/{shortened_url}.png"
    img.save(qr_code_path)

    # Save the mapping in the database
    if custom_path:
        db_url = models.Urls(original_url=original_url, shortened_url=shortened_url, user_id=current_user.id, custom_path=custom_path, qr_code_path=qr_code_path, visit_count=0)
    else:
        db_url = models.Urls(original_url=original_url, shortened_url=shortened_url, qr_code_path=qr_code_path, visit_count=0)
    db.add(db_url)
    db.commit()
    
    # Return the newly created URL
    return {
        "id": db_url.id,
        "original_url": db_url.original_url,
        "shortened_url": full_shortened_url,
        "qr_code_path": db_url.qr_code_path,
        "visit_count": db_url.visit_count,
        "custom_path": db_url.custom_path
    }

# @url_router.get("/{shortened_url}", response_model=UrlsValidator)
# def get_url(shortened_url: str, db: Session = Depends(get_db), current_user: models.Users = Depends(get_current_user)):
#     db_url = db.query(models.Urls).filter(models.Urls.shortened_url == shortened_url).first()
#     if db_url is None or db_url.user_id != current_user.id:
#         raise HTTPException(status_code=404, detail="URL not found")
#     return db_url

@url_router.put("/url/{shortened_url}", response_model=UrlsValidator)
def update_url(shortened_url: str, url: UrlsValidator, db: Session = Depends(get_db), current_user: models.Users = Depends(get_current_user)):
    db_url = db.query(models.Urls).filter(models.Urls.shortened_url == shortened_url).first()
    if db_url is None or db_url.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="URL not found")
    
    # Update the URL
    for var, value in url.dict().items():
        setattr(db_url, var, value) if value else None
    db.commit()
    return db_url


@url_router.delete("/url/{shortened_url}")
def delete_url(shortened_url: str, db: Session = Depends(get_db), current_user: models.Users = Depends(get_current_user)):
    db_url = db.query(models.Urls).filter(models.Urls.shortened_url == shortened_url).first()
    if db_url is None or db_url.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="URL not found")
    db.delete(db_url)
    db.commit()

@url_router.get("/url/{shortened_url}", status_code=status.HTTP_302_FOUND)
def redirect_to_original_url(shortened_url: str, db: Session = Depends(get_db)):
    # Retrieve the original URL from the database based on the shortened URL
    db_url = db.query(models.Urls).filter(models.Urls.shortened_url == shortened_url).first()
    
    if db_url:
        # Increment the visit count (optional)
        db_url.visit_count += 1
        db.commit()

        # Redirect to the original URL
        return RedirectResponse(url=db_url.original_url, status_code=status.HTTP_302_FOUND)
    else:
        # If the shortened URL is not found, return a 404 Not Found response
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shortened URL not found")