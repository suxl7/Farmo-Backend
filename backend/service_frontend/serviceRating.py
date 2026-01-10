from ..models import Users, ProductRating, Rating
from ..serializers import RatingSerializer
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from backend.permissions import HasValidTokenForUser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

##########################################################################################
#                            Farmer Rating Start
##########################################################################################
# Create a rating (rate_farmer)
class RateFarmer(APIView):
    def post(self, request):
        serializer = RatingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Edit a rating
class EditRate(APIView):
    def put(self, request, pk):
        rating = get_object_or_404(Rating, pk=pk)
        serializer = RatingSerializer(rating, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# View a single rating
class ViewRate(APIView):
    def get(self, request, pk):
        rating = get_object_or_404(Rating, pk=pk)
        serializer = RatingSerializer(rating)
        return Response(serializer.data)

# Delete a rating
class DeleteRate(APIView):
    def delete(self, request, pk):
        rating = get_object_or_404(Rating, pk=pk)
        rating.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# List all ratings
class ListRatings(APIView):
    def get(self, request):
        ratings = Rating.objects.all()
        serializer = RatingSerializer(ratings, many=True)
        return Response(serializer.data)



from django.db.models import Avg 

# Average Rating
def format_count(count):
    """Format counts like 5600 -> '5.6k', 300 -> '300'"""
    if count >= 1000:
        return f"{count/1000:.1f}k"
    return str(count)

@api_view(['POST'])
@permission_classes([HasValidTokenForUser])
def farmer_profile_rating(request):
    """Get average rating and total ratings for a farmer (POST version)"""
    farmer_id = request.data.get('farmer_id')   # farmer_id comes from POST body

    if not farmer_id:
        return Response({'error': 'farmer_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    qs = Rating.objects.filter(farmer_id=farmer_id)
    avg_rating = qs.aggregate(Avg('score'))['score__avg']
    total_count = qs.count()

    if avg_rating is None:
        return Response({
            'average_rating': 0,
            'total_ratings': format_count(total_count),
            'message': 'No ratings yet'
        }, status=status.HTTP_200_OK)

    return Response({
        'average_rating': round(avg_rating, 2),
        'total_ratings': format_count(total_count)
    }, status=status.HTTP_200_OK)


##########################################################################################
#                            Farmer Rating End
##########################################################################################



##########################################################################################
#                            Product Rating Start
##########################################################################################

##########################################################################################
#                            Product Rating End
##########################################################################################



##########################################################################################
#                            Consumer Rating Start
##########################################################################################
##########################################################################################
#                            Consumer Rating End
##########################################################################################
