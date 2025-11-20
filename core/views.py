from django.shortcuts import render

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated 
from rest_framework.exceptions import NotFound

from .models import Admin, PoliceOffice, Report, Message
from .serializers import (
    AdminSerializer, 
    PoliceOfficeLoginSerializer, 
    PoliceOfficeCreateSerializer,
    ReportCreateSerializer,
    ReportListSerializer,
    ReportStatusUpdateSerializer,
    MessageSerializer,
)

# Create your views here.
class LoginAPIView(APIView):
    # handles login for both Admin and Police roles

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password') # Plaintext for now; to be hashed later

        if not email or not password:
            return Response({"detail": "Email and password are required."}, 
                            status=status.HTTP_400_BAD_REQUEST)

        # 1. Attempt Admin Login
        try:
            admin_user = Admin.objects.get(email=email)
            # TEMPORARY CHECK: Replace with actual hashing check later (Day 3 update)
            if password == "testpass": 
                serializer = AdminSerializer(admin_user)
                return Response({
                    "message": "Admin login successful",
                    "role": "admin",
                    "user": serializer.data,
                    "token": "DUMMY_ADMIN_TOKEN"
                }, status=status.HTTP_200_OK)
        except Admin.DoesNotExist:
            pass # Continue to Police check

        # 2. Attempt Police Login
        try:
            police_office = PoliceOffice.objects.get(email=email)
            # TEMPORARY CHECK: Replace with actual hashing check later (Day 3 update)
            if password == "testpass":
                serializer = PoliceOfficeLoginSerializer(police_office)
                return Response({
                    "message": "Police login successful",
                    "role": "police",
                    "user": serializer.data,
                    "token": "DUMMY_POLICE_TOKEN"
                }, status=status.HTTP_200_OK)
        except PoliceOffice.DoesNotExist:
            # 3. If neither found
            return Response({"detail": "Invalid credentials."}, 
                            status=status.HTTP_401_UNAUTHORIZED)
        
        # 4. Fallback for incorrect password (if email found but temp password is wrong)
        return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
    
class PoliceOfficeAdminViewSet(viewsets.ModelViewSet):
    # queryset = PoliceOffice.objects.all() # Fetch all offices for Admin view
    
    # CRITICAL: Filter to exclude the main Admin login account
    queryset = PoliceOffice.objects.all().exclude(email='test@crash.ph') 
    
    serializer_class = PoliceOfficeCreateSerializer
    # permission_classes = [IsAuthenticated, IsAdminUser] # You'll add IsAdminUser later

    # --- Override methods for different serializers ---
    
    def get_serializer_class(self):
        """Use the standard PoliceOfficeLoginSerializer for list/read, 
        but use the creation serializer for POST/CREATE."""
        if self.action in ['create', 'update', 'partial_update']:
            return PoliceOfficeCreateSerializer
        return PoliceOfficeLoginSerializer # Use the safer LoginSerializer for viewing

    # Automatically set the created_by field to the logged-in Admin
    def perform_create(self, serializer):
        # 1. Get the admin_id string from the request data
        admin_id_str = self.request.data.get('created_by', None)

        if not admin_id_str:
            # Handle case where created_by is missing (Optional: raise a validation error here)
            return Response({"created_by": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 2. Fetch the actual Admin object using the UUID string
            admin_instance = Admin.objects.get(admin_id=admin_id_str)
        except Admin.DoesNotExist:
            # Handle case where the provided UUID doesn't exist
            return Response({"created_by": "Admin account not found."}, status=status.HTTP_404_NOT_FOUND)

        # 3. Pass the *object instance* to the serializer.save() method
        # Django will automatically extract the primary key (admin_id) for the DB insertion.
        serializer.save(created_by=admin_instance)

class ReportViewSet(viewsets.ModelViewSet):
    # Base queryset for all report operations
    queryset = Report.objects.all().select_related('reporter', 'assigned_office')
    
    def get_serializer_class(self):
        """Use different serializers for input (create) vs. output (read)."""
        if self.action == 'create':
            return ReportCreateSerializer
        return ReportListSerializer # Use the list serializer for GET requests

    # --- Step 1: Implement Police Dashboard Read (Filtering) ---
    def get_queryset(self):
        # Implement the logic for Police Dashboard: fetch all active reports
        if self.request.method == 'GET':
            # Active status means NOT Resolved or Canceled 
            return self.queryset.exclude(status__in=['Resolved', 'Canceled']).order_by('-created_at')
        
        # For other methods (like PUT, DELETE), use the base queryset
        return self.queryset

    # --- Step 2: Implement Report Submission (Nearest Office Stub) ---
    def perform_create(self, serializer):
        # NOTE: In a real system, reporter_id comes from the auth token, 
        # but for Postman simulation, we get it from the request data for now.
        reporter_id = self.request.data.get('reporter')
        
        # 1. Simulate Nearest Office Assignment (STUB)
        # Full distance calculation (GIS) is Day X, so for now, assign to the first existing office.
        try:
            nearest_office = PoliceOffice.objects.all().first()
            assigned_office_instance = nearest_office
        except PoliceOffice.DoesNotExist:
            assigned_office_instance = None # If no offices exist

        # 2. Save the report with the assigned office and reporter ID
        serializer.save(
            assigned_office=assigned_office_instance,
            reporter_id=reporter_id # Django handles UUID string for reporter_id correctly here
        )
    
    # --- Step 3: Implement Report Status Update ---
    def get_serializer_class(self):
        """Use different serializers based on the action."""
        if self.action == 'create':
            return ReportCreateSerializer
        # Use the specific serializer for PUT/PATCH operations
        if self.action in ['update', 'partial_update']:
            return ReportStatusUpdateSerializer
        return ReportListSerializer # Default for GET (list/retrieve)

class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    
    # We define this dynamically based on the URL path
    def get_queryset(self):
        # 1. Get report_id from the URL path (from core/urls.py)
        report_id = self.kwargs.get('report_id')
        
        if report_id:
            # 2. Filter messages only for the specified report
            return Message.objects.filter(report_id=report_id).order_by('timestamp')
        return Message.objects.none() # Return empty if no report_id is provided

    def perform_create(self, serializer):
        # 1. Get report_id from the URL path (Change key from 'report_id' to 'report_pk')
        report_id = self.kwargs.get('report_pk') 
        
        # 2. Assign the report to the new message
        try:
            report_instance = Report.objects.get(report_id=report_id)
        except Report.DoesNotExist:
            # 3. Raise the correct exception type
            raise NotFound(detail="Report not found.") # <-- CORRECTED SYNTAX
        
        # 3. Simulate sender identification (Police flow)
        # NOTE: In a real authenticated scenario, you would get sender_id and sender_type 
        # from the logged-in user's token (PoliceOffice ID and 'police' role).
        
        # For testing the Police POST (Day 7):
        # The frontend provides sender_id, sender_type, and receiver_id in the body.
        
        serializer.save(
            report=report_instance,
            # For the POST request, the necessary sender/receiver IDs are expected
            # in the request body for testing flexibility.
        )

