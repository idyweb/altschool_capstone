# Scissors

Brief is the new black, this is what inspires Scissors. In todays world, its important to keep things as short as possible, and this applies to more concepts than you may realize. From music, and speeches, to wedding receptions, brief is the new black. Scissors is a simple tool that makes URLs as short as possible.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/idyweb/altschool_capstone.git

2. Install dependencies:
   ```bash
   pip install -r requirements.txt

3. Run the server:
   ```bash
   uvicorn main:app --reload

4. Access the API documentation at http://localhost:8000/docs and explore the available endpoints.

**Endpoints**

**Authentication**

- **POST /auth/signup**: Register a new user.

- **POST /auth/login**: Log in and obtain an access token.

**URL Shortener**

- **POST /url/shorten**: Shorten a URL.

- **GET /urls**: Retrieve all shortened URLs created by the authenticated user.
- **PUT /url/{shortened_url}**: Update a shortened URL.
- **DELETE /url/{shortened_url}**: Delete a shortened URL.
- **GET /url/{shortened_url}**: Redirect to the original URL associated with a shortened URL.

**Authentication**

This project uses OAuth2 password flow for authentication. Users can sign up for a new account or log in with their credentials to obtain an access token. The access token is required to access protected endpoints.

**Hosted Backend**

[Link to the hosted backend](https://altschool-1id4.onrender.com)
