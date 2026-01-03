import pytest
from sqlalchemy.orm import Session
from backend.src.services.core.authentication_service import AuthenticationService
from backend.src.services.core.user_management_service import UserManagementService
from backend.src.schemas.auth import UserCreate

def test_auth_services_split_verification(db: Session):
    auth_service = AuthenticationService(db)
    user_mgmt = UserManagementService(db)
    
    # 1. Create User via UserManagementService
    username = "split_test_user"
    password = "ComplexPassword123!"
    email = "split@example.com"
    
    user_in = UserCreate(
        username=username,
        password=password,
        email=email,
        full_name="Split Test User",
        role="staff"
    )
    
    user = user_mgmt.create_user(user_in)
    assert user.id is not None
    assert user.username == username
    
    # 2. Authenticate via AuthenticationService
    authenticated_user = auth_service.authenticate_user(username, password)
    assert authenticated_user is not None
    assert authenticated_user.id == user.id
    
    # 3. Fail Authentication with wrong password
    failed_user = auth_service.authenticate_user(username, "WrongPass")
    assert failed_user is None
    
    # 4. Cleanup
    # user_mgmt.delete_user (if it existed) or just rely on test db rollback
    # For now ensuring it runs without error is key
