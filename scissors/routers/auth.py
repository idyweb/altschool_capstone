from fastapi import APIRouter, Cookie, Depends, HTTPException,Request, Path
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Annotated
from pydantic import BaseModel, Field 
from sqlalchemy.orm import Session
from scissors.models import Users
from passlib.context import CryptContext
from scissors.db import session
from starlette import status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import Form
from starlette.responses import RedirectResponse

router = APIRouter(
    prefix='/auth',
    tags=['auth']
)

SECRET_KEY = '63ab7ac1d662423addb6d33b661413ca99fe035c069b3922f2acbacb04b1073e'
ALGORITHM = 'HS256'

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='/login')

templates = Jinja2Templates(directory="templates")

class CreateUserRequest(BaseModel):
    username: str
    email: str
    first_name: str
    last_name: str
    password: str
    role: str

class ShowUser(BaseModel):
    username: str
    email: str
    first_name: str
    last_name: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
   
def get_db():
    db = session()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]


def authenticate_user(username: str, password: str, db: db_dependency):
    user = db.query(Users).filter(Users.username == username).first()
    if user is None:
        return RedirectResponse(url='/login', status_code=status.HTTP_303_SEE_OTHER)
    if not bcrypt_context.verify(password, user.hashed_password):
        return RedirectResponse(url='/login', status_code=status.HTTP_303_SEE_OTHER)
    
    return user

def create_access_token(username: str, user_id: int, expires_delta:timedelta):
    encode = {'sub': username, 'id': user_id}
    expires = datetime.utcnow() + expires_delta
    encode.update({'exp': expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)
    

#async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)], db: db_dependency):
async def get_current_user(token: str = Cookie(None), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get('sub')
        user_id: int = payload.get('id')
        
        if username is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token. please login or signup')

        user = db.query(Users).filter(Users.id == user_id).first()
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not found')

        return user
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token. please login or signup')


@router.post("/signup", response_model=ShowUser, status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, username: str = Form(...), email: str = Form(...), first_name: str = Form(...), last_name: str = Form(...), password: str = Form(...)):
    create_user_model = Users(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
        hashed_password=bcrypt_context.hash(password),
        is_active=True
    )
    db.add(create_user_model)
    db.commit()
    db.refresh(create_user_model)
    return RedirectResponse(url='/login', status_code=status.HTTP_303_SEE_OTHER)

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=5)  # replace 5 with your actual token expiration time
    access_token = create_access_token(user.username, user.id, access_token_expires)

    response = RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    response.set_cookie("access_token", access_token, httponly=True)

    return response
    
    