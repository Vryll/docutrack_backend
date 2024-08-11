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


router = Router()
    
@router.post('/docu_recieve_record/document_detail={docuId}')
def DocuRecipient(request, docuId: int, form:CreateRecieveRecordSchema = Form(...)):
    try:
        document_details = get_object_or_404(Document_Details, id=docuId)
        
        data = json.loads(request.body)
        user_token = data.get("jwt_token")
        print(user_token)
        status_value = data.get("status_value")
        print(status_value)

        try:
            docu_status = Document_Status.objects.get(docu_status=status_value)
            recipient_status = Recipient_Status.objects.get(receiving_status = status_value)
            document_details.status = docu_status
            document_details.save()
        except Document_Status.DoesNotExist:
            return JsonResponse({"message": "Document status not found"}, status=404)

        try:
            user = User.objects.get(jwt_token=user_token)
        except User.DoesNotExist:
            return JsonResponse({"message": "User not found"}, status=404)
       
        recieve_record = Receive_Record(
            docu_details=document_details,
            user_staff=user,
            recipient_status=recipient_status,
        )
        recieve_record.save()
        
        return JsonResponse({"message": "Receive_Record created successfully!"}, status=201)
    except Exception as e:
        return JsonResponse({"message": str(e)}, status=400)

    

@router.post('/guest_docu_recieve_record/document_detail={docuId}')
def DocuRecipient(request, docuId: int, form:CreateRecieveRecordSchema = Form(...)):
    try:
    
        document_details = get_object_or_404(Document_Details, id=docuId)
        
       
        data = json.loads(request.body)
        
      
        guest_email = data.get("email")
        
        try:
           
            user = User.objects.get(username=guest_email)
        except User.DoesNotExist:
            return JsonResponse({"message": "User not found"}, status=404)
        
       
      
        imgstr = data.get('employee_id_image')
        image_data = base64.b64decode(imgstr)
        image_unique_filename = f"employeeID_{int(time.time())}.png"
        image_buffer = io.BytesIO(image_data)
        image_file = django_file(image_buffer, name=image_unique_filename)

        selfie_imgstr = data.get('user_selfie_image')
        selfie_image_data = base64.b64decode(selfie_imgstr)
        selfie_image_unique_filename = f"user_selfie_img_{int(time.time())}.png"
        selfie_image_buffer = io.BytesIO(selfie_image_data)
        selfie_image_file = django_file(selfie_image_buffer, name=selfie_image_unique_filename)
        
       
        recieve_record = Receive_Record(
            docu_details=document_details,
            user_staff=user,
            recipient_status = form.recipient_status,
            employee_id_image = image_file,
            user_selfie_image = selfie_image_file
        )
        recieve_record.save()
        
        return JsonResponse({"message": "Recieve_Record created successfully!"}, status=201)
    except Exception as e:
        return JsonResponse({"message": str(e)}, status=400)


@router.post('/getJwtToken')
def GetJWTToken(request):
    try:  
       
        data = json.loads(request.body)
        
        
        user_token = data.get("jwt_token")
        
        try:
            
            user = User.objects.get(jwt_token=user_token)

           
            user_id = user.id
            
           
            return {"user_id": user_id}
            
        except User.DoesNotExist:
            return JsonResponse({"message": "User not found"}, status=404)
       
    except Exception as e:
        return JsonResponse({"message": str(e)}, status=400)
    

#fetching of data for outgoing
@router.get('/getDocumentDetailsDashboard/UserID={userId}')
def GetDocumentDetailsDashboard(request, userId: int):
    user_instance = get_object_or_404(User, id=userId)
    user_id = user_instance.id

    admin_data_instance = Admin_Data.objects.get(user_id = user_id)
    admin_office_name = admin_data_instance.office_name

    try:
        office_instance = Office.objects.get(office_list=admin_office_name)
    except Office.DoesNotExist:
        return {"error": "No matching data found"}

    office_name = office_instance.office_list

    document_details_instances = Document_Details.objects.filter(docu_sender=office_name)

    if document_details_instances:
        docu_details_list = []
        for document_details_instance in document_details_instances:
            docu_details_list.append({
                "id": document_details_instance.id, 
                "memorandum_number":document_details_instance.memorandum_number,
                "docu_type": document_details_instance.type.docu_type,
                "docu_title": document_details_instance.docu_title,
                "docu_dateNtime_released": document_details_instance.docu_dateNtime_released,
                "docu_recipient": [recipient.office_list for recipient in document_details_instance.docu_recipient.all()] if document_details_instance.docu_recipient.exists() else [],
                "status": document_details_instance.status.docu_status if document_details_instance.status is not None else None,
                "is_deleted": document_details_instance.is_deleted
            })
        return docu_details_list
        
    for docu_details in docu_details_list:
        print(docu_details)
        
    else:
        return {"error": "No matching data found"}

    
