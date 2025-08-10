from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from .models import User
from django.contrib.auth.hashers import make_password, check_password
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import MyTokenObtainPairSerializer, UserSerializer



class MyTokenObtainPairView(TokenObtainPairView):
    authentication_classes = []
    permission_classes = (AllowAny,)
    serializer_class = MyTokenObtainPairSerializer
    

@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def register_user(request):
    email = request.data.get('email')
    password = request.data.get('password')
    if not email or not password:
        return Response({'error': 'Email and password are required.'}, status=status.HTTP_400_BAD_REQUEST)
    if User.objects.filter(email=email).exists():
        return Response({'error': 'User with this email already exists.'}, status=status.HTTP_409_CONFLICT)
    hashed_password = make_password(password)
    user = User.objects.create(email=email, password=hashed_password)
    return Response({'message': 'User created successfully.'}, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated]) 
def get_current_user(request):
    """
    API endpoint that returns the details of the currently authenticated user.
    """
    user = request.user
    serializer = UserSerializer(user)
    return Response(serializer.data, status=status.HTTP_200_OK)