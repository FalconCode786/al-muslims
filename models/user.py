from flask_login import UserMixin
from dataclasses import dataclass
from typing import Optional

@dataclass
class User(UserMixin):
    id: str
    email: str
    full_name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    cnic: Optional[str] = None
    disco_region: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False
    
    def get_id(self):
        return str(self.id)
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_anonymous(self):
        return False