#fetching of data for recieved
@router.get('/getRecievedDocumentDetailsDashboard/UserID={userId}')
def RecievedDocumentDetailsDashboard(request, userId:int):
    user_instance = get_object_or_404(User, id=userId)
    user_id = user_instance.id

    admin_data_instance = Admin_Data.objects.get(user_id = user_id)
    admin_office_name = admin_data_instance.office_name
    print(userId)
    try:
        office_instance = Office.objects.get(office_list=admin_office_name)
        print(office_instance)
    except Admin_Data.DoesNotExist:
        return {"error": "No matching data found"}

    office_id = office_instance.id

    document_details_instances = Document_Details.objects.filter(docu_recipient=office_id)

    if document_details_instances:
        docu_details_list = []
        for document_details_instance in document_details_instances:
            docu_details_list.append({
                "id": document_details_instance.id,
                "memorandum_number":document_details_instance.memorandum_number,
                "docu_type": document_details_instance.type.docu_type,
                "docu_title": document_details_instance.docu_title,
                "docu_dateNtime_released": document_details_instance.docu_dateNtime_released,
                "docu_sender": document_details_instance.docu_sender,
                "status": document_details_instance.status.docu_status if document_details_instance.status is not None else None,
                "is_deleted": document_details_instance.is_deleted
            })
        return docu_details_list
     
    for docu_details in docu_details_list:
        print(docu_details)
    
    else:
        return {"error": "No matching data found"}

#GET REQUEST DOCUMENT DASHBOARD
@router.get('/getRequestDocumentDetailsDashboard/user_id={userId}')
def GetRequestDocumentDetailsDashboard(request, userId: int):
    user_instance = get_object_or_404(User, id=userId)
    user_id = user_instance.id

    admin_data_instance = Admin_Data.objects.get(user_id=user_id)
    admin_office_name = admin_data_instance.office_name

    try:
        office_instance = Office.objects.get(office_list=admin_office_name)
    except Office.DoesNotExist:
        return {"error": "No matching data found"}

    office_name = office_instance.office_list

    forwarded_document_details_instances = Forward_Request_Document.objects.filter(forwarded_requested=office_name)
    requested_document_details_instances = Requested_Document.objects.filter(requested=office_name)

  
    merged_document_list = []

    for forwarded_doc in forwarded_document_details_instances:
        merged_document_list.append({
            "id": forwarded_doc.id,
            "status": forwarded_doc.forwarded_requested_docu_status.req_docu_status if forwarded_doc.forwarded_requested_docu_status else None,
            "requested": forwarded_doc.forwarded_requested,
            "docu_request_topic": forwarded_doc.forwarded_subject,
            "docu_request_recipient": forwarded_doc.forwarded_docu_request_recipient,
            "docu_request_deadline": forwarded_doc.forwarded_date_requested,
            "requested_docu_file": forwarded_doc.forwarded_requested_docu_file.url,
            "process_type": forwarded_doc.forwarded_process_type.process_type,
           
            "is_deleted": False, 
        })

    for requested_doc in requested_document_details_instances:
        merged_document_list.append({
            "id": requested_doc.id,
            "status": requested_doc.status.req_docu_status if requested_doc.status else None,
            "requested": requested_doc.requested,
            "docu_request_topic": requested_doc.docu_request_topic,
            "docu_request_recipient": requested_doc.docu_request_recipient,
            "docu_request_deadline": requested_doc.docu_request_deadline,
          
            "requested_docu_file":requested_doc.docu_request_file.url,
            "process_type": requested_doc.requested_process_type.process_type,
            "is_deleted": requested_doc.is_deleted,
        })

    print("Merged Document List:")
    for merged_doc in merged_document_list:
        print(merged_doc)

    return {"merged_document_list": merged_document_list}

    

