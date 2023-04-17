import json
import pandas as pd
import datetime,pytz
import random, string, os,json
from django.db.models import Sum
from django.utils import timezone
from django.db.models import Count
from datetime import datetime, timedelta
from django.db.models import Prefetch
from django.utils.decorators import method_decorator
from django.http import Http404,HttpResponse,JsonResponse
from .authentication import ExpiringTokenAuthentication

from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate,logout

from .serializers import CountrySerializer,AnswersSectionSerializer,EducationSerializer,UserSerializer,TypeIDSerializer,MediaSerializer,ClientsSerializer,DashboardsSerializer,FootsoldiersSerializer
from .serializers import SectionsSerializer,PosSerializer,ProduitSerializer,ExamSerializer,UserExamenSerializer,AnswersExamen,UploadSerializer,TrainingSerializer,UserScoreExamSerializer
from .serializers import TypeIDSerializer ,UsersClientSerializer,TargetSerializer,ChaptersSerializer,QuizSectionSerializer,QuizExamen,QuizExamenSerializer,AnswersExamenSerializer

from .models import EducationLevel,Locality,User,Countries,TokenPin,TypeID,Media,Kyc,Clients,Dashboards,Industry,Produit,Training,AnswersSection,UserScoreExam,Chapters,Exam
from .models import Kyc, User, EducationLevel, Locality, Countries, TypeID, Media,Footsoldiers,Pos,Domaine,UsersClient,Target,Sections,QuizSection,Privilege,UserExam,TypeID

from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework import viewsets,status,generics
from django_filters import rest_framework as filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import authentication_classes, permission_classes,api_view
from rest_framework.parsers import MultiPartParser, FormParser,FileUploadParser


######################################### Login, token ##################################################
# connexion user
class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)

        data = {}

        if not user:
            data['login_status'] = 'Echec'

        utc_now = datetime.utcnow()
        utc_now = utc_now.replace(tzinfo=pytz.utc)

        result = Token.objects.filter(user=user, created__lt=utc_now - timedelta(seconds=10)).delete()

        # Create a new token for the user
        token, created = Token.objects.get_or_create(user=user)

        # Set the expiration time for the token
        expiration_time = timezone.now() + timezone.timedelta(seconds=7200)
        token.expires = expiration_time
        token.save()

        if token.expires < timezone.now():
            data['token_status'] = 'Token invalide'

        user_serializer = UserSerializer(user)
        data = {
            'user': user_serializer.data,
            'token': token.key,
            'token_status': 'Token valide' if not created else 'Nouveau Token',
            'date_expiration': expiration_time,
            'login_status': 'Valid',
        }
        return Response(data=data)

# déconnexion super admin
class LogoutView(APIView):
    def post(self, request, *args, **kwargs):
        # Récupérer le token d'authentification de la requête
        auth_token = request.META.get('HTTP_AUTHORIZATION').split(' ')[1]
        # Supprimer le token de la base de données
        Token.objects.filter(key=auth_token).delete()
        # Déconnecter l'utilisateur de la session
        logout(request)
        return Response({'message': 'Vous êtes déconnecter'})

######################################### CRUD for user ##################################################
# list for user
class UserView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        queryset = User.objects.all()
        data = {
            'List des Users': list(queryset.values())
        }
        return Response(data)
    
    serializer_class = UsersClientSerializer
    filter_backends = (filters.DjangoFilterBackend)

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# list user for client
class ClientUsersView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    serializer_class = UserSerializer

    def get(self, request):
        user = request.user
        users = User.objects.filter(the_client=user.the_client)
        users_list = list(users.values())
        return JsonResponse(users_list, safe=False)
    filter_backends = (filters.DjangoFilterBackend)

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
    
# Afficher les détails d'un user
class DetailsUser(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, id, format=None):
        try:
            user = User.objects.get(id=id)
        except User.DoesNotExist:
            data = {'message':"L'utilisateur n'existe pas"}
            return JsonResponse(data, status=404)
        
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
            
        data = {
            'user_id': user.id,
            'user_email': user.email,
            'user_identifiant': user.username,
            'user_name': user.user_name,
            'privilege_id': user.privilege_id,
            'country_id': user.country_id,
            'client_id': user.client_id,
        }

        return JsonResponse(data)
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
    
# create one user
class CreateUsersView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @csrf_exempt
    def post(self, request, format=None):
        email = request.POST.get('email', None)
        if not email:
            return HttpResponse("Le champ email est requis.")
        nom = request.POST.get('nom', None)
        if not nom:
            return HttpResponse("Le champ nom est requis.")
        prenoms = request.POST.get('prenoms', None)
        if not prenoms:
            return HttpResponse("Le champ prenoms est requis.")
        username = request.POST.get('username', None)
        if not username:
            return HttpResponse("Le champ username est requis.")
        password = request.POST.get('password', None)
        if not password:
            return HttpResponse("Le champ password est requis.")
        niveau_education = request.POST.get('niveau_education', None)
        if not niveau_education:
            return HttpResponse("Le champ niveau_education est requis.")
        country = request.POST.get('country', None)
        if not country:
            return HttpResponse("Le champ country est requis.")
        numero = request.POST.get('numero', None)
        if not numero:
            return HttpResponse("Le champ numero est requis.")
        date_naissance = request.POST.get('date_naissance', None)
        if not date_naissance:
            return HttpResponse("Le champ date_naissance est requis.")
        type_piece = request.POST.get('type_piece', None)
        if not type_piece:
            return HttpResponse("Le champ type_piece est requis.")
        numero_piece = request.POST.get('numero_piece', None)
        if not numero_piece:
            return HttpResponse("Le champ numero_piece est requis.")
        date_expiration = request.POST.get('date_expiration', None)
        if not date_expiration:
            return HttpResponse("Le champ date_expiration est requis.")
        piece_recto = request.FILES.get('piece_recto', None)
        if not piece_recto:
            return HttpResponse("Le champ piece_recto est requis.")
        piece_verso = request.FILES.get('piece_verso', None)
        if not piece_verso:
            return HttpResponse("Le champ piece_verso est requis.")
        profile_picture = request.FILES.get('profile_picture', None)
        if not profile_picture:
            return HttpResponse("Le champ profile_picture est requis.")
        privilege = request.POST.get('privilege', None)
        if not privilege:
            return HttpResponse("Le champ privilege est requis.")
        the_client = request.POST.get('the_client', None)
        if not the_client:
            return HttpResponse("Le champ the_client est requis.")

        # user = request.user
        # if not user.is_superuser:
        #     try:
        #         privilege_admin = Privilege.objects.get(id=1)
        #     except Privilege.DoesNotExist:
        #         data = {'message':"Le privilège 'admin' n'existe pas."}
        #         return HttpResponse(data)

        #     if not user.privilege == privilege_admin:
        #         data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
        #         return HttpResponse(data)

        try:
            education = EducationLevel.objects.get(id_education=niveau_education)
        except EducationLevel.DoesNotExist:
            return HttpResponse("L'education spécifié n'existe pas.")

        try:
            privilege = Privilege.objects.get(id=privilege)
        except Privilege.DoesNotExist:
            return HttpResponse("Le privilège spécifié n'existe pas.")
        
        try:
            type = TypeID.objects.get(id_type=type_piece)
        except Countries.DoesNotExist:
            return HttpResponse("Le type d'ID spécifié n'existe pas.")
        
        try:
            pays = Countries.objects.get(id_country=country)
        except Countries.DoesNotExist:
            return HttpResponse("Le pays spécifié n'existe pas.")
        
        try:
            clientss = Clients.objects.get(id_client=the_client)
        except Clients.DoesNotExist:
            return HttpResponse("Le CLient spécifié n'existe pas.")
        
        user = User(
            email=email,
            nom=nom,
            prenoms=prenoms,
            username=username,
            niveau_education=education,
            country=pays,
            numero=numero,
            date_naissance=date_naissance,
            type_piece=type,
            numero_piece=numero_piece,
            date_expiration=date_expiration,
            piece_recto=piece_recto,
            piece_verso=piece_verso,
            account_validated=True,
            privilege = privilege,
            the_client = clientss,
            is_active=True,
            is_staff=False,
            profile_picture=profile_picture,
        )
        user.set_password(password)
        user.save()

        data = {'message': 'Utilisateur ajouté avec succès'}
        return JsonResponse(data)
    
    def get(self, request, format=None):
        return JsonResponse({'error': 'Méthode non autorisée'})
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
        
