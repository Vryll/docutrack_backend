from django.http import HttpRequest
from ninja import Router, Form, Query, File
from typing import List
from .models import *
from django.contrib.auth import get_user_model
from django.forms.models import model_to_dict
from .schema import *
from .forms import *
from django.contrib.auth.hashers import make_password
from ninja.security import HttpBasicAuth, HttpBearer
from django.contrib.auth import authenticate, login, logout
import jwt
from django.conf import settings
import datetime
from django.core.files.storage import FileSystemStorage
from django.shortcuts import get_object_or_404
from ninja.files import UploadedFile
from django.core.files.storage import default_storage
from django.utils.text import get_valid_filename
from django.db import transaction
from django.core.files.base import ContentFile
from django.contrib.auth import authenticate
from django.http import JsonResponse
import base64
import io, re
from uuid import uuid4
import json 
from ninja.errors import HttpError

User = get_user_model()

router = Router()

#AUTHENTICATION TOKEN
class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        try:
            JWT_SIGNING_KEY = getattr(settings, "JWT_SIGNING_KEY", None)
            payload = jwt.decode(token, JWT_SIGNING_KEY, algorithms=["HS256"])
            username: str = payload.get("username")

            if username is None:
                return None
        except jwt.PyJWTError as e:
            return None
        
        return username

#END POINTS FOR DISPLAYING DATA
@router.get('/getRole/all/', response=List[RoleSchema])
def list_roles(request):
    return Role.objects.all()

@router.get('/getStaffPosition/all', response=List[StaffPositionSchema])
def list_StaffPosition(request):
    return StaffPosition.objects.all()


@router.get('getOfficeList/all/', response=List[OfficeSchema])
def list_Offices(request):
    return Office.objects.all()

#all data
@router.get('/getAdminData/all')
def list_admin_data(request):
    admin_data_instances = Admin_Data.objects.all()

    admin_data_list = []
    for admin_data_instance in admin_data_instances:
        office_list = admin_data_instance.office_name.office_list if admin_data_instance.office_name else None

        user_instance = get_object_or_404(User, id=admin_data_instance.user.id) if admin_data_instance.user else None

        admin_data = {
            "id": admin_data_instance.id,
            "admin_logo": admin_data_instance.admin_logo.url if admin_data_instance.admin_logo else None,
            "office_name_id": admin_data_instance.office_name_id,
            "office_name": office_list,
            "user_id": admin_data_instance.user.id if admin_data_instance.user else None,
            "email": user_instance.email if user_instance else None,
            
        }
        admin_data_list.append(admin_data)

    return {"admin_data":admin_data_list}


    

@router.get('/getStaffData/all/', response=List[Staff_DataSchema])
def list_userData(request):
    return Staff_Data.objects.all()

@router.get('/getUserAdmin/{adminId}')
def get_combined_data(request, id:int = Query(...)):
    admin_data = Admin_Data.objects.filter(user__id=id).first()
    
    if not admin_data:
        return None
    
    user_data = {
        "id": admin_data.id,
        "username": admin_data.user.username,
        "jwt_token": admin_data.user.jwt_token,
        "office_name": admin_data.office_name,
        "admin_id": admin_data.admin_id,
        "role": admin_data.user.role.role_title
    }


#FETCHING ADMIN
@router.get('/getAdminDetails/{adminId}')
def GetAdminDetails(request, adminId:int):
    admin_details_instance = Admin_Data.objects.get(user_id = adminId)
    user_id = admin_details_instance.user_id
    user_instance = User.objects.get(id = user_id)

    user_data = {
        "email": user_instance.email,
    }

    admin_data = {
        "id": admin_details_instance.id,
        "admin_logo":admin_details_instance.admin_logo.url,
        "admin_overview": admin_details_instance.admin_overview,
        "office_name": admin_details_instance.office_name.office_list,
        "user_id": admin_details_instance.user_id
    }
    return {"user": user_data, "admin_data":admin_data}

#FETCH SUPERADMIN
@router.get('/getSuperadminDetails/{userId}')
def GetSuperadminDetails(request, userId: int):
    try:
        superadmin_details_instance = Superadmin_Data.objects.get(user_id=userId)
    except Superadmin_Data.DoesNotExist:
         
        return {"error": "Superadmin Data not found for the given user ID."}

    user_id = superadmin_details_instance.user_id
    user_instance = User.objects.get(id=user_id)    

    user_data = {
        "userId":user_instance.id,
        "email": user_instance.email,
        "password": user_instance.password
    }

    superadmin_data = {
        "id": superadmin_details_instance.id,
        "superadmin_name": superadmin_details_instance.superadmin_name,
        "superadmin_image": superadmin_details_instance.superadmin_image.url,
        "user_id": superadmin_details_instance.user_id,
    }
    return {"user": user_data, "superadmin_data": superadmin_data}