#GET INCOMING REQUEST DOCUMENT DASHBOARD
@router.get('/getIncomingRequestDocumentDetailsDashboard/user_id={userId}')
def GetRequestDocumentDetailsDashboard(request, userId: int):
    user_instance = get_object_or_404(User, id=userId)
    user_id = user_instance.id
    print(user_id)

    admin_data_instance = Admin_Data.objects.get(user_id=user_id)
    admin_office_name = admin_data_instance.office_name
    print(admin_office_name)

    try:
        office_instance = Office.objects.get(office_list=admin_office_name)
    except Office.DoesNotExist:
        return {"error": "No matching data found"}

    office_name = office_instance.office_list

    requested_document_details_instances = Requested_Document.objects.filter(docu_request_recipient=office_name)
    forwarded_requested_document_instances = Forward_Request_Document.objects.filter(forwarded_docu_request_recipient=office_name)

    requestedDocument_list = []

    # Merge data from Requested_Document
    for requested_document_details_instance in requested_document_details_instances:
        requestedDocument_list.append({
            "id": requested_document_details_instance.id,
            "status": requested_document_details_instance.status.req_docu_status if requested_document_details_instance.status else None,
            "requested": requested_document_details_instance.requested,
            "docu_request_topic": requested_document_details_instance.docu_request_topic,
            "docu_request_recipient": requested_document_details_instance.docu_request_recipient,
            "docu_request_deadline": requested_document_details_instance.docu_request_deadline,
            "docu_request_comment": requested_document_details_instance.docu_request_comment,
            "docu_request_file": requested_document_details_instance.docu_request_file.url,
            "process_type": requested_document_details_instance.requested_process_type.process_type,
            "is_deleted": requested_document_details_instance.is_deleted
        })

    # Merge data from Forward_Request_Document
    for forwarded_document_instance in forwarded_requested_document_instances:
        requestedDocument_list.append({
            "id": forwarded_document_instance.requested_document.id,
            "status": forwarded_document_instance.forwarded_requested_docu_status.req_docu_status
                      if forwarded_document_instance.forwarded_requested_docu_status else None,
            "requested": forwarded_document_instance.forwarded_requested,
            "docu_request_topic": forwarded_document_instance.forwarded_subject,
            "docu_request_recipient": forwarded_document_instance.forwarded_docu_request_recipient,
            "docu_request_deadline": forwarded_document_instance.forwarded_date_requested,
            "docu_request_comment": "",  
            "docu_request_file": forwarded_document_instance.forwarded_requested_docu_file.url,
            "process_type": forwarded_document_instance.forwarded_process_type.process_type,
            "is_deleted": False, 
        })

    for reqDocu in requestedDocument_list:
        print(reqDocu)

    return requestedDocument_list

    
#GET MAIN DASHBOARD
@router.get('/getMain_dashboard/{userId}')
def GetMainDashboard(request, userId: int):
    user_instance = get_object_or_404(User, id=userId)
    user_id = user_instance.id

    admin_data_instance = Admin_Data.objects.get(user_id = user_id)
    admin_office_name = admin_data_instance.office_name
    try:
        office_instance = Office.objects.get(office_list=admin_office_name)
    except Office.DoesNotExist:
        return {"error": "No matching data found"}

    office_name = office_instance.office_list

    combined_data_list = []

    # Fetch data from Document_Details
    document_details_list = Document_Details.objects.filter(docu_sender=office_name)
    for document in document_details_list:
        docu_recipients = document.docu_recipient.all()
        docu_recipient_list = [recipient.office_list for recipient in docu_recipients]
        combined_data_list.append({
            "id": document.id,
            "memorandum_number": document.memorandum_number,
            "docu_type": document.type.docu_type if hasattr(document, 'type') else None,
            "docu_title": document.docu_title if hasattr(document, 'docu_title') else None,
            "docu_dateNtime_released": document.docu_dateNtime_released if hasattr(document, 'docu_dateNtime_released') else None,
            "docu_recipient": docu_recipient_list,
            "status": str(document.status.docu_status) if document.status is not None else None,
            "docu_source": "docu_details",
        })

    # Fetch data from Requested_Document
    request_document_list = Requested_Document.objects.filter(requested=office_name)
    for request_document in request_document_list:
        docu_recipient = request_document.docu_request_recipient
        combined_data_list.append({
            "id": request_document.id,
            "docu_type": request_document.type.docu_type if hasattr(request_document, 'type') else None,
            "docu_title": request_document.docu_request_topic if hasattr(request_document, 'docu_request_topic') else None,
            "docu_dateNtime_released": request_document.docu_request_deadline if hasattr(request_document, 'docu_request_deadline') else None,
            "docu_recipient": [docu_recipient],
            "docu_request_comment": request_document.docu_request_comment,
            "status": str(request_document.status) if request_document.status is not None else None,
            "docu_source": "requested_document",
        })

    main_dashboard_data = {
        "combined_data": combined_data_list
    }

    return main_dashboard_data






