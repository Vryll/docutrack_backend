from ninja import Router, Form, File
from .models import *
from .forms import *
import io
from django.core.files import File as django_file
from user_accounts.models import Admin_Data
from ninja.files import UploadedFile
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.base import ContentFile
import base64
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http import Http404
from django.core import serializers
from user_accounts.models import *
from document.models import *
import json
from django.http import JsonResponse
from json.decoder import JSONDecodeError
from django.shortcuts import get_object_or_404

from uuid import uuid4
import time
from ninja.errors import HttpError
from django.shortcuts import get_list_or_404
from django.http import JsonResponse
from .forms import *
from docx2pdf import convert



router = Router()

@router.post('/getClerkUserName')
def GetClerkUserName(request):

    data = json.loads(request.body)
    
   
    user_token = data.get("jwt_token")

    user_instance = User.objects.get(jwt_token = user_token)
    clerk_user_name = {
        "first_name":user_instance.first_name,
        "middle_name":user_instance.middle_name,
        "last_name":user_instance.last_name,
    }
    return {"clerk_user_name": clerk_user_name}

@router.get('/getUserClerk/{userId}')
def GetUserClerk(request, userId:int):
    user_instance = get_object_or_404(User, id=userId)
    
    staff_user ={
        "first_name":user_instance.first_name,
        "middle_name":user_instance.middle_name,
        "last_name":user_instance.last_name
    }   

    return {"staff_user": staff_user}

@router.post('/createworkspace/user_id={userId}')
def CreateWorkSpace(request, userId:int, form: WorkspaceFormSchema = Form(...), workspace_docu_file: UploadedFile = File(...)):
    

    if not workspace_docu_file.name.endswith('.pdf'):
        return {"error": "Only PDF files are allowed for upload."}

   
    workspace_docu = Workspace_Docu_Details(
        workspace_docu_type=Document_Type.objects.get(docu_type=form.workspace_docu_type),
        workspace_docu_status=Workspace_Docu_Status.objects.get(status_list=form.workspace_docu_status),
        workspace_docu_title=form.workspace_docu_title,
        user=User.objects.get(id = userId),
        workspace_docu_file=workspace_docu_file
    )

  
    workspace_docu.save()
    
  
    return {"message": "Workspace created successfully"}

@router.get('/getWorkspaceDocumentDetailsDashboard/userID={userId}')
def GetWorkspaceDocumentDetailsDashboard(request, userId: int):
    try:
        admin_data_instance = Admin_Data.objects.get(user_id=userId)
    except Admin_Data.DoesNotExist:
        return JsonResponse({"error": "Admin data not found for the given user ID"}, status=404)

    admin_office_name = admin_data_instance.office_name
    print(admin_office_name)

    staff_data_instances = Staff_Data.objects.filter(admin_office=admin_office_name)

    if not staff_data_instances.exists():
        return JsonResponse({"error": "No matching staff data found!"}, status=404)

    workspace_details_list = []

    for staff_data_instance in staff_data_instances:
        staff_user_id = staff_data_instance.user_id

        try:
            staff_user_instance = User.objects.get(id=staff_user_id)
        except User.DoesNotExist:
            continue  

        workspace_details_instances = Workspace_Docu_Details.objects.filter(user_id=staff_user_id)

        for workspace_details_instance in workspace_details_instances:
            workspace_details_list.append({
                "id": workspace_details_instance.id,
                "workspace_docu_type": workspace_details_instance.workspace_docu_type,
                "workspace_docu_title": workspace_details_instance.workspace_docu_title,
                "upload_dateNtime": workspace_details_instance.upload_dateNtime,
                "first_name": staff_user_instance.first_name,
                "middle_name": staff_user_instance.middle_name,
                "last_name": staff_user_instance.last_name,
                "workspace_docu_file": workspace_details_instance.workspace_docu_file.url,
            })

    if workspace_details_list:
        return JsonResponse(workspace_details_list, safe=False)
    else:
        return JsonResponse({"error": "No matching workspace details found!"}, status=404)
    