@router.get('/getClerkDetails/{userId}')
def GetClerkDetails(request, userId:int):
    clerk_data_instance =Staff_Data.objects.get(user_id = userId)

    user_id = clerk_data_instance.user_id
    user_instance = User.objects.get(id = user_id)

    user_data = {
        "email":user_instance.email,
        "first_name":user_instance.first_name,
        "last_name":user_instance.last_name,
    }

    clerk_data = {
        "user_image_profile":clerk_data_instance.user_image_profile.url
    }

    return{"user": user_data, "clerk_data":clerk_data}


@router.get('/admin_account_counter')
def admin_account_counter(request):
   
    admin_data_count = Admin_Data.objects.count()

 
    return  admin_data_count



#CREATE SUPERADMIN
@router.post('/create_superadmin')
def Create_Admin(request, form: CreateSuperAdminSchema = Form(...)):
    
 
    # existing_user = User.objects.filter(username=form.username).first()
    # if existing_user:
    #     return {"error": "A user with this username already exists!"}
    
  
    if form.password != form.confirm_password:
        return {"error": "Passwords do not match!"}

    user = User.objects.create(
        username=form.username,
        password=make_password(form.password),
        role=Role.objects.get(role_title=form.role)
    )
    
    payload = {
        "user_id": user.id,
        "username": user.username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    
    JWT_SIGNING_KEY = getattr(settings, "JWT_SIGNING_KEY", None)
    encoded_token = jwt.encode(payload, JWT_SIGNING_KEY, algorithm="HS256")
    
    user.jwt_token = encoded_token
    user.save()
    
    print(form.dict())

    return {"success": "Superadmin created successfully!", "token": encoded_token}


#ENDPOINTS FOR CREATING USER ACCOUNTS
@router.post('/create_admin')
def Create_Admin(request, form: CreateAdminSchema = Form(...)):
    
    
    existing_user = User.objects.filter(username=form.username).first()
    if existing_user:
        return {"error": "A user with this username already exists!"}
    
    
    if form.password != form.confirm_password:
        return {"error": "Passwords do not match!"}
    office_name = form.office_name

    office_name_instance = Office.objects.get(office_list=office_name)

    user = User.objects.create(
        email = form.email,
        username= form.email,
        password=make_password(form.password),
        role=Role.objects.get(role_title=form.role)
    )
  

    image_data = base64.b64decode(form.admin_logo)
    unique_admin_logo_name = f"admin_logo_{uuid4().hex}.png"
    file_content = ContentFile(image_data, name=unique_admin_logo_name)
    
    admin_data_instance = Admin_Data.objects.create(
   
    user=user,
    admin_logo=file_content
    )
    admin_data_instance.office_name = office_name_instance
    admin_data_instance.save()
    
    payload = {
        "user_id": user.id,
        "username": user.username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    
    JWT_SIGNING_KEY = getattr(settings, "JWT_SIGNING_KEY", None)
    encoded_token = jwt.encode(payload, JWT_SIGNING_KEY, algorithm="HS256")
    
    user.jwt_token = encoded_token
    user.save()
    
    print(form.dict())

    return {"success": "Admin created successfully!", "token": encoded_token}


@router.post('/create_staff')
def Create_Staff(request, form: CreateStaffSchema = Form(...)):
    if not form.email.endswith('@wmsu.edu.ph'):
        return {'error': 'Invalid username format. Please use a valid @wmsu.edu.ph email.'}

   
    # existing_user = User.objects.filter(username=form.username).first()
    # if existing_user:
    #     return {"error": "A user with this username already exists!"}

   
    if form.password != form.confirm_password:
        return {"error": "Passwords do not match!"}

    
    if not re.match(r'^(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{1,16}$', form.password):
        return {"error": "Password must contain at least one capitalized character, one number, and be up to 16 characters long."}

  
    user = User.objects.create(
        email=form.email,
        username=form.email,
        password=make_password(form.password),
        role=Role.objects.get(role_title=form.role)
    )

    
    Staff_Data.objects.create(
        user=user
    )

    
    payload = {
        "user_id": user.id,
        "username": user.username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }

    JWT_SIGNING_KEY = getattr(settings, "JWT_SIGNING_KEY", None)
    encoded_token = jwt.encode(payload, JWT_SIGNING_KEY, algorithm="HS256")

    user.jwt_token = encoded_token
    user.save()

    return {"success": "Staff created successfully!", "user_id": user.id, "token": encoded_token}


#ENDPOINTS FOR UPDATING USER ACCOUNTS
@router.post('/edit_staff_Details/{userId}')
def Edit_Staff_User(request, userId: int, form: UpdateUserStaffData):
    staff_instance = get_object_or_404(Staff_Data, user_id=userId)
    user_instance = staff_instance.user
    print(user_instance)
    print(form)
    
    for attr, value in form.dict().items():
        if attr == 'first_name':
            user_instance.first_name = value
        elif attr == 'middle_name':
            user_instance.middle_name = value
        elif attr == 'last_name':
            user_instance.last_name = value

   
    print(f'First Name: {user_instance.first_name}')
    print(f'Middle Name: {user_instance.middle_name}')
    print(f'Last Name: {user_instance.last_name}')


    user_instance.save()  

 
    admin_office_names = form.admin_office
    staff_position_names = form.staff_position
    
    if admin_office_names:
        office_instance = Office.objects.get(office_list=admin_office_names)
        staff_instance.admin_office = office_instance

    if staff_position_names:
        staff_position_instance = StaffPosition.objects.get(position_name=staff_position_names)
        staff_instance.staff_position = staff_position_instance

    if form.user_image_profile:
        image_data = base64.b64decode(form.user_image_profile)
        unique_user_image_name = f"user_image_{uuid4().hex}.png"
        file_content = ContentFile(image_data, name=unique_user_image_name)
        staff_instance.user_image_profile.save(unique_user_image_name, file_content, save=True)

    staff_instance.save()

    user = User.objects.get(id=userId)
    user_jwtToken = user.jwt_token
    print(user_jwtToken)


    return {"success": True, "jwt_token": user_jwtToken}


#ENDPOINTS FOR UPDATING THE ADMIN DATA
@router.post('/edit_admin_Details/{userId}')
def EditAdminDetails(request, userId: int, form: UpdateAdminDataSchema = Form(...)):
    user_instance = User.objects.get(id=userId)
    admin_data_instance = Admin_Data.objects.get(user_id=user_instance.id)

    for attr, value in form.dict().items():
        if attr == "email" and value:
            user_instance.email = value
            user_instance.username = value
            print(f"Email: {value}")

        elif attr == "password" and value:
            user_instance.password = make_password(value)
            print(f"password: {value}")

        if attr == "admin_overview" and value:
            admin_data_instance.admin_overview = value
            print(f"Admin Overview: {value}")

        if "admin_logo" in form.dict() and form.admin_logo:
            image_data = base64.b64decode(form.admin_logo)
            print(image_data)
            unique_admin_logo_name = f"admin_logo_{uuid4().hex}.png"
            file_content = ContentFile(image_data, name=unique_admin_logo_name)
            admin_data_instance.admin_logo.save(unique_admin_logo_name, file_content, save=True)
            print(f"Admin Logo: {unique_admin_logo_name}")

    user_instance.save()
    admin_data_instance.save()

    return {"success": True}

#ENDPOINTS FOR UPDATING THE SUPERADMIN DATA
@router.post('/edit_superadmin_data/{userId}')
def EditSuperadminAdmin(request, userId: int, form: UpdateSuperAdminDataSchema = Form(...)):
    user_instance = User.objects.get(id=userId)
    
    try:
        superadmin_data_instance = Superadmin_Data.objects.get(user_id=user_instance.id)
    except Superadmin_Data.DoesNotExist:
 
        superadmin_data_instance = Superadmin_Data(user=user_instance, superadmin_name=form.superadmin_name)

    for attr, value in form.dict().items():
        if attr == "email" and value:
            user_instance.email = value
            user_instance.username = value  

        elif attr == "password" and value:
            user_instance.password = make_password(value)

        if attr == "superadmin_name" and value:
            superadmin_data_instance.superadmin_name = value

    if "superadmin_image" in form.dict() and form.superadmin_image:
        image_data = base64.b64decode(form.superadmin_image)
        print(image_data)
        unique_superadmin_logo_name = f"superadmin_img_{uuid4().hex}.png"
        file_content = ContentFile(image_data, name=unique_superadmin_logo_name)
        superadmin_data_instance.superadmin_image.save(unique_superadmin_logo_name, file_content, save=True)

    
    user_instance.save()
    superadmin_data_instance.save()

    return {"success": True}

#ENDPOINT FOR FORGET PASSWORD
@router.post("/forget_password")
def update_user_password(request, form: EmailConfirmationSchema = Form(...)):
    try:
        user_instance = get_object_or_404(User, email=form.email)
        user_email = user_instance.email

        if form.email == user_email:
            return {"message": "Email matched", "email": user_email}
        else:
            return {"message": "Email does not match"}

    except HttpError as e:
     
        return {"message": "Email does not exist", "error": str(e)}
    
@router.post("/update_password/{email}")
def update_password(request, email: str, form: UpdatePasswordSchema = Form(...)):
        print(email)
        user_instance = User.objects.get(email=email)

        if form.password != form.confirm_password:
         
            return{"password does not matched"}

        user_instance.set_password(form.password)
        user_instance.save()

        return {"message": "Password updated successfully"}








#ENDPOINTS FOR CREATING GUEST INFORMATION
@router.post('/create_guest_details')
def create_guest_details(request, form: CreateGuestSchema = Form(...)):

 
    role_instance = Role.objects.get(role_title=form.role)
    office_instance = Office.objects.get(office_list=form.guest_admin_office)

  
    user = User.objects.create(
        email=form.email,
        first_name=form.first_name,
        middle_name=form.middle_name,
        last_name=form.last_name,
        username=form.email,  
        role=role_instance,  
    )


    guest_data = Guest_Data.objects.create(
        user=user,
        # employee_id_number=form.employee_id_number,
        guest_admin_office=office_instance,
    )


    response_data = {
        "success": "Guest details created successfully!",
        "guest_details": {
            "email": user.email,
            "role": user.role.role_title,
            "first_name": user.first_name,
            "middle_name": user.middle_name,
            "last_name": user.last_name,
            # "employee_id_number": guest_data.employee_id_number,
            "guest_admin_office": guest_data.guest_admin_office.office_list,
        }
    }
    return 200, response_data




#ENDPOINTS FOR DELETE OF USER ACCOUNTS

#ENDPOINTS FOR SIGN IN OF ACCOUNTS
@router.post('/Signin')
def Signin(request, form: SigninFormSchema = Form(...)):
   
    if not form.username.endswith('@wmsu.edu.ph'):
        return {'error': 'Invalid username format. Please use a valid @wmsu.edu.ph email.'}

    user = authenticate(username=form.username, password=form.password)
    print(form)

    if user is not None:
      
        jwt_token = user.jwt_token
        role = user.role.role_title
        return {"message": "Login successful", "role": role, "jwt_token": jwt_token}
    else:
        return {"message": "Login failed"}


    

#ENDPOINT FOR DELETION OF DATA
@router.delete("/deleting_admin_account/admin_id={adminId}")
def DeletingAdminAccount(request, adminId: int):

    admin_data_instance = get_object_or_404(Admin_Data, id=adminId)
    
    admin_user_id = admin_data_instance.user_id
    user_instance = get_object_or_404(User, id=admin_user_id)

  
    admin_data_instance.delete()
    user_instance.delete()

    return {"detail": "Admin account deleted successfully"}
    
@router.post('/getJwtTokenNClerkDetails')
def GetJWTToken(request):
  
    data = json.loads(request.body)
    
    
    user_token = data.get("jwt_token")
    
    
    user_instance = User.objects.get(jwt_token=user_token)
    user_id = user_instance.id

    clerk_data_instance = Staff_Data.objects.get(user_id = user_id)
    clerk_admin_office = clerk_data_instance.admin_office

    admin_data_instance = Admin_Data.objects.get(office_name = clerk_admin_office)

    user_data = {
        "userId":user_instance.id,
        "email":user_instance.email,
        "first_name":user_instance.first_name,
        "last_name":user_instance.last_name,
    }

    clerk_data = {
        "user_image_profile":clerk_data_instance.user_image_profile.url,
        "admin_office":clerk_data_instance.admin_office.office_list,
        "admin_logo":admin_data_instance.admin_logo.url,
        "office_name":admin_data_instance.office_name.office_list,
        "staff_positon": clerk_data_instance.staff_position.position_name
    }

    return{"user": user_data, "clerk_data":clerk_data}



@router.get('/getClerk_details/{userId}')
def GetClerk_details(request,userId: int ):
    

    user_instance = User.objects.get(id=userId)
    user_id = user_instance.id

    clerk_data_instance = Staff_Data.objects.get(user_id = user_id)
    clerk_admin_office = clerk_data_instance.admin_office

    admin_data_instance = Admin_Data.objects.get(office_name = clerk_admin_office)

    user_data = {
        "email":user_instance.email,
        "first_name":user_instance.first_name,
        "last_name":user_instance.last_name,
        "jwt_token":user_instance.jwt_token,
    }

    clerk_data = {
        "user_image_profile":clerk_data_instance.user_image_profile.url,
        "admin_office":clerk_data_instance.admin_office.office_list,
        "admin_logo":admin_data_instance.admin_logo.url,
        "office_name":admin_data_instance.office_name.office_list,
        "staff_positon": clerk_data_instance.staff_position.position_name
    }

    return{"user": user_data, "clerk_data":clerk_data}


            
    