#GET SELECTE ITEM IN MAIN DASHBOARD
@router.get('/getSelectItem_Main_dashboard/{userId}')
def tSelectItem_Main_dashboard(request, userId: int, docu_source:str):
    user_instance = get_object_or_404(User, id=userId)

    try:
        admin_data_instance = Admin_Data.objects.get(user_id=userId)
    except Admin_Data.DoesNotExist:
        return {"error": "No matching data found"}

    office_name = admin_data_instance.office_name

    combined_data_list = []

    # Fetch data from Document_Details
    document_details_list = Document_Details.objects.filter(docu_sender=office_name)
    for document in document_details_list:
        combined_data_list.append({
            "id": document.id,
            "docu_type": document.type.docu_type if hasattr(document, 'type') else None,
            "docu_title": document.docu_title if hasattr(document, 'docu_title') else None,
            "docu_dateNtime_released": document.docu_dateNtime_released if hasattr(document, 'docu_dateNtime_released') else None,
            "docu_recipient": document.docu_recipient if hasattr(document, 'docu_recipient') else None,
            "status": str(document.status.docu_status) if document.status is not None else None,
            "docu_source": "docu_details",  
        })

    # Fetch data from Requested_Document
    request_document_list = Requested_Document.objects.filter(requested=office_name)
    for request_document in request_document_list:
        combined_data_list.append({
            "id": request_document.id,
            "docu_type": request_document.type.docu_type if hasattr(request_document, 'type') else None,
            "docu_title": request_document.docu_request_topic if hasattr(request_document, 'docu_request_topic') else None,
            "docu_dateNtime_released": request_document.docu_request_deadline if hasattr(request_document, 'docu_request_deadline') else None,
            "docu_recipient": request_document.docu_request_recipient if hasattr(request_document, 'docu_request_recipient') else None,
            "docu_request_comment": request_document.docu_request_comment,
            "status": str(request_document.status) if request_document.status is not None else None,
            "docu_source": "requested_document",
        })

    main_dashboard_data = {
        "combined_data": combined_data_list
    }

    return main_dashboard_data

#ENDPOINTS FOR RECIEVERS INFROMATION AND THE INSTANCE OF THE DOCUMENT DETAILS
@router.post("/receiver_information/document_details={docuId}")
def ReceiverInformation(request, docuId: int):
    
    try:
        receive_record_instance = Receive_Record.objects.filter(docu_details=docuId).latest('time_scanned')
    except Receive_Record.DoesNotExist:
        raise Http404(f"No Receive Record found for document ID {docuId}")

    user_instance = receive_record_instance.user_staff
    role_name = user_instance.role.role_title

    
    user_data = {
        "user_id": user_instance.id,
        "email": user_instance.email,
        "first_name": user_instance.first_name,
        "middle_name": user_instance.middle_name,
        "last_name": user_instance.last_name,
        "role":user_instance.role.role_title
    }

    
    staff_data_instance = {}
    guest_data_instance = {}

   
    if role_name == "clerk":
        staff_data = get_object_or_404(Staff_Data, user=user_instance)
        staff_data_instance = {
            "user_image_profile":staff_data.user_image_profile.url,
            "staff_data_id": staff_data.id,
            "admin_office": staff_data.admin_office.office_list,
            "staff_position": staff_data.staff_position.position_name,
        }
    elif role_name == "guest":
        guest_data = get_object_or_404(Guest_Data, user=user_instance)
        guest_data_instance = {
            "guest_data_id": guest_data.id,
            "admin_office": guest_data.guest_admin_office.office_list,
        }

   
    admin_office_names = staff_data_instance.get("admin_office", "") + ", " + guest_data_instance.get("admin_office", "")
    admin_office_names = admin_office_names.strip(", ")

  
    employee_id_image_url = receive_record_instance.employee_id_image.url if receive_record_instance.employee_id_image else None
    user_selfie_image_url = receive_record_instance.user_selfie_image.url if receive_record_instance.user_selfie_image else None

    receive_record_instance_data = {
        "user_staff_id":receive_record_instance.user_staff_id,
        "employee_id_image": employee_id_image_url,
        "user_selfie_image": user_selfie_image_url,
    }

    response_data = {
        'user': user_data, 
        "admin_office": admin_office_names,
        "receive_record": receive_record_instance_data
    }

    if role_name == "clerk":
        response_data["staff_data"] = staff_data_instance
    elif role_name == "guest":
        response_data["guest_data"] = guest_data_instance

    return response_data

# #ENDPOINT FOR UPDATING THE STATUS FOR DOCUMENT AND GUEST
@router.post('update_guest_document_status/{userId}')
def UpdateGuestDocumentStatus(request, userId:int):
    data = json.loads(request.body)
    status_value = data.get("status_value")

    document_status_instance = Document_Status.objects.get(docu_status = status_value)
    docu_status = document_status_instance.docu_status

    recipient_status_instance = Recipient_Status.objects.get(receiving_status = status_value)
    receiving_status = recipient_status_instance.receiving_status

    receive_record_instance = Receive_Record.objects.get(user_staff_id = userId)
    docuId = receive_record_instance.docu_details_id

    receive_record_instance.recipient_status = receiving_status
    receive_record_instance.save()


    document_details_instance = Document_Details.objects.get(id = docuId)
    document_details_instance.status = document_status_instance
    document_details_instance.save()

    return {'message':'the document and guest status was successfully updated'}