# modification des éléments d'un user
class UpdateUserView(generics.UpdateAPIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    parser_classes = (MultiPartParser, FormParser, FileUploadParser)
    serializer_class = UserSerializer
    lookup_field = 'id'
    queryset = User.objects.all()
    
            
    def get_object(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise Http404
        
            
    def put(self, request, user_id):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
            
        user = self.get_object(user_id)
        user.email = request.data.get('email', user.email)
        user.nom = request.data.get('nom', user.nom)
        user.prenoms = request.data.get('prenoms', user.prenoms)
        country_id = request.data.get('country')
        if country_id:
            countries = Countries.objects.get(id_country=country_id)
            user.country = countries
        user.username = request.data.get('username', user.username)
        user.password = request.data.get('password', user.password)
        user.profile_picture = request.data.get('profile_picture', user.profile_picture)
        client = request.data.get('the_client')
        if client:
            clients = Clients.objects.get(id_client=client)
            user.the_client = clients
        privileges = request.data.get('privilege')
        if privileges:
            privilegess = Privilege.objects.get(id=privileges)
            user.privilege = privilegess
        user.save()

        data = {'message': 'Pays modifié avec succès'}
        return JsonResponse(data)
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
    
# delete one user
class DeleteUserView(generics.DestroyAPIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    serializer_class = UserSerializer
    lookup_field = 'id'
    queryset = User.objects.all()

    def delete(self, request, *args, **kwargs):
        user = request.user
        
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                return HttpResponse("Le privilège 'admin' n'existe pas.")
            
            if not user.privilege == privilege_admin:
                return HttpResponse("Vous n'avez pas le droit de supprimer un utilisateur.")
        
        return self.destroy(request, *args, **kwargs)
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
    
######################################### CRUD Final exam section ##################################################
# userscore crud
class UserScoreCreate(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @csrf_exempt
    def post(self, request, format=None):
        id_exam = request.POST.get('id_exam', None)
        if not id_exam:
            return HttpResponse("Le champ id_exam est requis.")
        score = request.POST.get('score', None)
        if not score:
            return HttpResponse("Le champ score est requis.")
        nombredepoints = request.POST.get('nombredepoints', None)
        if not nombredepoints:
            return HttpResponse("Le champ nombredepoints est requis.")
        results = request.POST.get('results', None)
        if not results:
            return HttpResponse("Le champ results est requis.")

        try:
            examen = Exam.objects.get(id_examen=id_exam)
        except Exam.DoesNotExist:
            return HttpResponse("L'examen spécifié n'existe pas.")
        
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)

        user_score_exam = UserScoreExam(
            id_exam=examen, 
            id_user=user,
            score=score,
            results=results,
            nombredepoints=nombredepoints,
        )
        user_score_exam.save()

        data = {'message': 'Le score du user ajouté avec succès'}
        return JsonResponse(data)
    
    def get(self, request, format=None):
        return JsonResponse({'error': 'Méthode non autorisée'})
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# userscore list
class UserScoreList(generics.ListAPIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = UserScoreExam.objects.filter(user = request.user)
        data = {
            'Scores des users': list(queryset.values())
        }
        return Response(data)
    serializer_class = UserScoreExamSerializer

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

######################################### CRUD Exam ##################################################
# créer une question pour l'examen
class AnswerExamCreate(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @csrf_exempt
    def post(self, request, format=None):

        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
            
        id_quiz_examen = request.POST.get('id_quiz_examen', None)
        if not id_quiz_examen:
            return HttpResponse("Le champ id_quiz_examen est requis.")
        answer_label = request.POST.get('answer_label', None)
        if not answer_label:
            return HttpResponse("Le champ answer_label est requis.")
        answer_correct = request.POST.get('answer_correct', None)
        if not answer_correct:
            return HttpResponse("Le champ answer_correct est requis.")

        try:
            quiz_examen = QuizExamen.objects.get(id_quiz_examen=id_quiz_examen)
        except QuizExamen.DoesNotExist:
            return HttpResponse("L'examen spécifié n'existe pas.")
        
        

        answer_exam = AnswersExamen(
            id_quiz_examen=quiz_examen, 
            answer_label=answer_label,
            answer_correct=answer_correct,
        )
        answer_exam.save()

        data = {'message': 'User ajouté avec succès'}
        return JsonResponse(data)
    
    def get(self, request, format=None):
        return JsonResponse({'error': 'Méthode non autorisée'})
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# liste des questions pour l'examen
class AnswerExamList(generics.ListAPIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = AnswersExamen.objects.all()
        data = {
            'Questions des examens': list(queryset.values())
        }
        return Response(data)
    serializer_class = AnswersExamenSerializer

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# créer un user pour l'examen
class UserExamCreate(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @csrf_exempt
    def post(self, request, format=None):
        id_quiz = request.POST.get('id_quiz', None)
        if not id_quiz:
            return HttpResponse("Le champ id_quiz est requis.")
        choice = request.POST.get('choice', None)
        if not choice:
            return HttpResponse("Le champ choice est requis.")
        answer = request.POST.get('answer', None)
        if not answer:
            return HttpResponse("Le champ answer est requis.")

        try:
            quiz_examen = QuizExamen.objects.get(id_quiz_examen=id_quiz)
        except QuizExamen.DoesNotExist:
            return HttpResponse("L'examen spécifié n'existe pas.")
        
        user_exam = UserExam(
            id_quiz=quiz_examen, 
            choice=choice,
            answer=answer,
        )
        user_exam.save()

        data = {'message': 'User ajouté avec succès'}
        return JsonResponse(data)
    
    def get(self, request, format=None):
        return JsonResponse({'error': 'Méthode non autorisée'})
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# liste des user pour l'examen
class UserExamList(generics.ListAPIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = UserExam.objects.all()
        data = {
            'List des participants': list(queryset.values())
        }
        return Response(data)
    serializer_class = UserExamenSerializer

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

######################################### CRUD Exam ##################################################
# Créer un examen
class ExamCreate(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @csrf_exempt
    def post(self, request, format=None):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
            
        id_training = request.POST.get('id_training', None)
        if not id_training:
            return HttpResponse("Le champ id_training est requis.")
        exam_name = request.POST.get('exam_name', None)
        if not exam_name:
            return HttpResponse("Le champ exam_name est requis.")
        exam_description = request.POST.get('exam_description', None)
        if not exam_description:
            return HttpResponse("Le champ exam_description est requis.")
        try:
            training = Training.objects.get(id_training=id_training)
        except Training.DoesNotExist:
            return HttpResponse("La formation spécifié n'existe pas.")
        
        exam = Exam(
            id_training=training,
            exam_name=exam_name,
            exam_description=exam_description,
        )
        exam.save()

        data = {'message': 'Examen quiz ajouté avec succès'}
        return JsonResponse(data)
    
    def get(self, request, format=None):
        return JsonResponse({'error': 'Méthode non autorisée'})
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# liste des examen
class ExamList(generics.ListAPIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        queryset = Exam.objects.all()
        data = {
            'Liste des Examens': list(queryset.values())
        }
        return Response(data)
    serializer_class = ExamSerializer

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

######################################### CRUD Quiz_Exam ##################################################
# Créer un quiz pour l'examen
class QuizExamCreate(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @csrf_exempt
    def post(self, request, format=None):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        id_examen = request.POST.get('id_examen', None)
        if not id_examen:
            return HttpResponse("Le champ id_examen est requis.")
        quiz_question_name = request.POST.get('quiz_question_name', None)
        if not quiz_question_name:
            return HttpResponse("Le champ quiz_question_name est requis.")
        quiz_question_points = request.POST.get('quiz_question_points', None)
        if not quiz_question_points:
            return HttpResponse("Le champ quiz_question_points est requis.")
        quiz_question_type = request.POST.get('quiz_question_type', None)
        if not quiz_question_type:
            return HttpResponse("Le champ quiz_question_type est requis.")
        quiz_question_media = request.FILES.get('quiz_question_media', None)
        if not quiz_question_media:
            return HttpResponse("Le champ quiz_question_media est requis.")
        quiz_description = request.POST.get('quiz_description', None)
        if not quiz_description:
            return HttpResponse("Le champ quiz_description est requis.")

        try:
            examen = Exam.objects.get(id_examen=id_examen)
        except Exam.DoesNotExist:
            return HttpResponse("L'examen spécifié n'existe pas.")
        
        quiz_exam = QuizExamen(
            id_examen=examen, 
            quiz_question_name=quiz_question_name,
            quiz_question_points=quiz_question_points,
            quiz_question_type=quiz_question_type,
            quiz_question_media=quiz_question_media,
            quiz_description=quiz_description,
        )
        quiz_exam.save()

        data = {'message': 'Examen quiz ajouté avec succès'}
        return JsonResponse(data)
    
    def get(self, request, format=None):
        return JsonResponse({'error': 'Méthode non autorisée'})
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# liste des quizExamen
class QuizExamList(generics.ListAPIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Exam.objects.prefetch_related(
            Prefetch('quizexamen_set', queryset=QuizExamen.objects.prefetch_related('answersexamen_set'))
        )
        data = {
            'La liste des Examens avec le nombre de quiz questions et les questions avec les réponses': [
                {
                    'examen': exam.exam_name,
                    'nombre_questions': exam.quizexamen_set.count(),
                    'questions': [
                        {
                            'question': question.quiz_question_name,
                            'points': question.quiz_question_points,
                            'type': question.quiz_question_type,
                            'media': question.quiz_question_media.url,
                            'description': question.quiz_description,
                            'reponses': [
                                {
                                    'label': answer.answer_label,
                                    'correct': answer.answer_correct
                                } for answer in question.answersexamen_set.all()
                            ]
                        } for question in exam.quizexamen_set.all()
                    ]
                } for exam in queryset
            ]
        }
        return Response(data)


    # def handle_exception(self, exc):
    #     data = {}
    #     if isinstance(exc, AuthenticationFailed):
    #         data['token_status'] = 'Token Invalide'
    #         return Response(data, status=status.HTTP_401_UNAUTHORIZED)
    #     return super().handle_exception(exc)

# modifier un quizexam
class ModifierQuizExam(generics.UpdateAPIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self, exam_id, quiz_id):
        try:
            quiz = QuizExamen.objects.select_related('id_examen').get(id_quiz_examen=quiz_id, id_examen__id_exam=exam_id)
            return quiz
        except QuizExamen.DoesNotExist:
            raise Http404

    def update(self, request, exam_id, quiz_id):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        quiz = self.get_object(exam_id, quiz_id)
        quiz.quiz_question_name = request.data.get('quiz_question_name', quiz.quiz_question_name)
        quiz.quiz_question_points = request.data.get('quiz_question_points', quiz.quiz_question_points)
        quiz.quiz_question_type = request.data.get('quiz_question_type', quiz.quiz_question_type)
        quiz.quiz_question_media = request.data.get('quiz_question_media', quiz.quiz_question_media)
        quiz.quiz_description = request.data.get('quiz_description', quiz.quiz_description)
        quiz.save()

        for answer in quiz.answersexamen_set.all():
            answer_id = str(answer.id_answer_examen)
            answer_label = request.data.get(f'answer_label_{answer_id}', answer.answer_label)
            answer_correct = request.data.get(f'answer_correct_{answer_id}', answer.answer_correct)
            answer.answer_label = answer_label
            answer.answer_correct = answer_correct
            answer.save()

        data = {
            'message': 'Le quiz et ses réponses ont été modifiés avec succès',
            'quiz': {
                'id_quiz_examen': quiz.id_quiz_examen,
                'quiz_question_name': quiz.quiz_question_name,
                'quiz_question_points': quiz.quiz_question_points,
                'quiz_question_type': quiz.quiz_question_type,
                'quiz_question_media': quiz.quiz_question_media.url if quiz.quiz_question_media else None,
                'quiz_description': quiz.quiz_description,
                'answers': [
                    {
                        'id_answer_examen': answer.id_answer_examen,
                        'answer_label': answer.answer_label,
                        'answer_correct': answer.answer_correct,
                    } for answer in quiz.answersexamen_set.all()
                ]
            }
        }
        return Response(data)

######################################### CRUD answers section ##################################################
# Créer un quiz pour la section
class AnswerSectionCreate(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @csrf_exempt
    def post(self, request, format=None):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        id_quiz = request.POST.get('id_quiz', None)
        if not id_quiz:
            return HttpResponse("Le champ id_quiz est requis.")
        answer_label = request.POST.get('answer_label', None)
        if not answer_label:
            return HttpResponse("Le champ answer_label est requis.")
        answer_correct = request.POST.get('answer_correct', None)
        if not answer_correct:
            return HttpResponse("Le champ answer_correct est requis.")

        try:
            quiz = QuizSection.objects.get(id_quiz_section=id_quiz)
        except QuizSection.DoesNotExist:
            return HttpResponse("Le Quiz spécifié n'existe pas.")
        
        answer_quiz_section = AnswersSection(
            id_quiz=quiz, 
            answer_label=answer_label,
            answer_correct=answer_correct,
        )
        answer_quiz_section.save()

        data = {'message': 'Answer quiz ajouté avec succès'}
        return JsonResponse(data)
    
    def get(self, request, format=None):
        return JsonResponse({'error': 'Méthode non autorisée'})
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# liste des quiz pour la section
class AnswerSectionList(generics.ListAPIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = AnswersSection.objects.all()
        data = {
            'Answer for Section': list(queryset.values())
        }
        return Response(data)
    serializer_class = SectionsSerializer

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

######################################### CRUD quiz section ##################################################
# Créer un quiz pour la section
class QuizSectionCreate(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @csrf_exempt
    def post(self, request, format=None):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        id_section = request.POST.get('id_section', None)
        if not id_section:
            return HttpResponse("Le champ id_section est requis.")
        quiz_question_name = request.POST.get('quiz_question_name', None)
        if not quiz_question_name:
            return HttpResponse("Le champ quiz_question_name est requis.")
        quiz_question_points = request.POST.get('quiz_question_points', None)
        if not quiz_question_points:
            return HttpResponse("Le champ quiz_question_points est requis.")
        quiz_question_type = request.POST.get('quiz_question_type', None)
        if not quiz_question_type:
            return HttpResponse("Le champ quiz_question_type est requis.")
        quiz_question_media = request.FILES.get('quiz_question_media', None)
        if not quiz_question_media:
            return HttpResponse("Le champ quiz_question_media est requis.")
        quiz_description = request.POST.get('quiz_description', None)
        if not quiz_description:
            return HttpResponse("Le champ quiz_description est requis.")

        # user = request.user
        
        try:
            section = Sections.objects.get(id_section=id_section)
        except Sections.DoesNotExist:
            return HttpResponse("La Section spécifié n'existe pas.")
        
        quiz_section = QuizSection(
            id_section=section, 
            quiz_question_name=quiz_question_name,
            quiz_question_points=quiz_question_points,
            quiz_question_type=quiz_question_type,
            quiz_question_media=quiz_question_media,
            quiz_description=quiz_description,
            # user=user
        )
        quiz_section.save()

        data = {'message': 'Quiz ajouté avec succès'}
        return JsonResponse(data)
    
    def get(self, request, format=None):
        return JsonResponse({'error': 'Méthode non autorisée'})
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# modifier un quiz
class ModifierSectionQuiz(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self, quiz_section_id):
        try:
            return QuizSection.objects.get(id_quiz_section=quiz_section_id)
        except QuizSection.DoesNotExist:
            raise Http404

    def put(self, request, quiz_section_id):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)

        quiz_section = self.get_object(quiz_section_id)

        section_quiz = request.data.get('id_section')
        if section_quiz:
            sections = Sections.objects.get(id_section=section_quiz)
            quiz_section.id_section = sections
        quiz_section.quiz_question_name = request.data.get('quiz_question_name', quiz_section.quiz_question_name)
        quiz_section.quiz_question_points = request.data.get('quiz_question_points', quiz_section.quiz_question_points)
        quiz_section.quiz_question_type = request.data.get('quiz_question_type', quiz_section.quiz_question_type)
        quiz_section.quiz_question_media = request.data.get('quiz_question_media', quiz_section.quiz_question_media)
        quiz_section.quiz_description = request.data.get('quiz_description', quiz_section.quiz_description)
        quiz_section.save()

        data = {'message': 'Quiz modifié avec succès'}
        return JsonResponse(data)

    def get(self, request, countrie_id, format=None):
        return JsonResponse({'error': 'Méthode non autorisée'})
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
    
# liste des quizs
class QuizSectionList(generics.ListAPIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = QuizSection.objects.all()
        data = {
            'Quizs': list(queryset.values())
        }
        return Response(data)
    serializer_class = QuizSectionSerializer

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

######################################### CRUD chapter ##################################################
# Créer une chapter
class ChapterCreate(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @csrf_exempt
    def post(self, request, format=None):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        id_section = request.POST.get('id_section', None)
        if not id_section:
            return HttpResponse("Le champ id_section est requis.")
        chapter_name = request.POST.get('chapter_name', None)
        if not chapter_name:
            return HttpResponse("Le champ chapter_name est requis.")
        chapter_description = request.POST.get('chapter_description', None)
        if not chapter_description:
            return HttpResponse("Le champ chapter_description est requis.")

        # user = request.user
        
        try:
            section = Sections.objects.get(id_section=id_section)
        except Sections.DoesNotExist:
            return HttpResponse("La Section spécifié n'existe pas.")
        
        chapters = Chapters(
            id_section=section, 
            # chapter_order=chapter_order,
            chapter_name=chapter_name,
            chapter_description=chapter_description,
            # user=user
        )
        chapters.save()

        data = {'message': 'Chapter ajouté avec succès'}
        return JsonResponse(data)
    
    def get(self, request, format=None):
        return JsonResponse({'error': 'Méthode non autorisée'})
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# liste des chapters
class ChapterList(generics.ListAPIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Chapters.objects.all()
        data = {
            'Chapitres': list(queryset.values())
        }
        return Response(data)
    serializer_class = ChaptersSerializer

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# modifier une section
class ModifierChapter(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self, chapter_id):
        try:
            return Chapters.objects.get(id_chapter=chapter_id)
        except Chapters.DoesNotExist:
            raise Http404

    def put(self, request, chapter_id):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)

        chapters = self.get_object(chapter_id)

        section = request.data.get('id_section')
        if section:
            sections = Sections.objects.get(id_section=section)
            chapters.id_section = sections
        chapters.chapter_name = request.data.get('chapter_name', chapters.chapter_name)
        chapters.chapter_description = request.data.get('chapter_description', chapters.chapter_description)
        chapters.save()

        data = {'message': 'Chapter modifié avec succès'}
        return JsonResponse(data)

    def get(self, request, countrie_id, format=None):
        return JsonResponse({'error': 'Méthode non autorisée'})

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
    
# supprimer un training
class DeleteChapter(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, chapter_id):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        chapter = self.get_Training(chapter_id)

        chapter.delete()

        data = {'message': 'Chapitre supprimé avec succès.'}
        return JsonResponse(data)
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

######################################### CRUD section ##################################################
# Créer une section
class SectionCreate(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @csrf_exempt
    def post(self, request, format=None):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        id_formation = request.POST.get('id_formation', None)
        if not id_formation:
            return HttpResponse("Le champ id_formation est requis.")
        sections_order = request.POST.get('sections_order', None)
        if not sections_order:
            return HttpResponse("Le champ sections_order est requis.")
        sections_name = request.POST.get('sections_name', None)
        if not sections_name:
            return HttpResponse("Le champ sections_name est requis.")
        
        try:
            training = Training.objects.get(id_training=id_formation)
        except Training.DoesNotExist:
            return HttpResponse("La Formation spécifié n'existe pas.")
        
        try:
            produit = Produit.objects.get(id_product=sections_order)
        except Produit.DoesNotExist:
            return HttpResponse("Le Produit spécifié n'existe pas.")
        
        sections = Sections(
            sections_name=sections_name, 
            id_formation=training,
            sections_order=produit
        )
        sections.save()

        data = {'message': 'Section ajouté avec succès'}
        return JsonResponse(data)
    def get(self, request, format=None):
        return JsonResponse({'error': 'Méthode non autorisée'})
    
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
    
# liste des sections
class SectionList(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    serializer_class = SectionsSerializer

    def get_queryset(self):
        queryset = Sections.objects.all()
        return queryset

    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        for section in data:
            chapter_queryset = Chapters.objects.filter(id_section=section['id_section'])
            chapter_serializer = ChaptersSerializer(chapter_queryset, many=True)
            section['chapters'] = chapter_serializer.data

            quiz_queryset = QuizSection.objects.filter(id_section=section['id_section'])
            quiz_serializer = QuizSectionSerializer(quiz_queryset, many=True)
            section['quizzes'] = quiz_serializer.data

            for quiz in section['quizzes']:
                answer_queryset = AnswersSection.objects.filter(id_quiz=quiz['id_quiz_section'])
                answer_serializer = AnswersSectionSerializer(answer_queryset, many=True)
                quiz['answers'] = answer_serializer.data
        return Response(data)

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# modifier une section
class ModifierSection(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self, section_id):
        try:
            return Sections.objects.get(id_section=section_id)
        except Sections.DoesNotExist:
            raise Http404

    def put(self, request, section_id):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)

        section = self.get_object(section_id)

        training = request.data.get('id_formation')
        if training:
            trainings = Training.objects.get(id_training=training)
            section.id_formation = trainings
        produit = request.data.get('sections_order')
        if produit:
            produits = Produit.objects.get(id_product=produit)
            section.sections_order = produits
        section.sections_name = request.data.get('sections_name', section.sections_name)
        section.save()

        data = {'message': 'Section modifié avec succès'}
        return JsonResponse(data)

    def get(self, request, countrie_id, format=None):
        return JsonResponse({'error': 'Méthode non autorisée'})
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# supprimer un training
class DeleteSection(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, section_id):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        section = self.get_Training(section_id)

        section.delete()

        data = {'message': 'Section supprimé avec succès.'}
        return JsonResponse(data)
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
    
######################################### CRUD training ##################################################
# liste des training
class TrainingList(generics.ListAPIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Training.objects.all()
        data = {
            'Formations': list(queryset.values()),
        }
        return Response(data)
    serializer_class = TrainingSerializer

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# Créer un training
class TrainingCreate(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @csrf_exempt
    def post(self, request, format=None):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        id_client = request.POST.get('id_client', None)
        if not id_client:
            return HttpResponse("Le champ id_client est requis.")
        countrie_id = request.POST.get('countrie_id', None)
        if not countrie_id:
            return HttpResponse("Le champ countrie_id est requis.")
        produit_id = request.POST.get('produit_id', None)
        if not produit_id:
            return HttpResponse("Le champ produit_id est requis.")
        training_name = request.POST.get('training_name', None)
        if not training_name:
            return HttpResponse("Le champ training_name est requis.")
        training_onBoarding = request.POST.get('training_onBoarding', None)
        if not training_onBoarding:
            return HttpResponse("Le champ training_onBoarding est requis.")
        training_min_score = request.POST.get('training_min_score', None)
        if not training_min_score:
            return HttpResponse("Le champ training_min_score est requis.")
        training_description = request.POST.get('training_description', None)
        if not training_description:
            return HttpResponse("Le champ training_description est requis.")
        training_mode = request.POST.get('training_mode', None)
        if not training_mode:
            return HttpResponse("Le champ training_mode est requis.")
        training_statut = request.POST.get('training_statut', None)
        if not training_statut:
            return HttpResponse("Le champ training_statut est requis.")
        training_category = request.POST.get('training_category', None)
        if not training_category:
            return HttpResponse("Le champ training_category est requis.")
        
        # user = request.user
        
        try:
            client = Clients.objects.get(id_client=id_client)
        except Clients.DoesNotExist:
            return HttpResponse("Le Client spécifié n'existe pas.")
        
        try:
            produit = Produit.objects.get(id_product=produit_id)
        except Produit.DoesNotExist:
            return HttpResponse("Le Produit spécifié n'existe pas.")
        
        try:
            country = Countries.objects.get(id_country=countrie_id)
        except Countries.DoesNotExist:
            return HttpResponse("Le Pays spécifié n'existe pas.")
        
        training = Training(
            id_client=client, 
            countrie_id=country,
            produit_id=produit,
            training_name=training_name,
            training_onBoarding=training_onBoarding,
            training_min_score=training_min_score,
            training_description=training_description,
            training_mode=training_mode,
            training_statut=training_statut,
            training_category=training_category,
            # user=user
        )
        training.save()

        data = {'message': 'Training ajouté avec succès'}
        return JsonResponse(data)
    
    def get(self, request, format=None):
        return JsonResponse({'error': 'Méthode non autorisée'})

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
    
# supprimer un training
class DeleteTraining(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, training_id):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        training = self.get_Training(training_id)

        training.delete()

        data = {'message': 'Training supprimé avec succès.'}
        return JsonResponse(data)

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# modifier un training
class ModifierTraining(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self, training_id):
        try:
            return Training.objects.get(id_training=training_id)
        except Training.DoesNotExist:
            raise Http404

    def put(self, request, training_id):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)

        training = self.get_object(training_id)

        country_id = request.data.get('countrie_id')
        if country_id:
            country = Countries.objects.get(id_country=country_id)
            training.countrie_id = country
        training.training_name = request.data.get('training_name', training.training_name)
        client_id = request.data.get('id_client')
        if client_id:
            client = Clients.objects.get(id_client=client_id)
            training.id_client = client
        produit = request.data.get('produit_id')
        if produit:
            produits = Produit.objects.get(id_product=produit)
            training.produit_id = produits
        training.training_onBoarding = request.data.get('training_onBoarding', training.training_onBoarding)
        training.training_min_score = request.data.get('training_min_score', training.training_min_score)
        training.training_description = request.data.get('training_description', training.training_description)
        training.training_mode = request.data.get('training_mode', training.training_mode)
        training.training_statut = request.data.get('training_statut', training.training_statut)
        training.training_category = request.data.get('training_category', training.training_category)
        training.save()

        training_serializer = TrainingSerializer(training)
        data = {
            'formations':training_serializer.data,
            'message': 'Formation modifié avec succès'
        }
        return JsonResponse(data)

    def get(self, request, countrie_id, format=None):
        return JsonResponse({'error': 'Méthode non autorisée'})

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

######################################## settings_privilege CRUD ################################################
# Ajouter un nouveau settings_privilege
class AjouterPrivilege(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @csrf_exempt
    def post(self, request, format=None):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        name = request.POST.get('name', None)
        if not name:
            return HttpResponse("Le champ name est requis.")
        description = request.POST.get('description', None)
        if not description:
            return HttpResponse("Le champ description est requis.")

        privilege = Privilege(
            name=name, 
            description=description,
        )
        privilege.save()

        data = {'message': 'Privilege ajouté avec succès'}
        return JsonResponse(data)

    def get(self, request, format=None):
        return JsonResponse({'error': 'Méthode non autorisée'})
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# list des privilèges
class ListePrivilege(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        privilege = Privilege.objects.all()
        data = {
            'Privilèges': list(privilege.values()),
        }
        return Response(data)

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
      
######################################## settings_typeID CRUD ################################################
# Ajouter un nouveau settings_typeID
class AjouterTypeId(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @csrf_exempt
    def post(self, request, format=None):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        id_name = request.POST.get('id_name', None)
        if not id_name:
            return HttpResponse("Le champ id_name est requis.")
        id_country = request.POST.get('id_country', None)
        if not id_country:
            return HttpResponse("Le champ id_country est requis.")
        
        try:
            country = Countries.objects.get(id_country=id_country)
        except Countries.DoesNotExist:
            return HttpResponse("Le TypeID spécifié n'existe pas.")
        
        type_id = TypeID(
            id_name=id_name, 
            id_country=country
        )
        type_id.save()

        data = {'message': 'TypeID ajouté avec succès'}
        return JsonResponse(data)

    def get(self, request, format=None):
        return JsonResponse({'error': 'Méthode non autorisée'})
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
    
# modifier un settings_typeID
class ModifierTypeId(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self, type_id):
        try:
            return TypeID.objects.get(id_type=type_id)
        except TypeID.DoesNotExist:
            raise Http404
        
    def put(self, request, type_id):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        type = self.get_object(type_id)
        type.id_name = request.data.get('id_name', type.id_name)
        
        # récupérer l'objet Countries correspondant à partir de son ID et l'assigner au champ id_country
        country_id = request.data.get('id_country')
        if country_id:
            country = Countries.objects.get(id_country=country_id)
            type.id_country = country
        
        type.save()

        data = {'message': 'TypeID modifié avec succès'}
        return JsonResponse(data)

    def get(self, request, *args, **kwargs):
        # retourne un message d'erreur indiquant que cette vue ne prend pas en charge les requêtes GET
        data = {'error': 'Cette vue ne prend pas en charge les requêtes GET.'}
        return JsonResponse(data)
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# supprimer un settings_typeID
class DeleteTypeId(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, type_id):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        typeid = self.get_typeId(type_id)

        typeid.delete()

        data = {'message': 'typeID supprimé avec succès.'}
        return JsonResponse(data)
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
    
# list des settings_typeID
class ListeTypeId(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        counts_by_country = TypeID.objects.values('id_country__country_name').annotate(count=Count('id_country'))
        data = {}
        for count in counts_by_country:
            data[count['id_country__country_name']] = count['count']
        return Response(data)

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
      
######################################## settings_levef_of_study CRUD ################################################
# Ajouter un nouveau settings_level
class AjouterEducationLevel(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @csrf_exempt
    def post(self, request, format=None):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        level_name = request.POST.get('level_name', None)
        if not level_name:
            return HttpResponse("Le champ level_name est requis.")
        id_country = request.POST.get('id_country', None)
        if not id_country:
            return HttpResponse("Le champ id_country est requis.")
        
        try:
            country = Countries.objects.get(id_country=id_country)
        except Countries.DoesNotExist:
            return HttpResponse("Le TypeID spécifié n'existe pas.")
        
        level_education = EducationLevel(
            level_name=level_name, 
            id_country=country
        )
        level_education.save()

        data = {'message': 'TypeID ajouté avec succès'}
        return JsonResponse(data)

    def get(self, request, format=None):
        return JsonResponse({'error': 'Méthode non autorisée'})
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
    
# modifier un settings_level
class ModifierEducationLevel(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self, education_id):
        try:
            return EducationLevel.objects.get(id_education=education_id)
        except EducationLevel.DoesNotExist:
            raise Http404

    def put(self, request, education_id):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        education = self.get_object(education_id)
        education.level_name = request.data.get('level_name', education.level_name)

        # récupérer l'objet Countries correspondant à partir de son ID et l'assigner au champ id_country
        country_id = request.data.get('id_country')
        if country_id:
            country = Countries.objects.get(id_country=country_id)
            education.id_country = country

        education.save()

        data = {'message': 'Education Level modifié avec succès'}
        return JsonResponse(data)

    def get(self, request, id_country, format=None):
        return JsonResponse({'error': 'Méthode non autorisée'})
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# supprimer un settings_level
class DeleteEducationLevel(APIView):

    def delete(self, request, education_id):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        education = self.get_educationLevel(education_id)

        education.delete()

        data = {'message': 'educationLevel supprimé avec succès.'}
        return JsonResponse(data)
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
    
# list des settings_level
class ListeEducationLevel(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        counts_by_country = EducationLevel.objects.values('id_country__country_name').annotate(count=Count('id_country'))
        count_list = [count['count'] for count in counts_by_country]
        total_level = sum(count_list)
        data = {'Total_level': total_level}
        for count in counts_by_country:
            data[count['id_country__country_name']] = count['count']
        return Response(data)

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
      
######################################## settings_countries CRUD ################################################
# Ajouter un nouveau settings_countries
class AjouterCountries(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @csrf_exempt
    def post(self, request, format=None):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        country_name = request.data.get('country_name', None)
        if not country_name:
            return HttpResponse("Le champ country_name est requis.", status=400)
        country_prefixe = request.data.get('country_prefixe', None)
        if not country_prefixe:
            return HttpResponse("Le champ country_prefixe est requis.", status=400)
        flag = request.data.get('flag', None)
        if not flag:
            return HttpResponse("Le champ flag est requis.", status=400)

        countries = Countries(country_name=country_name,
                              country_prefixe=country_prefixe,
                              flag=flag)
        countries.save()

        # Mettre à jour le nombre de clients associés à ce pays
        num_clients = Clients.objects.filter(country_id=countries).count()
        countries.numbers_of_clients = num_clients
        countries.save()

        data = {'message': 'Countries ajouté avec succès',
                'number_of_clients': num_clients}
        return JsonResponse(data)
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
    
# Afficher les détails d'un countries
class DetailsCountries(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, country_id, format=None):
        try:
            countries = Countries.objects.get(id_country=country_id)
        except Countries.DoesNotExist:
            data = {'message':"Le pays n'existe pas"}
            return JsonResponse(data, status=404)
            
        data = {
            'country_name': countries.country_name,
            'country_prefixe': countries.country_prefixe,
            'country_name': countries.country_name,
            'flag': request.build_absolute_uri(countries.flag.url),
            'numbers_of_clients': countries.numbers_of_clients,
        }

        return Response(data)
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
    
# Lister des countries
class ListeCountries(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        countries = Countries.objects.all()
        data = {
            'Pays': list(countries.values())
        }
        return Response(data)
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
    
# modifier un countrie_setting
class ModifierCountries(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self, country_id):
        try:
            return Countries.objects.get(id_country=country_id)
        except Countries.DoesNotExist:
            raise Http404

    def put(self, request, country_id):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        countries = self.get_object(country_id)
        countries.country_name = request.data.get('country_name', countries.country_name)
        countries.country_prefixe = request.data.get('country_prefixe', countries.country_prefixe)
        countries.flag = request.data.get('flag', countries.flag)
        countries.save()

        data = {'message': 'Pays modifié avec succès'}
        return JsonResponse(data)

    def get(self, request, id_country, format=None):
        return JsonResponse({'error': 'Méthode non autorisée'})
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# Supprimer un countries existant
class DeleteCountriesView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, country_id):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)

        countries = self.get_kyc(country_id)
        countries.delete()

        data = {'message': 'Pays supprimé avec succès.'}
        return JsonResponse(data)

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
    
######################################## pos CRUD ################################################
# affichage des Pos
class ListPosView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):

        pos = Pos.objects.filter()
        # récupérer tous les objets Pos
        total_pos_active = pos.aggregate(Sum('pos_active'))['pos_active__sum']
        total_numb_pos = pos.aggregate(Sum('numb_pos'))['numb_pos__sum']
        total_pos_indication = pos.aggregate(Sum('pos_indication'))['pos_indication__sum']

        # sérialiser les objets Pos
        serializer = PosSerializer(pos, many=True)

        # renvoyer la réponse avec les objets sérialisés
        return Response({
        'Pos': serializer.data,
        'total_pos_active': total_pos_active,
        'total_numb_pos': total_numb_pos,
        'total_pos_indication': total_pos_indication
    })

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# pos for client
class ClientPosView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        client_id = user.the_client.id_client
        pos = Pos.objects.filter(pos_client=client_id).values()
        pos_list = list(pos.values())
        # récupérer tous les objets Pos
        total_pos_active = pos.aggregate(Sum('pos_active'))['pos_active__sum']
        total_numb_pos = pos.aggregate(Sum('numb_pos'))['numb_pos__sum']
        total_pos_indication = pos.aggregate(Sum('pos_indication'))['pos_indication__sum']

        return Response({
        'Pos': pos_list,
        'total_pos_active': total_pos_active,
        'total_numb_pos': total_numb_pos,
        'total_pos_indication': total_pos_indication
    })
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# ajout d'un POS
class CreatePosView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        file = request.FILES.get('file')
        pos_countrie = request.data.get('pos_countrie')
        pos_client = request.data.get('pos_client')

        if not file and (not pos_countrie or not pos_client):
            return Response({'error': 'Fichier ou informations sur la cible non trouvés'})

        try:
            sheet_name = 'Sheet'
            if file:
                # sheet_name = file.name 
                df = pd.read_excel(file)
            else:
                df = pd.DataFrame(request.data)

            for index, row in df.iterrows():
                pos_name = row['pos_name'].strip().lower()
                pos_long = row['pos_long']
                pos_lat = row['pos_lat']

                pos_exists = Pos.objects.filter(pos_countrie_id=pos_countrie,
                                                pos_client_id=pos_client,
                                                pos_name=pos_name,
                                                pos_long=pos_long,
                                                pos_lat=pos_lat).exists()
                if not pos_exists:
                    pos = Pos(
                        pos_countrie_id=pos_countrie,
                        pos_client_id=pos_client,
                        pos_name=pos_name,
                        pos_long=pos_long,
                        pos_lat=pos_lat,
                        pos_active=row['pos_active'],
                        numb_pos=row['numb_pos'],
                        pos_indication=row['pos_indication']
                    )
                    pos.save()

            return Response({'success': f'Données importées avec succès depuis le fichier "{sheet_name}"'})
        except Exception as e:
            return Response({'error': str(e)})
        
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

######################################## target CRUD ################################################
# ajout d'un target
class AjouterTargetView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, format=None):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        file = request.FILES.get('file')
        target_countrie = request.data.get('target_countrie')
        target_client = request.data.get('target_client')

        if not file and (not target_countrie or not target_client):
            return Response({'error': 'Fichier ou informations sur la cible non trouvés'})

        try:
            sheet_name = 'Sheet'
            if file:
                # sheet_name = file.name 
                df = pd.read_excel(file)
            else:
                df = pd.DataFrame(request.data)

            for index, row in df.iterrows():
                target_zone = row['target_zone'].strip().lower()
                target_month = row['target_month']

                target_exists = Target.objects.filter(target_countrie_id=target_countrie,
                                                       target_client_id=target_client,
                                                       target_zone=target_zone,
                                                       target_month=target_month).exists()
                if not target_exists:
                    target = Target(
                        target_countrie_id=target_countrie,
                        target_client_id=target_client,
                        target_zone=target_zone,
                        target_month=target_month,
                        target_moderm=row['target_moderm'],
                        target_routeurs=row['target_routeurs'],
                        target_airtelmoney=row['target_airtelmoney']
                    )
                    target.save()

            return Response({'success': f'Données importées avec succès depuis le fichier "{sheet_name}"'})
        except Exception as e:
            return Response({'error': str(e)})
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# affichage de tous les targets
class TargetListView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        targets = Target.objects.all()
        # récupérer tous les objets Targets
        total_target_moderm = targets.aggregate(Sum('target_moderm'))['target_moderm__sum']
        total_target_routeurs = targets.aggregate(Sum('target_routeurs'))['target_routeurs__sum']
        total_target_airtelmoney = targets.aggregate(Sum('target_airtelmoney'))['target_airtelmoney__sum']

        serializer = TargetSerializer(targets, many=True)

        return Response({
        'targets': serializer.data,
        'total_target_moderm': total_target_moderm,
        'total_target_routeurs': total_target_routeurs,
        'total_target_airtelmoney': total_target_airtelmoney
        })

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# target for client view
class ClientTargetsView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    serializer_class = TargetSerializer

    def get(self, request):
        user = request.user
        targets = Target.objects.filter(target_client=user.the_client)
        targets_list = list(targets.values())
        # récupérer tous les objets Targets
        total_target_moderm = targets.aggregate(Sum('target_moderm'))['target_moderm__sum']
        total_target_routeurs = targets.aggregate(Sum('target_routeurs'))['target_routeurs__sum']
        total_target_airtelmoney = targets.aggregate(Sum('target_airtelmoney'))['target_airtelmoney__sum']

        return Response({
        'targets': targets_list,
        'total_target_moderm': total_target_moderm,
        'total_target_routeurs': total_target_routeurs,
        'total_target_airtelmoney': total_target_airtelmoney
        })

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

class ModifierTarget(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, target_id):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)

        try:
            target = Target.objects.get(id_target=target_id)
        except Target.DoesNotExist:
            return Response({'error': 'Target non trouvée'}, status=status.HTTP_404_NOT_FOUND)

        target.target_countrie = request.data.get('target_countrie', target.target_countrie)
        target.target_client = request.data.get('target_client', target.target_client)
        target.target_zone = request.data.get('target_zone', target.target_zone)
        target.target_month = request.data.get('target_month', target.target_month)
        target.target_moderm = request.data.get('target_moderm', target.target_moderm)
        target.target_routeurs = request.data.get('target_routeurs', target.target_routeurs)
        target.target_airtelmoney = request.data.get('target_airtelmoney', target.target_airtelmoney)
        target.save()

        return Response({'message': 'Target modifiée avec succès'}, status=status.HTTP_200_OK)
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

class SupprimerTarget(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, target_id):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)

        target = Target.objects.get(id_target=target_id)
        target.delete()

        return Response({'message': 'Target supprimée avec succès'})
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
    
######################################## KYC CRUD ###################################################
# Ajouter un nouveau KYC
class AjouterKYCView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        prenoms = request.data.get('prenoms', None)
        if not prenoms:
            return HttpResponse("Le champ prenoms est requis.", status=400)
        nom = request.data.get('nom', None)
        if not nom:
            return HttpResponse("Le champ nom est requis.", status=400)
        username = request.data.get('username', None)
        if not username:
            return HttpResponse("Le champ username est requis.", status=400)
        clients_kyc_id = request.data.get('clients_kyc_id', None)
        if not clients_kyc_id:
            return HttpResponse("Le champ clients_kyc_id est requis.", status=400)
        country_kyc_id = request.data.get('country_kyc_id', None)
        if not country_kyc_id:
            return HttpResponse("Le champ country_kyc_id est requis.", status=400)

        kyc = Kyc(prenoms=prenoms,
                  nom=nom,
                  country_kyc_id=country_kyc_id,
                  clients_kyc_id=clients_kyc_id,
                  username=username)
        kyc.save()

        data = {'message': 'KYC ajouté avec succès'}
        return JsonResponse(data)

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# Lister tous les KYC
class ListeKYC(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):        

        kycs = Kyc.objects.all()
        data = {'Kyc': list(kycs.values())}
        return Response(data)
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
    
# Mettre à jour un kyc existant
class UpdateKYCView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self, kyc_id):
        try:
            return Kyc.objects.get(id=kyc_id)
        except Kyc.DoesNotExist:
            raise Http404

    def put(self, request, kyc_id):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        kyc = self.get_object(kyc_id)

        kyc.createdAt = request.data.get('createdAt', kyc.createdAt)
        kyc.prenoms = request.data.get('prenoms', kyc.prenoms)
        kyc.nom = request.data.get('nom', kyc.nom)
        kyc.clients_kyc_id = request.data.get('clients_kyc_id', kyc.clients_kyc_id)
        kyc.country_kyc_id = request.data.get('country_kyc_id', kyc.country_kyc_id)
        kyc.save()

        data = {'message': 'KYC modifié avec succès'}
        return JsonResponse(data)
    
    # def handle_exception(self, exc):
    #     data = {}
    #     if isinstance(exc, AuthenticationFailed):
    #         data['token_status'] = 'Token Invalide'
    #         return Response(data, status=status.HTTP_401_UNAUTHORIZED)
    #     return super().handle_exception(exc)
    
# Supprimer un produit existant
class DeleteKycView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, kyc_id):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)

        kyc = self.get_kyc(kyc_id)

        kyc.delete()

        data = {'message': 'Objet KYC supprimé avec succès.'}
        return JsonResponse(data)
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
    
######################################## FootSoldiers CRUD ################################################
# Lister tous les footsoldiers
class ListeFootsoldiersView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        footsoldiers = Footsoldiers.objects.all()
        data = {'footsoldiers': list(footsoldiers.values())}
        return JsonResponse(data)
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# footsoldiers for client
class ClientFootsoldiersView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    serializer_class = FootsoldiersSerializer

    def get(self, request):
        user = request.user
        footsoldiers = Footsoldiers.objects.filter(footsoldiers_clients=user.the_client)
        serializer = self.serializer_class(footsoldiers, many=True)
        return Response(serializer.data)

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
    
# Ajouter un nouveau userclient
class AjouterFootsoldiers(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @csrf_exempt
    def post(self, request):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        footsoldiers_phonenumber = request.POST.get('footsoldiers_phonenumber')
        if not footsoldiers_phonenumber:
            return HttpResponse("Le champ footsoldiers_phonenumber est requis.", status=400)

        footsoldiers_fullname = request.POST.get('footsoldiers_fullname')
        if not footsoldiers_fullname:
            return HttpResponse("Le champ footsoldiers_fullname est requis.", status=400)

        footsoldiers_zone = request.POST.get('footsoldiers_zone')
        if not footsoldiers_zone:
            return HttpResponse("Le champ footsoldiers_zone est requis.", status=400)

        footsoldiers_clients_id = request.POST.get('footsoldiers_clients_id')
        if not footsoldiers_clients_id:
            return HttpResponse("Le champ footsoldiers_clients_id est requis.", status=400)

        footsoldiers_country_id = request.POST.get('footsoldiers_country_id')
        if not footsoldiers_country_id:
            return HttpResponse("Le champ footsoldiers_country_id est requis.", status=400)

        footsoldiers = Footsoldiers(
            footsoldiers_phonenumber=footsoldiers_phonenumber,
            footsoldiers_fullname=footsoldiers_fullname,
            footsoldiers_zone=footsoldiers_zone,
            footsoldiers_clients_id=footsoldiers_clients_id,
            footsoldiers_country_id=footsoldiers_country_id
        )
        footsoldiers.save()

        data = {'message': 'footsoldiers ajouté avec succès'}
        return JsonResponse(data)

    def get(self, request):
        return JsonResponse({'error': 'Méthode non autorisée'})

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
    
# Mettre à jour un footsoldiers existant
class UpdateFootsoldiersView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self, footsoldiers_id):
        try:
            return Footsoldiers.objects.get(id_footsoldiers=footsoldiers_id)
        except Footsoldiers.DoesNotExist:
            raise Http404

    def put(self, request, footsoldiers_id):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)

        footsoldiers = self.get_object(footsoldiers_id)
        
        # Récupération des données à mettre à jour
        footsoldiers_country = request.data.get('footsoldiers_country', footsoldiers.footsoldiers_country_id)
        footsoldiers_phonenumber = request.data.get('footsoldiers_phonenumber', footsoldiers.footsoldiers_phonenumber)
        footsoldiers_fullname = request.data.get('footsoldiers_fullname', footsoldiers.footsoldiers_fullname)
        footsoldiers_zone = request.data.get('footsoldiers_zone', footsoldiers.footsoldiers_zone)
        footsoldiers_clients = request.data.get('footsoldiers_clients', footsoldiers.footsoldiers_clients_id)
        footsoldiers_picture = request.data.get('footsoldiers_picture', footsoldiers.footsoldiers_picture)

        # Mise à jour des données
        footsoldiers.footsoldiers_country_id = footsoldiers_country
        footsoldiers.footsoldiers_phonenumber = footsoldiers_phonenumber
        footsoldiers.footsoldiers_fullname = footsoldiers_fullname
        footsoldiers.footsoldiers_zone = footsoldiers_zone
        footsoldiers.footsoldiers_clients_id = footsoldiers_clients
        footsoldiers.footsoldiers_picture = footsoldiers_picture
        footsoldiers.save()

        data = {'message': 'Footsoldiers modifié avec succès'}
        return JsonResponse(data)

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
    
# Supprimer un produit existant
class DeleteFootsoldiersView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, footsoldiers_id):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)

        footsoldiers = self.get_object(footsoldiers_id)
        footsoldiers.delete()

        data = {'message': 'Footsoldiers supprimé avec succès'}
        return JsonResponse(data)
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

######################################## Clients CRUD #################################################
# list des clients
class ClientsList(generics.ListAPIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    serializer_class = ClientsSerializer
    def get_queryset(self):
        return Clients.objects.all()
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# AJouter un client
class CreateClient(generics.CreateAPIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @csrf_exempt
    def post(self, request, format=None):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        country_id = request.data.get('country_id', None)
        if not country_id:
            return HttpResponse("Le champ country_id est requis.", status=400)
        client_logo = request.data.get('client_logo', None)
        if not client_logo:
            return HttpResponse("Le champ client_logo est requis.", status=400)
        client_industry = request.data.get('client_industry', None)
        if not client_industry:
            return HttpResponse("Le champ client_industry est requis.", status=400)

        client_name = request.data.get('client_name', None)
        if not client_name:
            return HttpResponse("Le champ client_name est requis.", status=400)

        client_status = request.data.get('client_status', None)
        if not client_status:
            return HttpResponse("Le champ client_status est requis.", status=400)

        try:
            country = Countries.objects.get(id_country=country_id)
        except Countries.DoesNotExist:
            data = {'message':'Le pays spécifié existe pas.'}
            return HttpResponse(data)
        
        try:
            industry = Industry.objects.get(id_industry=client_industry)
        except Countries.DoesNotExist:
            data = {'message':'Le pays spécifié existe pas.'}
            return HttpResponse(data)

        clients = Clients(country_id=country,
                              client_industry=industry,
                              client_logo=client_logo,
                              client_name=client_name,
                              client_status=client_status
                              )
        clients.save()

        data = {'message': 'Client ajouté avec succès'}
        return JsonResponse(data)

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# Afficher les détails d'un client
class DetailsClient(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, client_id, format=None):
        try:
            clients = Clients.objects.get(id_client=client_id)
        except Clients.DoesNotExist:
            data = {'message':"Le Client n'existe pas"}
            return JsonResponse(data, status=404)
            
        data = {
            'client_name': clients.client_name,
            'client_status': clients.client_status,
            'country_id': clients.country_id.id_country,
            'client_logo': request.build_absolute_uri(clients.client_logo.url),
            'client_industry': clients.client_industry.id_industry,
        }

        return Response(data)
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
    
# modifier un client
class ClientsUpdate(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self, client_id):
        try:
            return Clients.objects.get(id_client=client_id)
        except Clients.DoesNotExist:
            raise Http404

    def put(self, request, client_id):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        clients = self.get_object(client_id)
        clients.client_name = request.data.get('client_name', clients.client_name)
        clients.client_status = request.data.get('client_status', clients.client_status)
        clients.client_logo = request.data.get('client_logo', clients.client_logo)
        country_id = request.data.get('id_country')
        if country_id:
            country = Countries.objects.get(id_country=country_id)
            clients.id_country = country
        client_industry = request.data.get('id_industry')
        if client_industry:
            industry = Industry.objects.get(id_industry=client_industry)
            clients.id_industry = industry
        clients.save()

        data = {'message': 'Client modifié avec succès'}
        return JsonResponse(data)
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# supprimer un client
class ClientsDelete(generics.DestroyAPIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    serializer_class = ClientsSerializer

    def delete(self, request, id_client):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        client = self.get_object(id_client)
        client.delete()
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

######################################## Product CRUD ###################################################
# Lister tous les produits
class ProduitListView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        produits = Produit.objects.all()
        data = {'produits': list(produits.values())}
        return Response(data)

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
    
# liste des produits par client
class ProductListByClientView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    serializer_class = ProduitSerializer

    def get(self, request):
        user = request.user
        produits = Produit.objects.filter(client_id=user.the_client.id_client)
        serialized_produits = self.serializer_class(produits, many=True)
        return Response(serialized_produits.data)

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
    

# Afficher les détails d'un produit spécifique
class DetailsProduit(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, produit_id, format=None):

        try:
            produit = Produit.objects.get(id_product=produit_id)
        except Produit.DoesNotExist:
            return JsonResponse({'error': "Le produit n'existe pas"}, status=404)

        data = {
            'id_product': produit.id_product,
            'product_name': produit.product_name,
            'price': produit.product_price,
            'Icone': produit.product_picture,
            'client': produit.client_id,
            'pays': produit.country_id,
            'user': produit.user_id,
        }

        return JsonResponse(data)
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
    
# Ajouter un nouveau produit
class ProduitCreateView(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @csrf_exempt
    def post(self, request, *args, **kwargs):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        product_picture = request.FILES.get('product_picture', None)
        if not product_picture:
            return HttpResponse("Le champ product_picture est requis.", status=400)
        product_name = request.POST.get('product_name', None)
        if not product_name:
            return HttpResponse("Le champ product_name est requis.", status=400)
        product_price = request.POST.get('product_price', None)
        if not product_price:
            return HttpResponse("Le champ product_price est requis.", status=400)
        product_commission = request.POST.get('product_commission', None)
        if not product_commission:
            return HttpResponse("Le champ product_commission est requis.", status=400)
        country_id = request.POST.get('country_id', None)
        if not country_id:
            return HttpResponse("Le champ country_id est requis.", status=400)
        client_id = request.POST.get('client_id', None)
        if not client_id:
            return HttpResponse("Le champ client_id est requis.", status=400)

        # user = request.user

        # if not user.is_superuser:
        #     try:
        #         privilege_admin = Privilege.objects.get(id=5)
        #     except Privilege.DoesNotExist:
        #         return HttpResponse("Le privilège 'admin' n'existe pas.")

        #     if not user.privilege == privilege_admin:
        #         return HttpResponse("Vous n'avez pas le droit de créer un utilisateur.")
            
        # création du nouveau produit
        produit = Produit(product_picture=product_picture, product_name=product_name,
                          product_price=product_price, product_commission=product_commission,
                          country_id=country_id, client_id=client_id)
        produit.save()

        data = {'message': 'Produit ajouté avec succès'}
        return JsonResponse(data)

    def get(self, request, *args, **kwargs):
        return JsonResponse({'error': 'Méthode non autorisée'})
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# Mettre à jour un produit existant
class ModifierProduit(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self, produit_id):
        try:
            return Produit.objects.get(id_product=produit_id)
        except Produit.DoesNotExist:
            raise Http404

    def put(self, request, produit_id):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        produit = self.get_object(produit_id)
        produit.product_name = request.data.get('product_name', produit.product_name)
        produit.product_price = request.data.get('product_price', produit.product_price)
        produit.product_commission = request.data.get('product_commission', produit.product_commission)
        country_id = request.data.get('country')
        if country_id:
            countries = Countries.objects.get(id_country=country_id)
            produit.country = countries
        client_id = request.data.get('client')
        if client_id:
            clients = Clients.objects.get(id_client=client_id)
            produit.client = clients
        produit.product_picture = request.data.get('product_picture', produit.product_picture)
        produit.save()

        data = {'message': 'Produit modifié avec succès'}
        return JsonResponse(data)

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# Supprimer un produit existant
class SupprimerProduit(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, produit_id, format=None):

        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        produit = get_object_or_404(Produit, id_product=produit_id)
        produit.delete()
        return Response({'message': 'Produit supprimé avec succès'}, status=status.HTTP_204_NO_CONTENT)
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

######################################## dashboard CRUD ###################################################
class DashboardView(generics.RetrieveUpdateAPIView):
    queryset = Dashboards.objects.all()
    serializer_class = DashboardsSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        # Récupérer le tableau de bord correspondant à l'utilisateur actuel
        dashboard, created = Dashboards.objects.get_or_create(user=user)
        return dashboard

class CreateDashboardView(generics.CreateAPIView):
    serializer_class = DashboardsSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

######################################## Domaine CRUD ###################################################
class AjouterDomaine(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @csrf_exempt
    def post(self, request, format=None):
        domaine_name = request.POST.get('domaine_name', None)
        if not domaine_name:
            return HttpResponse("Le champ domaine_name est requis.")
        
        domaine = Domaine(
            domaine_name=domaine_name,
        )
        domaine.save()

        data = {'message': 'Domaine ajouté avec succès'}
        return JsonResponse(data)

    def get(self, request, format=None):
        return JsonResponse({'error': 'Méthode non autorisée'})

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# list des domaines
class ListeDomaine(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        domaine = Domaine.objects.all()
        data = {
            'Domaines': list(domaine.values()),
        }
        return Response(data)

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
      
######################################## Locality CRUD ###################################################
# ajouter une localité
class AjouterLocality(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @csrf_exempt
    def post(self, request, format=None):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        locality_name = request.POST.get('locality_name', None)
        if not locality_name:
            return HttpResponse("Le champ locality_name est requis.")
        id_country = request.POST.get('id_country', None)
        if not id_country:
            return HttpResponse("Le champ id_country est requis.")

        try:
            country = Countries.objects.get(id_country=id_country)
        except Countries.DoesNotExist:
            return HttpResponse("Le Pays spécifié n'existe pas.")


        lacality = Locality(
            locality_name=locality_name, 
            country=country,
        )
        lacality.save()

        data = {'message': 'Localité ajouté avec succès'}
        return JsonResponse(data)

    def get(self, request, format=None):
        return JsonResponse({'error': 'Méthode non autorisée'})

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# list des localités
class ListeLocality(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        locality = Locality.objects.all()
        data = {
            'Localités': list(locality.values()),
        }
        return Response(data)

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)
      
######################################## Industry CRUD ###################################################
# ajouter une localité
class AjouterIndustrie(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @csrf_exempt
    def post(self, request, format=None):
        user = request.user
        if not user.is_superuser:
            try:
                privilege_admin = Privilege.objects.get(id=1)
            except Privilege.DoesNotExist:
                data = {'message':"Le privilège 'admin' n'existe pas."}
                return HttpResponse(data)

            if not user.privilege == privilege_admin:
                data = {'message':"Vous n'avez pas le droit de créer un utilisateur."}
                return HttpResponse(data)
        industry_name = request.POST.get('industry_name', None)
        if not industry_name:
            return HttpResponse("Le champ industry_name est requis.")
        industry_status = request.POST.get('industry_status', None)
        if not industry_status:
            return HttpResponse("Le champ industry_status est requis.")

        industry = Industry(
            industry_name=industry_name, 
            industry_status=industry_status,
        )
        industry.save()

        data = {'message': 'Industrie ajouté avec succès'}
        return JsonResponse(data)

    def get(self, request, format=None):
        return JsonResponse({'error': 'Méthode non autorisée'})

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

# list des localités
class ListeIndustry(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        industry = Industry.objects.all()
        data = {
            'Industries': list(industry.values()),
        }
        return Response(data)

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)




class TypeIDViewSet(viewsets.ModelViewSet):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = TypeID.objects.all()
    serializer_class = TypeIDSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_fields = ('id_country',)

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

class TypeIDList(generics.ListAPIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = TypeID.objects.all()
    serializer_class = TypeIDSerializer

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

class TypeIDDetail(generics.RetrieveAPIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = TypeID.objects.all()
    serializer_class = TypeIDSerializer

    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

class TypeIDViewSets(viewsets.ViewSet):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request, id_country_id=None):
        queryset = TypeID.objects.filter(id_country=id_country_id)
        serializer = TypeIDSerializer(queryset, many=True)
        return Response(serializer.data)
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

class TypeIDDetail(generics.RetrieveAPIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = TypeID.objects.all()
    serializer_class = TypeIDSerializer
    def get_queryset(self):
        id_country = self.kwargs.get('id_country')
        if id_country:
            queryset = TypeID.objects.filter(id_country=id_country)
        else:
            queryset = TypeID.objects.all()
        return queryset
    
    def handle_exception(self, exc):
        data = {}
        if isinstance(exc, AuthenticationFailed):
            data['token_status'] = 'Token Invalide'
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

class CountryViewSet(APIView):
    def get(self, request):
        countries = Countries.objects.all()
        serializer = CountrySerializer(countries, many=True)
        return Response(serializer.data)
        
    def post(self, request):
        serializer = CountrySerializer(data=request.data)

        if serializer.is_valid(raise_exception=False):
                    country = serializer.save()
                    return Response({"status": "ok", "message": f"Country {country.country_name} created"})
        else:
            errors = serializer.errors
            print(errors)
            data=json.dumps(errors)
            print(data)
            tab=[]
            default_errors = serializer.errors
            new_error = {}
            for field_name, field_errors in default_errors.items():
                new_error[field_name] = field_errors[0]

            return Response({"status": "nok", "message": new_error}, status=status.HTTP_400_BAD_REQUEST)
    
class clientsViewSet(viewsets.ModelViewSet):
    queryset = Clients.objects.all()
    serializer_class = ClientsSerializer
    filter_backends = (filters.DjangoFilterBackend,)

class EducationViewSet(viewsets.ModelViewSet):
    queryset = EducationLevel.objects.all()
    serializer_class = EducationSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_fields = ('id_country',)

class CreateUserView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = UserSerializer(data=request.data)
        
        print("test")
        if serializer.is_valid(raise_exception=False):
                    user = serializer.save()

                    # create a new Kyc object
                    kyc = Kyc.objects.create(
                        userId=user,
                        createdAt=timezone.now(),
                        email=user.email,
                        nom=user.nom,
                        prenoms=user.prenoms,
                        niveau_education=user.niveau_education,
                        localite=user.localite,
                        pays=user.pays,
                        username=user.username,
                        date_naissance=user.date_naissance,
                        lieu_naissance=user.lieu_naissance,
                        type_piece=user.type_piece,
                        numero_piece=user.numero_piece,
                        date_expiration=user.date_expiration,
                        photo_selfie=user.photo_selfie,
                        piece_recto=user.piece_recto,
                        piece_verso=user.piece_verso,
                        isNomOk=False,
                        isPrenomOk=False,
                        isTypepPieceOk=False,
                        isDateNaissanceOk=False,
                        isLieuNaissanceOk=False,
                        isTypePieceOk=False,
                        isNumeroPieceOk=False,
                        isDateExpirationOk=False,
                        isPhotoSelfieOk=False,
                        isPieceRectoOk=False,
                        isPieceVersoOk=False,
                        isAllok=False,
                    )

                    user.save()
                    kyc.save()

                    return Response({"status": "ok", "message": f"User {user.numero} created"})
        else:
            errors = serializer.errors
            print(errors)
            data=json.dumps(errors)
            print(data)
            tab=[]
            default_errors = serializer.errors
            new_error = {}
            for field_name, field_errors in default_errors.items():
                new_error[field_name] = field_errors[0]

            return Response(new_error, status=status.HTTP_400_BAD_REQUEST)

#curl -X POST http://localhost:8000/api/uploadImages/ -H "Content-Type: multipart/form-data" -b "cookie1=value1;cookie2=value2" -H "X-CSRFToken: GLafZcpiUT2sfwZwujowMWp0OtupUEcEZGNFgo7DtsLzgApRblL9pght8V6WlEYF" -F "file=@/Users/gillesgnanagbe/Desktop/Screenshot 2023-01-25 at 18.22.22.png“ 

def check_otp(request, token, otp):
    try:
        tp = TokenPin.objects.get(token=token)
    except TokenPin.DoesNotExist:
        return JsonResponse({'status':'404','error': 'Invalid token'}, status=404)
    if tp.pin != otp:
        return JsonResponse({'status':'401','error': 'Invalid OTP'}, status=401)
    return JsonResponse({'status':'200','message': 'OTP is valid'})

@api_view(['GET'])
def search_token_pin(request, token, pin,phone):
    count = TokenPin.objects.filter(token=token, pin=pin,phone_number=phone).count()
    return Response({'count': count}, status=status.HTTP_200_OK)

class PosExcelUploadViewSet(viewsets.ModelViewSet):
    serializer_class = PosSerializer
    queryset = Pos.objects.all()

    def create(self, request, *args, **kwargs):
        excel_file = request.FILES.get('file')
        if not excel_file:
            return Response({'error': 'Excel file is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            df = pd.read_excel(excel_file)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=df.to_dict('records'), many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response({'message': 'Pos créer avec succès'}, status=status.HTTP_201_CREATED)
    queryset = Pos.objects.all()
    serializer_class = PosSerializer
    filter_backends = (filters.DjangoFilterBackend)

class FileViewSet(APIView):
  parser_classes = (MultiPartParser, FormParser)
  def post(self, request, *args, **kwargs):
    file_serializer = MediaSerializer(data=request.data)
    if file_serializer.is_valid():
      file_serializer.save()
      return Response(file_serializer.data, status=status.HTTP_201_CREATED)
    else:
      return Response(file_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
  
class UploadViewSet(ViewSet):
    serializer_class = UploadSerializer

    def list(self, request):
        return Response("GET API")

    def create(self, request):
        file_uploaded = request.FILES.get('file_uploaded')
        content_type = file_uploaded.content_type
        response = "POST API and you have uploaded a {} file".format(content_type)
        return Response(response)
    
def getToken(request):
    csrf_token = get_token(request)
    return JsonResponse({'status': csrf_token})
 
class EducationFilter(filters.FilterSet):
    id_country = filters.NumberFilter(field_name='id_country')
    class Meta:
        model = EducationLevel
        fields = ['id_country']
        
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

def upload_image(request):
    if request.method == 'POST':
        image = request.FILES['image']
        mymodel = Media(image=image)
        mymodel.save()
        return JsonResponse({'status': 'success'})
    else:
        return HttpResponse('Only POST method is allowed')

def generate_token_pin(request, phone_number):
    token = os.urandom(20).hex()
    pin = ''.join(random.choices(string.digits, k=4))
    token_pin = TokenPin.objects.create(phone_number=phone_number, token=token, pin=pin)
    return JsonResponse({"token": token, "pin": pin})

