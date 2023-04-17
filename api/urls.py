
from rest_framework.schemas import get_schema_view
from rest_framework import routers
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from .views import UserView, AjouterIndustrie, CountryViewSet,EducationViewSet,TypeIDViewSet,FileViewSet,AjouterFootsoldiers,AjouterTargetView,TargetListView,AjouterLocality,DetailsCountries
from .views import TypeIDDetail, LogoutView,AjouterKYCView,ListeKYC,UpdateKYCView,DeleteKycView,CreatePosView,ListPosView,CustomAuthToken,AjouterDomaine,ListePrivilege,ClientFootsoldiersView
from .views import UploadViewSet,ClientsList,CreateClient,ClientsUpdate,ClientsDelete,SupprimerProduit,ListeFootsoldiersView,SupprimerTarget,DeleteTraining,ListeIndustry,ClientTargetsView
from .views import UpdateUserView,TrainingCreate,ModifierProduit,UpdateFootsoldiersView,AjouterTypeId,ListeTypeId,ModifierTraining,ModifierTarget,ClientUsersView,ProductListByClientView
from .views import PosExcelUploadViewSet,CreateUsersView,TrainingList,ProduitListView,ProduitCreateView,DeleteFootsoldiersView,ModifierTypeId,DeleteTypeId,ModifierSectionQuiz,DetailsClient
from .views import AjouterCountries,ModifierCountries,DeleteCountriesView,ListeCountries,AjouterEducationLevel,ListeEducationLevel,ModifierEducationLevel,DeleteEducationLevel,QuizSectionList,ListeLocality
from .views import SectionCreate,SectionList,ModifierSection,DeleteSection,ChapterCreate,ChapterList,ModifierChapter,DeleteChapter,QuizSectionCreate,AnswerSectionCreate,ExamCreate,ListeDomaine,ClientPosView
from .views import QuizExamList,ExamList,AnswerSectionList,UserExamCreate,UserExamList,AnswerExamList,AnswerExamCreate,UserScoreList,UserScoreCreate,DeleteUserView,QuizExamCreate,AjouterPrivilege
from api.views import generate_token_pin,check_otp,upload_image,search_token_pin