#ENDPOINT FOR GETCHING WORKSPACE DOCUMENT FILE
@router.get('/getWorkspacePreviewDocu/{docuId}')
def GetWorkspacePreviewDocu(request, docuId: int):
    try:
        workspace_docu_details_instance = Workspace_Docu_Details.objects.get(id=docuId)

        workspace_docu_detail = {
            "id": workspace_docu_details_instance.id,
            "workspace_docu_file": workspace_docu_details_instance.workspace_docu_file.url,
            "workspace_docu_comment": workspace_docu_details_instance.workspace_docu_comment,
        }

        return JsonResponse(workspace_docu_detail)
    except Workspace_Docu_Details.DoesNotExist:
        raise Http404("Workspace Document_Details does not exist")
    
#ENDPOINT FOR UPDATING WORKSPACE DOCUMENT DETAILS
@router.post('/updateWorkspaceDocuDetail/docuID={docuId}')
def update_workspace_docu_detail(request, docuId: int, form: UpdateWorkspaceDocuDetailSchema = Form(...)):
    workspace_docu_details = Workspace_Docu_Details.objects.get(id=docuId)

    workspace_docu_details.workspace_docu_comment = form.workspace_docu_comment
    workspace_docu_details.save()

    return {"message": "The Workspace Docu Comment has been successfully saved!"}


#ENDPOINT IN UPDATING THE WORKSPACE DOCUMENT STATUS
@router.post('/UpdatingWorkspaceDocuStatus/docuID={docuId}')
def GetWorkspaceDocuStatus(request, docuId:int):
    data = json.loads(request.body)
    status = data.get('workspace_docu_status')
    print(status)


    status_instance = Workspace_Docu_Status.objects.get(status_list=status)

    workspace_docu_details_instance = get_object_or_404(Workspace_Docu_Details, id=docuId)
    workspace_docu_details_instance.workspace_docu_status = status_instance
    workspace_docu_details_instance.save()
    return {"message": "The Workspace Docu Status has been successfully Updated!"}


#ENDPOINT IN FETCHING ALL OF THE WORKSPACE DOCUMENTS DETAILS
@router.get('/getWorkspaceDocuments/all')
def GetWorkspaceDocuments(request):
    workspace_documents_instances = Workspace_Docu_Details.objects.all()

    
    workspace_document_data = []
    for instance in workspace_documents_instances:
        workspace_docu_status = instance.workspace_docu_status
        status_list = workspace_docu_status.status_list if workspace_docu_status else None

        workspace_document_data.append({
            "id":instance.id,
            "workspace_docu_type": instance.workspace_docu_type,
            "workspace_docu_title": instance.workspace_docu_title,
            "first_name": instance.first_name,
            "middle_name": instance.middle_name,
            "last_name": instance.last_name,
            "workspace_docu_file": instance.workspace_docu_file.url if instance.workspace_docu_file else None,
            "upload_dateNtime": instance.upload_dateNtime,
            "workspace_docu_comment": instance.workspace_docu_comment,
            "workspace_docu_status": status_list,
        })

    return {"workspace_document_data": workspace_document_data}

#ENDPOINT IN FETCHING WORKSPACE DOCUMENT DETAILS BASED ON THE USER CLERK
@router.get('/getWorkspaceDocuDetail/clerk_user={userId}')
def GetWorkspaceDocuDetail(request, userId: int):
      
        workspace_docu_details = Workspace_Docu_Details.objects.filter(user_id=userId)

        docu_details_count = workspace_docu_details.count()

 
        workspace_document_data = []
        for instance in workspace_docu_details:
        
            user_instance = instance.user

         
            staff_data_instance = Staff_Data.objects.get(user=user_instance)

            workspace_document_data.append({
                "id": instance.id,
                "workspace_docu_type": instance.workspace_docu_type,
                "workspace_docu_title": instance.workspace_docu_title,
                "user_first_name": user_instance.first_name if user_instance else None,
                "user_middle_name": user_instance.middle_name if user_instance else None,
                "user_last_name": user_instance.last_name if user_instance else None,
                "staff_office_name": staff_data_instance.admin_office.office_list if staff_data_instance.admin_office else None,
                "upload_dateNtime": instance.upload_dateNtime,
                "workspace_docu_comment": instance.workspace_docu_comment,
                "workspace_docu_status": instance.workspace_docu_status.status_list if instance.workspace_docu_status else None,
                "is_deleted":instance.is_deleted
            })

            response_data = {
                "docu_details_count": docu_details_count,
                "workspace_document_data": workspace_document_data
            }

        return response_data