#ENDPOINTS OF THE UPDATING USER CLERK AND DOCUMENT STATUS
@router.post("/userNdocument_status_update/user={userId}")
def UserNDocumentStatusUpdate(request, userId: int):
    data = json.loads(request.body)
    status_value = data.get("status_value")
    print(status_value)
    print(f"Updating status for userId: {userId} to {status_value}")

    try:
        recipient_status_instance = Recipient_Status.objects.get(receiving_status=status_value)
    except Recipient_Status.DoesNotExist:
        raise HttpError(404, "Recipient Status does not exist")

    try:
        docu_status = Document_Status.objects.get(docu_status=status_value)
    except Document_Status.DoesNotExist:
        raise HttpError(404, "Document Status does not exist")

    try:
        receive_record_instance = Receive_Record.objects.filter(user_staff_id=userId).first()
        if receive_record_instance is None:
            raise HttpError(404, "Receive Record does not exist")

      
        receive_record_instance.recipient_status = recipient_status_instance.receiving_status
        receive_record_instance.save()
    except Receive_Record.DoesNotExist:
        raise HttpError(404, "Receive Record does not exist")
    except Receive_Record.MultipleObjectsReturned:
        raise HttpError(500, "Multiple Receive Records found for the given user ID")

    try:
        docuId = receive_record_instance.docu_details_id
        document_details_instance = Document_Details.objects.get(id=docuId)

      
        document_details_instance.status = docu_status
        document_details_instance.save()
    except Document_Details.DoesNotExist:
        raise HttpError(404, "Document Details does not exist")

    updated_receive_status = receive_record_instance.recipient_status
    updated_document_status = document_details_instance.status.docu_status

    return JsonResponse({
        "success": True,
        "updated_receive_status": updated_receive_status,
        "updated_document_status": updated_document_status,
    })





#ENDPONT FOR FETCHIND DATA FOR SCANNED RECEIVED RECORD DASHBOARD
@router.get('/getrecord_dashboard')
def GetRecordDashboard(request):
    receive_records_instances = Receive_Record.objects.all()

    records_data = []
    for record in receive_records_instances:
        docu_details_id = record.docu_details.id if record.docu_details else None
        user_staff_id = record.user_staff.id if record.user_staff else None
    
   
        user_staff_data = {}
        if user_staff_id is not None:
            try:
                user_instance = User.objects.get(id=user_staff_id)
                
                print(user_instance.role.role_title)
                if user_instance.role.role_title == "clerk":
                    
                    staff_data = Staff_Data.objects.get(user_id=user_staff_id)
                    admin_office_data = staff_data.admin_office.office_list
                    print(admin_office_data)
            
                elif user_instance.role.role_title == "guest":
                    print(user_staff_id)
                    guest_data = Guest_Data.objects.get(user_id=user_staff_id)
                    admin_office_data = guest_data.guest_admin_office.office_list
                    print(admin_office_data)
                else:
                    admin_office_data = None

                user_staff_data = {
                    'user_staff_id': user_staff_id,
                    'admin_office': admin_office_data,
                    'first_name': user_instance.first_name,
                    'last_name': user_instance.last_name,
                    
                }
            except User.DoesNotExist as e:
                print(e)
                
               
            except (Staff_Data.DoesNotExist, Guest_Data.DoesNotExist) as e:
               
                print(e)


       
        docu_details_data = {}
        if docu_details_id is not None:
            try:
                docu_details_data = {
                    'docu_details_id': docu_details_id,
                    'docu_title': Document_Details.objects.get(id=docu_details_id).docu_title,
                    'memorandum_number': Document_Details.objects.get(id=docu_details_id).memorandum_number,
                    'status': Document_Details.objects.get(id=docu_details_id).status.docu_status,
                    'type':Document_Details.objects.get(id=docu_details_id).type.docu_type,
                   
                }
            except Document_Details.DoesNotExist:
              
                pass

        record_data = {
            'record_id': record.id,
            'docu_details': docu_details_data,
            'user_staff': user_staff_data,
            'employee_id_image': record.employee_id_image.url if record.employee_id_image else None,
            'user_selfie_image': record.user_selfie_image.url if record.user_selfie_image else None,
            'recipient_status': record.recipient_status,
            'time_scanned': record.time_scanned,
            'is_delete':record.is_deleted,
        }

        records_data.append(record_data)

    return {'receive_records': records_data}

#ENDPOINT FOR SELECTED SCANNED DOCUMENT FOR RECEIVED RECORDS
@router.get('getScanned_document/{docuId}')
def GetScannedReceiveRecords(request, docuId:int):
    document_details_instance = Document_Details.objects.get(id = docuId)

    scanned_docu_details = {
        "memorandum_number": document_details_instance.memorandum_number,
        "docu_type":document_details_instance.type.docu_type,
        "docu_title":document_details_instance.docu_title,
        "docu_dateNtime_created":document_details_instance.docu_dateNtime_created,
        "docu_sender": document_details_instance.docu_sender,
        "docu_status": document_details_instance.status.docu_status
    }

    return {"scanned_data":scanned_docu_details}

