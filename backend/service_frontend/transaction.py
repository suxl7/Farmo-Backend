from backend.models import Users, OrderRequest, Wallet, Transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from backend.permissions import HasValidTokenForUser, IsAdmin
from django.db.models import *

##########################################################################################
#                            Transfer fund Start
##########################################################################################

@api_view(['POST'])
@permission_classes([HasValidTokenForUser])
def transfer_fund(request):


    return Response(status=status.HTTP_200_OK)

##########################################################################################
#                            Transfer fund End
##########################################################################################
