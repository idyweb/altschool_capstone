from fastapi import Depends, HTTPException, Path, APIRouter, Request, Form, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from typing import Annotated, Optional, Union
from pydantic import BaseModel, Field, ValidationError, validators,validator
from sqlalchemy.orm import Session
from scissors import models
from starlette import status
from scissors.models import Urls
from scissors.db import engine, session
from scissors.routers.auth import get_current_user
from urllib.parse import urlparse
from fastapi.security import OAuth2PasswordBearer
import random
import string
import qrcode
import os
from urllib.parse import urlparse


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
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class UrlsValidator(BaseModel):
    original_url: str = Field(max_length=1000)
    custom_path: Optional[str] = Field(max_length=20)
    full_shortened_url: str = Field(max_length=1000)

async def get_token_from_header_or_cookie(request: Request):
    token: str = await oauth2_scheme(request)
    print(token, 'this is token')
    if token:
        return token
    print(request.cookies, 'this is request.cookies')
    if "access_token" in request.cookies:

        return request.cookies["access_token"]
    raise HTTPException(status_code=401, detail="Not authenticated")

def generate_short_code():
    # Generate a random short code consisting of alphanumeric characters
    characters = string.ascii_letters + string.digits
    short_code = ''.join(random.choices(characters, k=6))  # Adjust the length as needed
    return short_code

def check_uniqueness(db: Session, short_code: str):
    
    # Check if the short code already exists in the database
    return db.query(Urls).filter(Urls.shortened_url == short_code).first()

def generate_new_code(db: Session, short_code):
    print(check_uniqueness(db, short_code), 'this is check_uniqueness')
    if check_uniqueness(db, short_code):
        short_code = generate_short_code()
        return generate_new_code(db, short_code)
    else:
        return short_code
    
def validate_url_data(url_data):
    original_url = url_data.get('original_url')
    if not original_url:
        return False

    try:
        result = urlparse(original_url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


@url_router.post("/url/shorten", response_model=UrlsValidator,  status_code=status.HTTP_201_CREATED)
async def shorten_url(request:Request, original_url: str = Form(...), access_token: str = Cookie(None), db: Session = Depends(get_db), custom_path: Optional[str] = None):
    if not access_token:
        return RedirectResponse(url='/login', status_code=status.HTTP_303_SEE_OTHER)
    current_user = await get_current_user(access_token, db)
    
    # Validate the original_url
    if not validate_url_data({'original_url': original_url}):
        raise HTTPException(status_code=400, detail="Invalid URL")
    
    
    # Generate a unique short code
    short_code = generate_short_code()
    shortened_url = generate_new_code(db, short_code)
 
        
    if shortened_url is None:
        raise HTTPException(status_code=500, detail="Failed to generate a unique short code")
    
    shortened_url = shortened_url

    # Construct the full shortened URL
    full_shortened_url = f"http://{request.headers['host']}/url/{shortened_url}"
    if custom_path:
        full_shortened_url = f"http://{request.headers['host']}/{custom_path}/url/{shortened_url}"
        
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

    # Save the QR code image to a file
    qr_code_path = f"./static/{shortened_url}.png"
    qr_code_url = f"http://{request.headers['host']}/static/{shortened_url}.png"
    img.save(qr_code_path)

    # Save the mapping in the database
    if custom_path:
        db_url = models.Urls(original_url=original_url, shortened_url=shortened_url, full_shortened_url=full_shortened_url, user_id=current_user.id, custom_path=custom_path, qr_code_path=qr_code_path, visit_count=0)
    else:
        db_url = models.Urls(original_url=original_url, shortened_url=shortened_url, full_shortened_url=full_shortened_url, qr_code_path=qr_code_path, visit_count=0, user_id = current_user.id)
    try:
        db.add(db_url)
        db.commit()
    except Exception as e:
        print(f"Failed to add URL to database: {e}")
    
    return templates.TemplateResponse("index.html", {"request": request, 'qr_code_url' : qr_code_url, 'full_shortened_url':full_shortened_url})


@url_router.get("/urls")
def get_all_urls(db: Session = Depends(get_db), current_user: models.Users = Depends(get_current_user)):
    db_urls = db.query(models.Urls).filter(models.Urls.user_id == current_user.id).all()
    if db_urls is None:
        raise HTTPException(status_code=404, detail="URLs not found")
    return db_urls

@url_router.put("/url/{shortened_url}", response_model=UrlsValidator)
def update_url(shortened_url: str, url: UrlsValidator, db: Session = Depends(get_db), current_user: models.Users = Depends(get_current_user)):
    db_url = db.query(models.Urls).filter(models.Urls.shortened_url == shortened_url).first()
    if db_url is None or db_url.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="URL not found")
    
    # Validate the URL data
    url_data = url.dict()
    if not validate_url_data(url_data):
        raise HTTPException(status_code=400, detail="Invalid URL data")
    
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
    # Retrieve the original URL from the database based on the full shortened URL
    print(shortened_url, 'this is shortened_url')
    db_url = db.query(models.Urls).filter(models.Urls.shortened_url == f"{shortened_url}").first()
    
    
    if db_url:
        # Increment the visit count (optional)
        db_url.visit_count += 1
        db.commit()

        # Redirect to the original URL
        return RedirectResponse(url=db_url.original_url, status_code=status.HTTP_302_FOUND)
    else:
        # If the shortened URL is not found, return a 404 Not Found response
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shortened URL not found")