#ENDPOINT FOR RECEIVERS THAT SCANNED THE SELECTED DOCUMENT FOR RECEIVED RECORDS
@router.get('/getReceivers_scanned_docu/{docuId}')
def GetReceiversScannedDocu(request, docuId: int):
    
    receive_records = Receive_Record.objects.filter(docu_details_id=docuId)
    if not receive_records.exists():
        return []

    receivers_info = []

    for record in receive_records:
        user_id = record.user_staff_id
        user_instance = get_object_or_404(User, id=user_id)

        staff_instance = Staff_Data.objects.filter(user=user_instance).first()
        guest_instance = Guest_Data.objects.filter(user=user_instance).first()

        if staff_instance:
            role = "Clerk"
            office_name = staff_instance.admin_office.office_list if staff_instance.admin_office else None
        elif guest_instance:
            role = "Guest"
            office_name = guest_instance.guest_admin_office.office_list if guest_instance.guest_admin_office else None
        elif user_instance.role:
            role = user_instance.role.role_title

        receiver_data = {
            "user_id": user_id,
            "role": role,
            "office_name": office_name,
            "email":user_instance.email,
            "first_name": user_instance.first_name,
            "middle_name":user_instance.middle_name,
            "last_name": user_instance.last_name,
            "time_scanned": record.time_scanned,
        }

        receivers_info.append(receiver_data)

    return {"receiver_data": receivers_info}


#ENDPOINT FOR ARCHIVED SCANNED RECEIVE RECORDS
@router.get('getArchived_scanned_receive_records')
def GetArchivedScannedReceiveRecords(request):
    receive_records_instances = Receive_Record.deleted_objects.all()
    archived_records_count = receive_records_instances.count()

    archived_records_data = []
    for record in receive_records_instances:
        docu_details_id = record.docu_details.id if record.docu_details else None
        user_staff_id = record.user_staff.id if record.user_staff else None

      
        user_staff_data = {}
        if user_staff_id is not None:
            try:
                user_instance = User.objects.get(id=user_staff_id)
                
                if user_instance.role.role_title == "clerk":
                    staff_data = Staff_Data.objects.get(user_id=user_staff_id)
                    admin_office_data = staff_data.admin_office.office_list
                elif user_instance.role.role_title == "guest":
                    guest_data = Guest_Data.objects.get(user_id=user_staff_id)
                    admin_office_data = guest_data.guest_admin_office.office_list
                else:
                    admin_office_data = None

                user_staff_data = {
                    'user_staff_id': user_staff_id,
                    'admin_office': admin_office_data,
                    'first_name': user_instance.first_name,
                    'last_name': user_instance.last_name,
                 
                }
            except User.DoesNotExist as e:
              
                print(e)
            except (Staff_Data.DoesNotExist, Guest_Data.DoesNotExist) as e:
            
                print(e)

     
        docu_details_data = {}
        if docu_details_id is not None:
            try:
                docu_details_instance = Document_Details.objects.get(id=docu_details_id)
                docu_details_data = {
                    'docu_details_id': docu_details_id,
                    'docu_title': docu_details_instance.docu_title,
                    'memorandum_number': docu_details_instance.memorandum_number,
                    'status': docu_details_instance.status.docu_status,
                    'type': docu_details_instance.type.docu_type,
                 
                }
            except Document_Details.DoesNotExist:
            
                pass

        record_data = {
            'record_id': record.id,
            'docu_details': docu_details_data,
            'user_staff': user_staff_data,
            'employee_id_image': record.employee_id_image.url if record.employee_id_image else None,
            'user_selfie_image': record.user_selfie_image.url if record.user_selfie_image else None,
            'recipient_status': record.recipient_status,
            'time_scanned': record.time_scanned,
            'is_deleted': record.is_deleted
        }

        archived_records_data.append(record_data)

    archived_receive_records = {
        "archived_records_count": archived_records_count,
        "archived_records_data": archived_records_data,
    }

    return archived_receive_records




