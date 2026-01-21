from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import os

security = HTTPBearer()
# SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "admin_secret")

# def verify_admin(
#     credentials: HTTPAuthorizationCredentials = Depends(security)
# ):
#     token = credentials.credentials
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
#         if payload.get("role") != "admin":
#             raise HTTPException(status_code=403, detail="Forbidden: Admins only")
#         return payload
#     except jwt.PyJWTError:
#         raise HTTPException(status_code=401, detail="Invalid admin token")

SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "admin_secret")

def verify_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403)
        return payload
    except:
        raise HTTPException(status_code=401, detail="Invalid admin token")
