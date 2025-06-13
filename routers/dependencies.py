from fastapi import Depends, HTTPException, Security
from auth import get_current_user # Assuming auth.py is in the same 'routes' folder
import models

def require_admin(current_user: models.User = Depends(get_current_user)):
    """
    A dependency that checks if the current user is an admin.
    If not, it raises a 403 Forbidden error.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403, 
            detail="Not authorized. Admin access required."
        )
    return current_user