#ENDPOINT FOR FILTERING OUTGOING DOCUMENT DETAILS
@router.get('/filterOutgoingDocumentDetails/{userId}')
def filter_outgoing_document_details(
    request, userId: int, filters: OutgoingDocuDetailsFilterSchema = Form(...),
):
    user_instance = get_object_or_404(User, id=userId)
    user_id = user_instance.id

    admin_data_instance = Admin_Data.objects.get(user_id=user_id)
    admin_office_name = admin_data_instance.office_name

    try:
        office_instance = Office.objects.get(office_list=admin_office_name)
    except Office.DoesNotExist:
        return {"error": "No matching data found"}

    office_name = office_instance.office_list

    memorandum_number = filters.memorandum_number
    type = filters.type
    docu_recipient = filters.docu_recipient

    queryset = Document_Details.objects.filter(
    
        docu_recipient__office_list=office_name
    )


    if memorandum_number:
        queryset = queryset.filter(memorandum_number__icontains=memorandum_number)


    if type:
        queryset = queryset.filter(type__icontains=type)


    if docu_recipient:
        queryset = queryset.filter(docu_recipient__in=docu_recipient)


    queryset = queryset.order_by('memorandum_number')

    filtered_documents = queryset.all()

    return {"filtered_documents": filtered_documents}

#ENDPOINT FOR COUNTING THE NUMBER OF SCANNED DOCUMENT RECORDS
@router.get('/count_scanned_records_documents/all')
def CountScannedRecordsDocuments(request, ):
    scanned_document_instance = Receive_Record.objects.all()
    count = scanned_document_instance.count()

    return{"scanned_records": count}



#ENDPOINT FOR DOCUMENT TRACKING PROGRESS ADMIN END 
@router.get('/getOutgoingDocumentTrackingProgress/document_id={docuId}')
def GetOutgoingDocumentTrackingProgress(request, docuId: int):
    receive_record_instances = Receive_Record.objects.filter(docu_details_id=docuId)
    outgoingTrackingDetailList = []

    for receive_record_instance in receive_record_instances:
        docu_id = receive_record_instance.docu_details_id
        status = receive_record_instance.docu_details.status.docu_status
        time_scanned = receive_record_instance.time_scanned

        user_instance = receive_record_instance.user_staff

        if user_instance:
            try:
                staff_data_instance = Staff_Data.objects.get(user=user_instance)
                office_name = staff_data_instance.admin_office.office_list
                result = {
                    "docuId": docu_id,
                    "scanned_docu_user": user_instance.id,
                    "time_scanned": time_scanned,
                    "status": status,
                    "office_name": office_name
                }
                outgoingTrackingDetailList.append(result)
            except Staff_Data.DoesNotExist:
                pass

            try:
                guest_data_instance = Guest_Data.objects.get(user=user_instance)
                guest_admin_office_name = guest_data_instance.guest_admin_office.office_list
                result = {
                    "docuId": docu_id,
                    "scanned_docu_user": user_instance.id,
                    "time_scanned": time_scanned,
                    "status": status,
                    "office_name": guest_admin_office_name
                }
                outgoingTrackingDetailList.append(result)
            except Guest_Data.DoesNotExist:
                pass

    return outgoingTrackingDetailList
    


#ENDPOINT FOR DOCUMENT TRACKING PROGRESS ADMIN END FOR RECEIVE
@router.get('/getReceive_document_tracking_progress/document_id={docuId}')
def GetReceiveDocumentTrackingProgress(request, docuId: int):
    receiving_docu_tracking_progress = []

    docment_details_instances = Document_Details.objects.filter(id=docuId)
    for docment_details_instance in docment_details_instances:
        receive_record_instances = Receive_Record.objects.filter(docu_details_id=docuId)
        for receive_record_instance in receive_record_instances:
            scanned_docu_user_id = receive_record_instance.user_staff_id
            staff_data_instances = Staff_Data.objects.filter(user_id=scanned_docu_user_id)
            guest_data_instances = Guest_Data.objects.filter(user_id=scanned_docu_user_id)

            for staff_data_instance in staff_data_instances:
                clerk_admin_office_id = staff_data_instance.admin_office_id
                office_instances = Office.objects.filter(id=clerk_admin_office_id)
                user_instance = User.objects.get(id=scanned_docu_user_id)
                for office_instance in office_instances:
                    result = {
                        'role':user_instance.role.role_title,   
                        "first_name": user_instance.first_name,
                        "last_name": user_instance.last_name,
                        "office_name": office_instance.office_list,
                        "time_scanned": receive_record_instance.time_scanned
                    }
                    receiving_docu_tracking_progress.append(result)

            for guest_data_instance in guest_data_instances:
                guest_admin_office_id = guest_data_instance.guest_admin_office_id
                office_instances = Office.objects.filter(id=guest_admin_office_id)
                user_instance = User.objects.get(id=scanned_docu_user_id)
                for office_instance in office_instances:
                    result = {
                        "role":user_instance.role.role_title,
                        "first_name": user_instance.first_name,
                        "last_name": user_instance.last_name,
                        "office_name": office_instance.office_list,
                        "time_scanned": receive_record_instance.time_scanned
                    }
                    receiving_docu_tracking_progress.append(result)

    return receiving_docu_tracking_progress




