from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.contrib.auth import get_user_model

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'email'
    
    def validate(self, attrs):
        # print("LOGIN ATTEMPT:", attrs)
        return super().validate(attrs)
    


User = get_user_model() 

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'role', 'created_at', 'updated_at'] 
        read_only_fields = ['id', 'email', 'role', 'created_at', 'updated_at'] 
