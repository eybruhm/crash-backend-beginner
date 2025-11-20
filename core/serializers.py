# core/serializers.py
from rest_framework import serializers
from .models import Admin, PoliceOffice, Report, Message
from django.contrib.auth.hashers import make_password

# Serializer for Admin details 
class AdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Admin
        fields = ('admin_id', 'username', 'email', 'contact_no')
        
# Serializer for Police Office (used for login response, excluding password_hash)
class PoliceOfficeLoginSerializer(serializers.ModelSerializer):
    class Meta:
        model = PoliceOffice
        # Exclude sensitive data (password_hash) and focus on identification fields
        fields = ('office_id', 'office_name', 'email', 'head_officer', 'contact_number')

# Serializer for Police Office creation (includes password hashing)
class PoliceOfficeCreateSerializer(serializers.ModelSerializer):
    # 1. Define 'password' field for input only
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = PoliceOffice
        # Include email and password_hash for creation
        fields = (
            'office_name', 'email', 'password', 'head_officer', 
            'contact_number', 'latitude', 'longitude', 'created_by'
        )
        extra_kwargs = {
            'password_hash': {'write_only': True} 
        }
    
    # 2. Override the create method to hash the password
    def create(self, validated_data):
        # Pop the plain password out of the data dictionary
        password = validated_data.pop('password')
        
        # Hash the password and set it to the password_hash field
        validated_data['password_hash'] = make_password(password)
        
        # Create the PoliceOffice object with the hashed password
        return PoliceOffice.objects.create(**validated_data)
    
# Serializer for receiving new reports (input from mobile app)
class ReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = (
            'category', 
            'description', 
            'latitude', 
            'longitude', 
            'reporter', # The ID will be passed/inferred during POST
        )

# Serializer for listing active reports (output to police dashboard)
class ReportListSerializer(serializers.ModelSerializer):
    # Display the related police office name and reporter name, not just UUIDs
    assigned_office_name = serializers.CharField(source='assigned_office.office_name', read_only=True)
    reporter_full_name = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Report
        fields = (
            'report_id', 
            'category', 
            'status', 
            'created_at', 
            'latitude',
            'longitude',
            'description',
            'assigned_office_name', 
            'reporter_full_name'    
        )
    
    # Custom method to join first and last names
    def get_reporter_full_name(self, obj):
        if obj.reporter:
            return f"{obj.reporter.first_name} {obj.reporter.last_name}"
        return "N/A" # If reporter is null (deleted account)
    
# Serializer for updating report status (used by police to update status)
class ReportStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        # Only allow updating status and remarks
        fields = ('status', 'remarks')
        read_only_fields = ('report_id', 'reporter', 'category', 'latitude', 'longitude') 

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__' # Include all fields for simple read/write
        read_only_fields = ('message_id', 'timestamp')