schema_view = get_schema_view(
    openapi.Info(
        title="API Documentation",
        default_version='v1',
        description="API Documentation",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@xyz.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

router = routers.DefaultRouter()
router.register(r'upload', UploadViewSet, basename="uploadNew")

# Wire up our API using automatic URL routing.
router1 = routers.DefaultRouter()
router1.register(r'typeids', TypeIDViewSet, basename='typeids')

urlpatterns = [

    # api list by swagger
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('', include(router1.urls)),

    # logout API
    path('logout/', LogoutView.as_view(), name='logout'),

    # login API
    path('user-connection/', CustomAuthToken.as_view()),

    # super_users users_admin & users_reader CRUD API for Admin
    path('list-user/', UserView.as_view(), name='list_user'),
    path('ajouter-user/', CreateUsersView.as_view(), name='ajouter_user'),
    path('modifier-user/<int:user_id>/', UpdateUserView.as_view(), name='modifier_user'),
    path('supprimer-user/<int:user_id>/', DeleteUserView.as_view(), name='supprimer_user'),

    # super_users users_admin & users_reader CRUD API for Client
    path('list-userclient/', ClientUsersView.as_view(), name='list_user'),
    
    # settings setting_countries CRUD API
    path('ajouter-countries/', AjouterCountries.as_view(), name='ajouter_countries'),
    path('list-countries/', ListeCountries.as_view(), name='list_countries'),
    path('modifier-countries/<int:country_id>/', ModifierCountries.as_view(), name='modifier_countries'),
    path('detail-countries/<int:country_id>/', DetailsCountries.as_view(), name='detail_countries'),
    path('supprimer-countries/<int:country_id>/', DeleteCountriesView.as_view(), name='supprimer_countries'),

    # clients CRUD API
    path('list-clients/', ClientsList.as_view(), name='list_clients'),
    path('ajouter-clients/', CreateClient.as_view(), name='ajouter_clients'),
    path('detail-clients/<int:client_id>/', DetailsClient.as_view(), name='detail_clients'),
    path('modifier-clients/<int:client_id>/', ClientsUpdate.as_view(), name='modifier_clients'),
    path('supprimer-clients/<int:client_id>/', ClientsDelete.as_view(), name='modifier_clients'),

    # settings setting_typeID CRUD API
    path('ajouter-typeid/', AjouterTypeId.as_view(), name='ajouter_typeid'),
    path('modifier-typeid/<int:type_id>/', ModifierTypeId.as_view(), name='modifier_typeid'),
    path('list-typeid/', ListeTypeId.as_view(), name='list_setting_typeid'),
    path('supprimer-typeid/<int:type_id>/', DeleteTypeId.as_view(), name='supprimer_typeid'),

    # settings setting_privilege CRUD API
    path('ajouter-privilege/', AjouterPrivilege.as_view(), name='ajouter_privilege'),
    path('list-privilege/', ListePrivilege.as_view(), name='list_privilege'),

    # domaine CRUD API
    path('ajouter-domaine/', AjouterDomaine.as_view(), name='ajouter_domaine'),
    path('list-domaine/', ListeDomaine.as_view(), name='list_domaine'),

    # locality CRUD API
    path('ajouter-localite/', AjouterLocality.as_view(), name='ajouter_localite'),
    path('list-localite/', ListeLocality.as_view(), name='list_localite'),

    # industry CRUD API
    path('ajouter-industry/', AjouterIndustrie.as_view(), name='ajouter_industry'),
    path('list-industry/', ListeIndustry.as_view(), name='list_industry'),

    # settings setting_level CRUD API
    path('ajouter-level/', AjouterEducationLevel.as_view(), name='ajouter_level'),
    path('modifier-level/<int:education_id>/', ModifierEducationLevel.as_view(), name='modifier_level'),
    path('list-level/', ListeEducationLevel.as_view(), name='list_level'),
    path('supprimer-level/<int:education_id>/', DeleteEducationLevel.as_view(), name='supprimer_level'),

    # produit CRUD API
    path('list-produits/', ProduitListView.as_view(), name='liste_produits'),
    path('ajouter-produits/', ProduitCreateView.as_view(), name='ajouter_produit'),
    path('modifier-produits/<int:produit_id>/', ModifierProduit.as_view(), name='modifier_produit'),
    path('supprimer-produits/<int:produit_id>/', SupprimerProduit.as_view(), name='supprimer_produit'),

    # list des produits par client
    path('list-produitbyclient/', ProductListByClientView.as_view(), name='liste_produitbyclient'),

    # FootSoldiers CRUD API
    path('list-footsoldiers/', ListeFootsoldiersView.as_view(), name='liste_footsoldiers'),
    path('ajouter-footsoldiers/', AjouterFootsoldiers.as_view(), name='ajouter_footsoldiers'),
    path('modifier-footsoldiers/<int:footsoldiers_id>/', UpdateFootsoldiersView.as_view(), name='modifier_footsoldiers'),
    path('supprimer-footsoldiers/<int:footsoldiers_id>/', DeleteFootsoldiersView.as_view(), name='supprimer_footsoldiers'),

    # list des footsoldiers par client
    path('list-footsoldierbyclient/', ClientFootsoldiersView.as_view(), name='liste_footsoldierbyclient'),

    #  KYC CRUD API
    path('ajouter-kyc/', AjouterKYCView.as_view(), name='ajouter_kyc'),
    path('list-kyc/', ListeKYC.as_view(), name='list_kyc'),
    path('modifier-kyc/<int:kyc_id>/', UpdateKYCView.as_view(), name='modifier_kyc'),
    path('supprimer-kyc/<int:kyc_id>/', DeleteKycView.as_view(), name='supprimer_kyc'),

    # Target CRUD API
    path('ajouter-target/', AjouterTargetView.as_view(), name='ajouter_target'),
    path('list-target/', TargetListView.as_view(), name='list_target'),
    path('modifier-target/<int:target_id>/', ModifierTarget.as_view(), name='modifier_target'),
    path('supprimer-target/<int:target_id>/', SupprimerTarget.as_view(), name='supprimer_target'),

    # list target of client
    path('list-targetclient/', ClientTargetsView.as_view(), name='list_targetclient'),

    # pos CRUD API
    path('ajouter-pos/', CreatePosView.as_view(), name='ajouter_pos'),
    path('list-pos/', ListPosView.as_view(), name='list_pos'),

    # list pos of client
    path('list-posclient/', ClientPosView.as_view(), name='list_posclient'),

    # training CRUD API
    path('ajouter-training/', TrainingCreate.as_view(), name='ajouter_training'),
    path('list-training/', TrainingList.as_view(), name='liste_training'),
    path('supprimer-training/<int:training_id>/', DeleteTraining.as_view(), name='supprimer_training'),
    path('modifier-training/<int:training_id>/', ModifierTraining.as_view(), name='modifier_training'),

    # Section CRUD API
    path('ajouter-section/', SectionCreate.as_view(), name='ajouter_section'),
    path('list-section/', SectionList.as_view(), name='liste_section'),
    path('modifier-section/<int:section_id>/', ModifierSection.as_view(), name='modifier_section'),
    path('supprimer-section/<int:section_id>/', DeleteSection.as_view(), name='supprimer_section'),

    # Chapters CRUD API
    path('ajouter-chapter/', ChapterCreate.as_view(), name='ajouter_chapter'),
    path('list-chapter/', ChapterList.as_view(), name='list_chapter'),
    path('modifier-chapter/<int:chapter_id>/', ModifierChapter.as_view(), name='modifier_chapter'),
    path('supprimer-chapter/<int:chapter_id>/', DeleteChapter.as_view(), name='supprimer_chapter'),

    # quiz section CRUD API
    path('ajouter-quiz/', QuizSectionCreate.as_view(), name='ajouter_quiz'),
    path('modifier-quiz/<int:quiz_section_id>/', ModifierSectionQuiz.as_view(), name='modifier_quiz'),
    path('list-quiz/', QuizSectionList.as_view(), name='list_quiz'),

    # answer section CRUD APi
    path('ajouter-answersection/', AnswerSectionCreate.as_view(), name='ajouter_answersection'),
    path('list-answersection/', AnswerSectionList.as_view(), name='list_answersection'),

    # exam CRUD API
    path('ajouter-exam/', ExamCreate.as_view(), name='ajouter_exam'),
    path('list-exam/', ExamList.as_view(), name='list_exam'),

    # Quizexam CRUD API
    path('ajouter-quizexam/', QuizExamCreate.as_view(), name='ajouter_quizexam'),
    path('list-quizexam/', QuizExamList.as_view(), name='list_quizexam'),

    # Userexam CRUD API
    path('ajouter-userexam/', UserExamCreate.as_view(), name='ajouter_userexam'),
    path('list-usersexam/', UserExamList.as_view(), name='list_userexam'),

    # Answerexam CRUD API
    path('ajouter-answerexam/', AnswerExamCreate.as_view(), name='ajouter_answerexam'),
    path('list-answerexam/', AnswerExamList.as_view(), name='list_answerexam'),

    # userscore CRUD API
    path('ajouter-userscore/', UserScoreCreate.as_view(), name='ajouter_userscore'),
    path('list-userscore/', UserScoreList.as_view(), name='list_userscore'),










    path('pos-upload-excel/', PosExcelUploadViewSet.as_view({'post': 'create'}), name='pos-upload-excel'),
    path('typeid/<int:pk>/', TypeIDDetail.as_view(), name='typeid-detail'),
    path('search-token-pin/<str:token>/<str:pin>/<str:phone>/', search_token_pin, name='search_token_pin'),
    path('upload/', FileViewSet.as_view(),name='file-upload'),
    path('upload123/', include(router.urls)),
    path('countries/', CountryViewSet.as_view(), name='country-list'),
    path('educations/', EducationViewSet.as_view({'get': 'list', 'post': 'create'}), name='education-list'),
    path('educations/<int:pk>/', EducationViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='education-detail'),
    path('typepiece/', TypeIDViewSet.as_view({'get': 'list', 'post': 'create'}), name='education-list'),
    path('typepiece/<int:pk>/', TypeIDViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='education-detail'),
    path('generate_token_pin/<str:phone_number>', generate_token_pin),
    path('check_otp/<str:token>/<str:otp>', check_otp) ,
    path('uploadImages/', upload_image, name='upload'),
    
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