#ENDPOINT FOR FETCHING ARCHIVED WORKSPACE DOCUMENT DETAILS
@router.get('/getArchived_workspace_docu_details/user_id={userId}')
def GetArchivedWorkspaceDocuDetails(request, userId: int):
    
 
    workspace_docu_details_instance = Workspace_Docu_Details.deleted_objects.filter(
        user_id=userId, is_deleted=True
    )
    
    archived_workspace_docu_count = workspace_docu_details_instance.count()

    
    results = []

    for instance in workspace_docu_details_instance:
        result = {
            "workspace_docu_id": instance.id,
            "workspace_docu_type": instance.workspace_docu_type,
            "workspace_docu_title": instance.workspace_docu_title,
            "workspace_docu_status": instance.workspace_docu_status.status_list if instance.workspace_docu_status else None,
            "upload_dateNtime": instance.upload_dateNtime,
            "is_deleted": instance.is_deleted,
            "deleted_at": instance.deleted_at,
        }
        results.append(result)

    archived_workspace_docu_data = {
        "archived_workspace_docu_count": archived_workspace_docu_count,
        "workspace_docu_details": results,
    }

    return archived_workspace_docu_data



#ENDPOINT FOR COUNTING OF WORKSPACE DOCUMENTS
@router.get('/countWorkspaceDocu/clerk_user={userId}')
def CountWorkspaceDocu(request, userId: int):

    workspace_docu_details_count = Workspace_Docu_Details.objects.filter(user_id=userId).count()

    return {"docuCount": workspace_docu_details_count}


@router.get('/getOverallWorkspaceDocuDetailsCount/{userId}')
def GetOverallWorkspaceDocuDetailsCount(request, userId: int):
    try:
        admin_data_instance = Admin_Data.objects.get(user_id=userId)
    except Admin_Data.DoesNotExist:
        return JsonResponse({"error": "Admin data not found for the given user ID"}, status=404)

    admin_office_name = admin_data_instance.office_name
    print(admin_office_name)

    staff_data_instances = Staff_Data.objects.filter(admin_office=admin_office_name)

    if not staff_data_instances.exists():
        return JsonResponse({"error": "No matching staff data found!"}, status=404)

    overall_count = 0

    for staff_data_instance in staff_data_instances:
        staff_user_id = staff_data_instance.user_id

        try:
            staff_user_instance = User.objects.get(id=staff_user_id)
        except User.DoesNotExist:
            continue 

        staff_first_name = staff_user_instance.first_name
        print(staff_first_name)

        workspace_details_count = Workspace_Docu_Details.objects.filter(first_name=staff_first_name).count()
        overall_count += workspace_details_count

    return JsonResponse({"overall_count": overall_count})


#ENDPOINT FOR SOFT DELETION OF WORKSPACE DOCUMENT
@router.delete("deleting_workspace_document_details/docuId={docuId}")
def DeleteWorkspaceDocumentDetails(request, docuId:int):
    workspace_docu_details = Workspace_Docu_Details.objects.get(id = docuId)

    if workspace_docu_details is not None:
        workspace_docu_details.delete()
        return {'message': f'The document detail with ID {docuId} was successfully deleted'}
    else:
        return {'message': f'The document detail with ID {docuId} does not exist'}
    

#ENDPOINT FOR RESTORING OF WORKSPACE DOCUMENT
@router.get("restore_workspace_document_details/docuId={docuId}")
def RestoreWorkspaceDocumentDetails(request, docuId:int):
    workspace_docu_details = Workspace_Docu_Details.deleted_objects.get(id = docuId)

    if workspace_docu_details is not None:
        workspace_docu_details.restore()
        return {'message': f'The document detail with ID {docuId} was successfully restored'}
    else:
        return {'message': f'The document detail with ID {docuId} does not exist'}
    

#ENDPOINT FOR HARD DELETE OF WORKSPACE DOCUMENT
@router.delete("hard_delete_workspace_document_details/docuId={docuId}")
def HardDeleteWorkspaceDocumentDetails(request, docuId:int):
    workspace_docu_details = Workspace_Docu_Details.deleted_objects.get(id = docuId)

    if workspace_docu_details is not None:
        workspace_docu_details.hard_delete()
        return {'message': f'The document detail with ID {docuId} was successfully hard deleted'}
    else:
        return {'message': f'The document detail with ID {docuId} does not exist'}






        