# #ENDPOINT FOR DELETING RECEIVED RECORDS
@router.delete('/delete_receive_record/record_id={recordId}')
def DeleteReceiveRecord(request, recordId:int):
    receive_record_instance = Receive_Record.objects.get(id = recordId)

    if receive_record_instance is not None:
        receive_record_instance.delete()
        return {'message': f'The document detail with ID {recordId} was successfully deleted'}
    else:
        return {'message': f'The document detail with ID {recordId} does not exist'}


#ENDPOINT FOR RESTORING RECEIVED RECORDS
@router.get('/restoring_receive_record/record_id={recordId}')
def DeleteReceiveRecord(request, recordId:int):
    receive_record_instance = Receive_Record.deleted_objects.get(id = recordId)

    if receive_record_instance is not None:
        receive_record_instance.restore()
        return {'message': f'The document detail with ID {recordId} was successfully deleted'}
    else:
        return {'message': f'The document detail with ID {recordId} does not exist'}
    

#ENDPOINT FOR HARD DELETING RECEIVED RECORDS
@router.get('/hard_delete_receive_record/record_id={recordId}')
def DeleteReceiveRecord(request, recordId:int):
    receive_record_instance = Receive_Record.deleted_objects.get(id = recordId)

    if receive_record_instance is not None:
        receive_record_instance.hard_delete()
        return {'message': f'The document detail with ID {recordId} was successfully deleted'}
    else:
        return {'message': f'The document detail with ID {recordId} does not exist'}
    

#ENDPOINT FOR CLERK USER SCANNED HISTORY
@router.get('/getClerk_scanned_history/userId={userId}')
def GetClerkScannedHistory(request, userId: int):
    user_scanned_record_instances = Receive_Record.objects.filter(user_staff_id=userId)

    user_scanned_document_list = []

    for user_scanned_record_instance in user_scanned_record_instances:
        user_scanned_documentId = user_scanned_record_instance.docu_details.id

        scanned_document_detials_instance = Document_Details.objects.filter(id=user_scanned_documentId).first()

        if scanned_document_detials_instance:
            scanned_document = {
                "docuId": scanned_document_detials_instance.id,
                "docu_title": scanned_document_detials_instance.docu_title,
                "memorandum_number": scanned_document_detials_instance.memorandum_number,
                "docu_type": scanned_document_detials_instance.type.docu_type,
                "time_scanned": user_scanned_record_instance.time_scanned
            }

            user_scanned_document_list.append(scanned_document)

    result = {
        "data": user_scanned_document_list,
        "count": len(user_scanned_document_list)
    }

    return result if user_scanned_document_list else {"error": "User not found or no scanned documents"}

#ENDPOINT FOR CLERK SCANNED DOCUMENT TRACKING PROGRESS
@router.get('getClerkScannedDocuTrackingProgress/docuId={docuId}')
def GetClerkScannedDocuTrackingProgress(request, docuId: int):
    receiving_docu_tracking_progress = []

    docment_details_instances = Document_Details.objects.filter(id=docuId)
    for docment_details_instance in docment_details_instances:
        receive_record_instances = Receive_Record.objects.filter(docu_details_id=docuId)
        for receive_record_instance in receive_record_instances:
            scanned_docu_user_id = receive_record_instance.user_staff_id
            staff_data_instances = Staff_Data.objects.filter(user_id=scanned_docu_user_id)
            guest_data_instances = Guest_Data.objects.filter(user_id=scanned_docu_user_id)

            for staff_data_instance in staff_data_instances:
                clerk_admin_office_id = staff_data_instance.admin_office_id
                office_instances = Office.objects.filter(id=clerk_admin_office_id)
                user_instance = User.objects.get(id=scanned_docu_user_id)
                for office_instance in office_instances:
                    result = {
                        'role': user_instance.role.role_title,   
                        "first_name": user_instance.first_name,
                        "last_name": user_instance.last_name,
                        "office_name": office_instance.office_list,
                        "time_scanned": receive_record_instance.time_scanned
                    }
                    receiving_docu_tracking_progress.append(result)

            for guest_data_instance in guest_data_instances:
                guest_admin_office_id = guest_data_instance.guest_admin_office_id
                office_instances = Office.objects.filter(id=guest_admin_office_id)
                user_instance = User.objects.get(id=scanned_docu_user_id)
                for office_instance in office_instances:
                    result = {
                        "role": user_instance.role.role_title,
                        "first_name": user_instance.first_name,
                        "last_name": user_instance.last_name,
                        "office_name": office_instance.office_list,
                        "time_scanned": receive_record_instance.time_scanned
                    }
                    receiving_docu_tracking_progress.append(result)

    count = len(receiving_docu_tracking_progress)
    return {"count": count, "data": receiving_docu_tracking_progress}








    







