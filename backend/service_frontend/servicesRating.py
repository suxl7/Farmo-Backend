from ..models import Users, ProductRating,  Rating
from ..serializers import  RatingSerializer, ProductRatingSerializer
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from backend.permissions import HasValidTokenForUser, IsFarmer, IsConsumer
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.db.models import Avg


##########################################################################################
#                            Farmer Rating (Consumer rates Farmer)
##########################################################################################

# Create a farmer rating (Consumer rates Farmer)
class RateFarmer(APIView):
    permission_classes = [HasValidTokenForUser, IsConsumer]
    def post(self, request):
        # Automatically set rate_for to 'Farmer' since consumer is rating a farmer
        data = request.data.copy()
        data['rate_for'] = 'Farmer'
        serializer = RatingSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Edit a farmer rating
class EditFarmerRate(APIView):
    permission_classes = [HasValidTokenForUser, IsConsumer]
    def put(self, request, pk):
        rating = get_object_or_404(Rating, pk=pk, rate_for='Farmer')
        serializer = RatingSerializer(rating, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# View a single farmer rating
class ViewFarmerRate(APIView):
    permission_classes = [HasValidTokenForUser]
    def get(self, request, pk):
        rating = get_object_or_404(Rating, pk=pk, rate_for='Farmer')
        serializer = RatingSerializer(rating)
        return Response(serializer.data)

# Delete a farmer rating
class DeleteFarmerRate(APIView):
    permission_classes = [HasValidTokenForUser, IsConsumer]
    def delete(self, request, pk):
        rating = get_object_or_404(Rating, pk=pk, rate_for='Farmer')
        rating.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# List all farmer ratings
class ListFarmerRatings(APIView):
    permission_classes = [HasValidTokenForUser]
    def get(self, request):
        ratings = Rating.objects.filter(rate_for='Farmer')
        serializer = RatingSerializer(ratings, many=True)
        return Response(serializer.data)

# List ratings for a specific farmer
class ListRatingsByFarmer(APIView):
    permission_classes = [HasValidTokenForUser]
    def get(self, request, farmer_id):
        ratings = Rating.objects.filter(rated_to=farmer_id, rate_for='Farmer')
        serializer = RatingSerializer(ratings, many=True)
        return Response(serializer.data)

# Average Rating for Farmer
def format_count(count):
    """Format counts like 5600 -> '5.6k', 300 -> '300'"""
    if count >= 1000:
        return f"{count/1000:.1f}k"
    return str(count)

@api_view(['POST'])
@permission_classes([HasValidTokenForUser])
def farmer_profile_rating(request):
    """Get average rating and total ratings for a farmer (POST version)"""
    farmer_id = request.data.get('farmer_id')

    if not farmer_id:
        return Response({'error': 'farmer_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    qs = Rating.objects.filter(rated_to=farmer_id, rate_for='Farmer')
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
#                            Consumer Rating (Farmer rates Consumer)
##########################################################################################

# Create a consumer rating (Farmer rates Consumer)
class RateConsumer(APIView):
    permission_classes = [HasValidTokenForUser, IsFarmer]
    def post(self, request):
        # Automatically set rate_for to 'Consumer' since farmer is rating a consumer
        data = request.data.copy()
        data['rate_for'] = 'Consumer'
        serializer = RatingSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Edit a consumer rating
class EditConsumerRate(APIView):
    permission_classes = [HasValidTokenForUser, IsFarmer]
    def put(self, request, pk):
        rating = get_object_or_404(Rating, pk=pk, rate_for='Consumer')
        serializer = RatingSerializer(rating, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# View a single consumer rating
class ViewConsumerRate(APIView):
    permission_classes = [HasValidTokenForUser]
    def get(self, request, pk):
        rating = get_object_or_404(Rating, pk=pk, rate_for='Consumer')
        serializer = RatingSerializer(rating)
        return Response(serializer.data)

# Delete a consumer rating
class DeleteConsumerRate(APIView):
    permission_classes = [HasValidTokenForUser, IsFarmer]
    def delete(self, request, pk):
        rating = get_object_or_404(Rating, pk=pk, rate_for='Consumer')
        rating.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# List all consumer ratings
class ListConsumerRatings(APIView):
    permission_classes = [HasValidTokenForUser]
    def get(self, request):
        ratings = Rating.objects.filter(rate_for='Consumer')
        serializer = RatingSerializer(ratings, many=True)
        return Response(serializer.data)

# List ratings for a specific consumer
class ListRatingsByConsumer(APIView):
    permission_classes = [HasValidTokenForUser]
    def get(self, request, consumer_id):
        ratings = Rating.objects.filter(rated_to=consumer_id, rate_for='Consumer')
        serializer = RatingSerializer(ratings, many=True)
        return Response(serializer.data)

# Average Rating for Consumer
@api_view(['POST'])
@permission_classes([HasValidTokenForUser])
def consumer_profile_rating(request):
    """Get average rating and total ratings for a consumer (POST version)"""
    consumer_id = request.data.get('consumer_id')

    if not consumer_id:
        return Response({'error': 'consumer_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    qs = Rating.objects.filter(rated_to=consumer_id, rate_for='Consumer')
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
#                            Farmer as Consumer Rating (Farmer rates another Farmer)
##########################################################################################

# Create a rating for farmer as consumer (Farmer buying from another Farmer)
class RateFarmerAsConsumer(APIView):
    permission_classes = [HasValidTokenForUser, IsFarmer]
    def post(self, request):
        # Farmer acting as consumer, rating another farmer
        data = request.data.copy()
        data['rate_for'] = 'Farmer'
        serializer = RatingSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Edit a farmer-as-consumer rating
class EditFarmerAsConsumerRate(APIView):
    permission_classes = [HasValidTokenForUser, IsFarmer]
    def put(self, request, pk):
        rating = get_object_or_404(Rating, pk=pk, rate_for='Farmer')
        # Verify the rater is the logged-in farmer
        serializer = RatingSerializer(rating, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Delete a farmer-as-consumer rating
class DeleteFarmerAsConsumerRate(APIView):
    permission_classes = [HasValidTokenForUser, IsFarmer]
    def delete(self, request, pk):
        rating = get_object_or_404(Rating, pk=pk, rate_for='Farmer')
        rating.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

##########################################################################################
#                            Rating System End
#########################################################################################


##########################################################################################
#                            Product Rating Start
##########################################################################################
class RateProduct(APIView):
    permission_classes = [HasValidTokenForUser, IsConsumer]
    def post(self, request):
        serializer = ProductRatingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Edit a product rating
class EditProductRate(APIView):
    permission_classes = [HasValidTokenForUser, IsConsumer]
    def put(self, request, pk):
        product_rating = get_object_or_404(ProductRating, pk=pk)
        serializer = ProductRatingSerializer(product_rating, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# View a single product rating
class ViewProductRate(APIView):
    permission_classes = [HasValidTokenForUser, IsFarmer, IsConsumer]
    def get(self, request, pk):
        product_rating = get_object_or_404(ProductRating, pk=pk)
        serializer = ProductRatingSerializer(product_rating)
        return Response(serializer.data)

# Delete a product rating
class DeleteProductRate(APIView):
    permission_classes = [HasValidTokenForUser, IsConsumer]
    def delete(self, request, pk):
        product_rating = get_object_or_404(ProductRating, pk=pk)
        product_rating.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# List all product ratings
# class ListProductRatings(APIView):
#     permission_classes = [HasValidTokenForUser, IsFarmer, IsConsumer]
#     def get(self, request):
#         product_ratings = ProductRating.objects.all()
#         serializer = ProductRatingSerializer(product_ratings, many=True)
#         return Response(serializer.data)

# List ratings for a specific product
class ListProductRatingsByProduct(APIView):
    permission_classes = [HasValidTokenForUser, IsFarmer, IsConsumer]
    def get(self, request, product_id):
        product_ratings = ProductRating.objects.filter(p_id=product_id)
        serializer = ProductRatingSerializer(product_ratings, many=True)
        return Response(serializer.data)

# Average Rating and Total Count
def format_count(count):
    """Format counts like 5600 -> '5.6k', 300 -> '300'"""
    if count >= 1000:
        return f"{count/1000:.1f}k"
    return str(count)

@api_view(['POST'])
@permission_classes([HasValidTokenForUser])
def product_profile_rating(request):
    """Get average rating and total ratings for a product (POST version)"""
    product_id = request.data.get('product_id')   # product_id comes from POST body

    if not product_id:
        return Response({'error': 'product_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    qs = ProductRating.objects.filter(p_id=product_id)
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
#                            Product Rating End
##########################################################################################
 