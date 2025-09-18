from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from ..models import ReaderPreference, ReadingProgress, ExtractedEpub, AuditLog
from ..serializers import ReaderPreferenceSerializer, ReadingProgressSerializer


class ReaderPreferenceView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        pref, _ = ReaderPreference.objects.get_or_create(user=request.user)
        return Response(ReaderPreferenceSerializer(pref).data)

    def put(self, request, *args, **kwargs):
        pref, _ = ReaderPreference.objects.get_or_create(user=request.user)
        serializer = ReaderPreferenceSerializer(pref, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        return self.put(request, *args, **kwargs)


class ReadingProgressView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, extracted_epub_id, *args, **kwargs):
        extracted = get_object_or_404(ExtractedEpub, pk=extracted_epub_id, uploaded_file__user=request.user)
        obj = ReadingProgress.objects.filter(user=request.user, extracted_epub=extracted).first()
        if not obj:
            return Response({
                'current_chapter': 0,
                'current_position': 0,
                'progress_percentage': 0.0,
            })
        return Response(ReadingProgressSerializer(obj).data)

    def post(self, request, extracted_epub_id, *args, **kwargs):
        extracted = get_object_or_404(ExtractedEpub, pk=extracted_epub_id, uploaded_file__user=request.user)

        payload = {
            'current_chapter': int(request.data.get('current_chapter', 0) or 0),
            'current_position': int(request.data.get('current_position', 0) or 0),
            'progress_percentage': float(request.data.get('progress_percentage', 0.0) or 0.0),
        }
        serializer = ReadingProgressSerializer(data={ 'extracted_epub': extracted.pk, **payload })

        if serializer.is_valid():
            # upsert by user + extracted_epub
            obj, _created = ReadingProgress.objects.update_or_create(
                user=request.user,
                extracted_epub=extracted,
                defaults=payload
            )

            # Audit log
            AuditLog.objects.create(
                user=request.user,
                action='read',
                description='Reading progress updated',
                resource_id=extracted.pk,
                resource_type='extraction',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                metadata={
                    'current_chapter': obj.current_chapter,
                    'current_position': obj.current_position,
                    'progress_percentage': obj.progress_percentage,
                }
            )

            return Response(ReadingProgressSerializer(obj).data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)