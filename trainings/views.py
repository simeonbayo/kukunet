# trainings/views.py - Update the put method
import logging
from decimal import Decimal
from django.db.models import Sum, Count, Q, Avg
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from datetime import datetime, date
import django
from django.db import transaction

from .models import Training, TrainingAttendance, TrainingEvaluation
from .serializers import TrainingSerializer, TrainingAttendanceSerializer, TrainingEvaluationSerializer
from accounts.models import User

logger = logging.getLogger(__name__)


class TrainingListView(APIView):
    """Get all trainings for the organization"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            tenant = request.user.tenant
            if not tenant:
                return Response({
                    'success': False,
                    'message': 'No organization associated'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            trainings = Training.objects.filter(tenant=tenant).order_by('-start_date')
            serializer = TrainingSerializer(trainings, many=True, context={'request': request})
            
            # Calculate statistics
            total_trainings = trainings.count()
            upcoming = trainings.filter(status='UPCOMING').count()
            ongoing = trainings.filter(status='ONGOING').count()
            completed = trainings.filter(status='COMPLETED').count()
            total_participants = trainings.aggregate(total=Sum('expected_participants'))['total'] or 0
            
            return Response({
                'success': True,
                'trainings': serializer.data,
                'stats': {
                    'total': total_trainings,
                    'upcoming': upcoming,
                    'ongoing': ongoing,
                    'completed': completed,
                    'total_participants': total_participants
                }
            })
            
        except Exception as e:
            logger.error(f"Error fetching trainings: {str(e)}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @transaction.atomic
    def post(self, request):
        try:
            tenant = request.user.tenant
            if not tenant:
                return Response({
                    'success': False,
                    'message': 'No organization associated'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create a mutable copy of request data
            data = request.data.copy()
            data['tenant'] = tenant.id
            
            serializer = TrainingSerializer(data=data, context={'request': request})
            
            if serializer.is_valid():
                training = serializer.save()
                return Response({
                    'success': True,
                    'message': 'Training created successfully',
                    'training': serializer.data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'success': False,
                    'message': 'Validation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error creating training: {str(e)}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TrainingDetailView(APIView):
    """Get, update, delete a specific training"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, training_id):
        try:
            tenant = request.user.tenant
            training = Training.objects.get(id=training_id, tenant=tenant)
            serializer = TrainingSerializer(training, context={'request': request})
            
            # Get enrolled farmers
            enrolled_farmers = training.farmers.all()
            farmers_data = [{'id': f.id, 'full_name': f.full_name, 'phone_number': f.phone_number} for f in enrolled_farmers]
            
            return Response({
                'success': True,
                'training': serializer.data,
                'enrolled_farmers': farmers_data
            })
            
        except Training.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Training not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error fetching training: {str(e)}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @transaction.atomic
    def put(self, request, training_id):
        try:
            tenant = request.user.tenant
            training = Training.objects.get(id=training_id, tenant=tenant)
            
            logger.info(f"Updating training {training_id} with data: {request.data}")
            
            # Handle farmer_ids separately
            farmer_ids = request.data.pop('farmer_ids', None)
            
            # Get the status value - this is the key fix
            new_status = request.data.get('status')
            if new_status:
                request.data['status'] = new_status
                logger.info(f"Updating status to: {new_status}")
            
            serializer = TrainingSerializer(training, data=request.data, partial=True, context={'request': request})
            
            if serializer.is_valid():
                updated_training = serializer.save()
                logger.info(f"Training updated successfully. New status: {updated_training.status}")
                
                # Update farmers if provided
                if farmer_ids is not None:
                    updated_training.farmers.set(farmer_ids)
                    logger.info(f"Updated farmers: {farmer_ids}")
                
                return Response({
                    'success': True,
                    'message': 'Training updated successfully',
                    'training': serializer.data
                })
            else:
                logger.error(f"Serializer errors: {serializer.errors}")
                return Response({
                    'success': False,
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Training.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Training not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating training: {str(e)}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, training_id):
        try:
            tenant = request.user.tenant
            training = Training.objects.get(id=training_id, tenant=tenant)
            training.delete()
            return Response({
                'success': True,
                'message': 'Training deleted successfully'
            })
        except Training.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Training not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error deleting training: {str(e)}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TrainingAttendanceView(APIView):
    """Manage training attendance"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, training_id):
        try:
            tenant = request.user.tenant
            training = Training.objects.get(id=training_id, tenant=tenant)
            
            farmer_id = request.data.get('farmer_id')
            attendance_status = request.data.get('attendance_status', 'PRESENT')
            
            farmer = User.objects.get(id=farmer_id, tenant=tenant, role='FARMER')
            
            attendance, created = TrainingAttendance.objects.update_or_create(
                training=training,
                farmer=farmer,
                defaults={
                    'attendance_status': attendance_status,
                    'check_in_time': datetime.now() if attendance_status == 'PRESENT' else None
                }
            )
            
            # Update actual participants count
            training.actual_participants = TrainingAttendance.objects.filter(
                training=training, 
                attendance_status='PRESENT'
            ).count()
            training.save()
            
            return Response({
                'success': True,
                'message': 'Attendance recorded successfully'
            })
            
        except Training.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Training not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Farmer not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error recording attendance: {str(e)}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TrainingEvaluationView(APIView):
    """Submit training evaluation"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, training_id):
        try:
            tenant = request.user.tenant
            training = Training.objects.get(id=training_id, tenant=tenant)
            
            data = request.data.copy()
            data['training'] = training.id
            data['farmer'] = request.user.id if request.user.role == 'FARMER' else data.get('farmer_id')
            
            serializer = TrainingEvaluationSerializer(data=data)
            if serializer.is_valid():
                evaluation = serializer.save()
                
                # Update average rating for training
                avg_rating = TrainingEvaluation.objects.filter(training=training).aggregate(
                    avg=Avg('overall_rating')
                )['avg'] or 0
                training.average_rating = avg_rating
                training.save()
                
                return Response({
                    'success': True,
                    'message': 'Evaluation submitted successfully',
                    'evaluation': serializer.data
                })
            else:
                return Response({
                    'success': False,
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Training.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Training not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error submitting evaluation: {str(e)}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# trainings/views.py - Add this new class at the end of the file

class TrainingStatusUpdateView(APIView):
    """Dedicated endpoint for updating training status only"""
    permission_classes = [IsAuthenticated]
    
    def patch(self, request, training_id):
        """Update only the status of a training"""
        try:
            tenant = request.user.tenant
            training = Training.objects.get(id=training_id, tenant=tenant)
            
            new_status = request.data.get('status')
            if not new_status:
                return Response({
                    'success': False,
                    'message': 'Status is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate status
            valid_statuses = ['UPCOMING', 'ONGOING', 'COMPLETED', 'CANCELLED']
            if new_status not in valid_statuses:
                return Response({
                    'success': False,
                    'message': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update only the status field
            training.status = new_status
            training.save(update_fields=['status', 'updated_at'])
            
            logger.info(f"Training {training_id} status updated to {new_status}")
            
            return Response({
                'success': True,
                'message': f'Training status updated to {new_status}',
                'training': {
                    'id': training.id,
                    'title': training.title,
                    'status': training.status,
                    'status_display': training.get_status_display()
                }
            })
            
        except Training.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Training not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating training status: {str(e)}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)