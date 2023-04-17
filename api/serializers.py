from rest_framework import serializers
from rest_framework.serializers import Serializer, FileField
from .models import User, Countries,EducationLevel,Locality,TypeID,Media,QuizExamen,AnswersExamen,QuizSection ,AnswersSection,Dashboards,Footsoldiers,Produit,Target,UserExam,UserScoreExam
from .models import User,Media,Countries,TypeID,Clients,Chapters, EducationLevel, Locality,TokenPin,Kyc, Industry,Produit,Pos,Training,Chapters,Sections,Exam,Domaine,UsersClient,Privilege

# privilege serializer
class PrivilegeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Privilege
        fields = '__all__ '

class MediaSerializer(serializers.ModelSerializer):
      class Meta():
        model = Media
        fields = ('id_media','file', 'remark', 'timestamp')
    
# Serializers define the API representation.
class UploadSerializer(Serializer):
    file_uploaded = FileField()
    class Meta:
        fields = ['file_uploaded']

# user serializer 
class UserSerializer(serializers.ModelSerializer):
    # date_naissance = DateField()

    class Meta():
        model = User
        fields = '__all__'
        extra_kwargs = {'password': {'write_only': True}, 'profile_picture': {'required': False}}

    def create(self, validated_data):
        user = User(
            username=validated_data['username'],
            email=validated_data['email'],
            prenoms=validated_data['prenoms'],
            date_naissance=validated_data['date_naissance'],
            numero=validated_data['numero'],
            nom=validated_data['nom'],
            # privilege = validated_data['privilege'],
        )
        user.set_password(validated_data['password'])
        user.profile_picture = validated_data.get('profile_picture')
        user.save()
        return user
    
# dashboard serializer
class DashboardsSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = Dashboards
        fields = ('id', 'user', 'dashboard_name', 'refresh_frequency')
        read_only_fields = ('id',)

# client serializer
class ClientsSerializer(serializers.ModelSerializer):
    # created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Clients
        fields = '__all__'


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Countries
        fields = ('id_country', 'country_name', 'country_prefixe', 'country_flag_url')

class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationLevel
        fields = ('id_education', 'level_name', 'id_country','level_description')

class LocalitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Locality
        fields = ('id_locality', 'locality_name', 'id_country')

class TypeIDSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeID
        fields = '__all__'

class TargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Target
        fields = '__all__'

class FootsoldiersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Footsoldiers
        fields = '__all__'

class QuizExamenSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizExamen
        fields = '__all__'

class UserScoreExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserScoreExam
        fields = '__all__'
    
class AnswersExamenSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswersExamen
        fields = '__all__'
    
class UserExamenSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserExam
        fields = '__all__'

class QuizSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizSection
        fields = '__all__'

class AnswersSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswersSection
        fields = ('id_answer_section', 'id_quiz', 'answer_label','answer_correct')

class TrainingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Training
        fields = '__all__'

class UsersClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsersClient
        fields = '__all__'

class ProduitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Produit
        fields = '__all__'

class DomaineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domaine
        fields = '__all__'
        
class PosSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pos
        fields = '__all__'
        
class TrainingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Training
        fields = '__all__'
 
class ChaptersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chapters
        fields = '__all__'

class SectionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sections
        fields = '__all__'

class ExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = '__all__'

class KycSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kyc
        fields = '__all__'

class IndustrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Industry
        fields = '__all__'

class TokenPinSerializer(serializers.ModelSerializer):
    class Meta:
        model = TokenPin
        fields = '__all__'
