import django_filters
from django.contrib.auth import authenticate
from django.contrib.auth.models import Group, Permission
from django.views.decorators.csrf import csrf_exempt
from drf_yasg.openapi import Parameter, IN_QUERY
from drf_yasg.utils import swagger_auto_schema
import requests
from rest_framework import filters
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from .models import User, Country, Flight
from . import serializers


class PageSizeAndNumberPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 1000


@swagger_auto_schema(method='post', request_body=serializers.RegisterSerializer)
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = serializers.RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user, token = serializer.save()

    data = {"user": user, "access_token": token.key}
    return Response(serializers.UserTokenSerializer(data).data, status=status.HTTP_201_CREATED)


@swagger_auto_schema(method='post', request_body=serializers.LoginSerializer)
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    wrong_credentials = {"detail": "Wrong credentials."}
    serializer = serializers.LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    data = serializer.validated_data
    if data.get('email'):
        user = authenticate(request, email=data['email'], password=data['password'])
    elif data.get('phone_number'):
        user = authenticate(request, phone_number=data['phone_number'], password=data['password'])
    else:
        return Response({'detail': 'Please provide email or phone number.'}, status=status.HTTP_401_UNAUTHORIZED)

    if not user:
        return Response(wrong_credentials, status=status.HTTP_401_UNAUTHORIZED)

    token, created = Token.objects.get_or_create(user=user)

    data = {"user": user, "access_token": token.key}

    return Response(serializers.UserTokenSerializer(data).data, status=status.HTTP_200_OK)


class RoleListView(ListCreateAPIView):
    serializer_class = serializers.GroupSerializer
    permission_classes = [IsAdminUser]
    pagination_class = PageSizeAndNumberPagination
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = '__all__'

    def get_queryset(self):
        return Group.objects.all()


class RoleDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = serializers.GroupSerializer

    def get_queryset(self):
        return Group.objects.all()

    def get_object(self):
        id_ = self.kwargs.get('pk')
        recipe = Group.objects.get(id=id_)
        return recipe


class PermissionListView(ListCreateAPIView):
    serializer_class = serializers.PermissionSerializer
    permission_classes = [IsAdminUser]
    pagination_class = PageSizeAndNumberPagination
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['code_name']
    ordering_fields = '__all__'

    def get_queryset(self):
        return Permission.objects.all()


class PermissionDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = serializers.PermissionSerializer

    def get_queryset(self):
        return Permission.objects.all()

    def get_object(self):
        id_ = self.kwargs.get('pk')
        recipe = Permission.objects.get(id=id_)
        return recipe


class CountryListView(ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = serializers.CountrySerializer

    def get_queryset(self):
        return Country.objects.all()


@swagger_auto_schema(method='post', request_body=serializers.PermissionAssignSerializer, manual_parameters=[Parameter('operation', IN_QUERY, type='string')])
@api_view(http_method_names=['POST'])
@permission_classes([IsAdminUser])
def assign_permissions_to_user(request, pk):

    operation = request.query_params.get('operation')
    user = User.objects.get(pk=pk)
    serializer = serializers.PermissionAssignSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    ids = serializer.validated_data.get('permission_ids')
    if operation == 'add':
        user.user_permissions.add(*ids)
    else:
        user.user_permissions.remove(*ids)
    return Response({'detail': 'Successful'})


@swagger_auto_schema(method='post', request_body=serializers.PermissionAssignSerializer, manual_parameters=[Parameter('operation', IN_QUERY, type='string')])
@api_view(http_method_names=['POST'])
@permission_classes([IsAdminUser])
def assign_permissions_to_group(request, pk):

    operation = request.query_params.get('operation')
    role = Group.objects.get(pk=pk)
    serializer = serializers.PermissionAssignSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    ids = serializer.validated_data.get('permission_ids')
    if operation == 'add':
        role.permissions.add(*ids)
    else:
        role.permissions.remove(*ids)
    return Response({'detail': 'Successful'})


@swagger_auto_schema(method='post', request_body=serializers.RoleAssignSerializer, manual_parameters=[Parameter('operation', IN_QUERY, type='string')])
@api_view(http_method_names=['POST'])
@permission_classes([IsAdminUser])
def assign_roles_to_user(request, pk):

    operation = request.query_params.get('operation')
    user = User.objects.get(pk=pk)
    serializer = serializers.RoleAssignSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    ids = serializer.validated_data.get('role_ids')
    if operation == 'add':
        user.groups.add(*ids)
    else:
        user.groups.remove(*ids)
    return Response({'detail': 'Successful'})


@api_view(http_method_names=['GET'])
@permission_classes([AllowAny])
def recommendations(request, departure_port, departure_date):

    url = f'http://127.0.0.1:8100/{departure_port}/{departure_date}'
    resp = requests.get(url)
    if resp.ok:
        data = resp.json()
        for flt in data:
            flt['carrier_name'] = Flight.objects.get(id=flt.get('id')).carrier.name
    else:
        print(resp.json())
        data = 'There is an error'
    return Response({'detail': data})


class FlightListView(ListCreateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = serializers.FlightSerializer

    def get_queryset(self):
        return Flight.objects.all()
