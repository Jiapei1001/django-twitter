from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from comments.api.permissions import IsObjectOwner
from comments.models import Comment
from inbox.services import NotificationService
from comments.api.serializers import (
    CommentSerializer,
    CommentSerializerForCreate,
    CommentSerializerForUpdate,
)
from twitter.decorators import required_params


class CommentViewSet(viewsets.GenericViewSet):
    # 不实现retrieve的方法，因为不需要单独get某一个comment
    # 需要实现list，create，update，destroy这些功能
    serializer_class = CommentSerializerForCreate
    queryset = Comment.objects.all()
    # after install django-filter
    filterset_fields = ('tweet_id',)

    # NOTE：这里的get_permissions是针对Django的default methods
    # 如list，retrieve，create，update，destroy
    # 其他方法需要用decorator @action
    # 但是decorator @action对于这些default methods会报错
    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated()]
        if self.action in ['update', 'destroy']:
            return [IsAuthenticated(), IsObjectOwner()]
        return [AllowAny()]

    def create(self, request, *args, **kwargs):
        data = {
            'user_id': request.user.id,
            'tweet_id': request.data.get('tweet_id'),
            'content': request.data.get('content'),
        }
        serializer = CommentSerializerForCreate(data=data)
        if not serializer.is_valid():
            return Response({
                'message': 'Please check input.',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        comment = serializer.save()
        NotificationService.send_comment_notification(comment)
        # update below, as CommentSerializer added fields of likes_count and has_liked
        # both of them need the context of the request
        # return Response(
        #     CommentSerializer(comment).data,
        #     status=status.HTTP_201_CREATED,
        # )
        return Response(
            CommentSerializer(comment, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        serializer = CommentSerializerForUpdate(
            instance=self.get_object(),
            data=request.data,
        )
        if not serializer.is_valid():
            return Response({
                'message': 'Please check input.',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        comment = serializer.save()
        # update below, as CommentSerializer added fields of likes_count and has_liked
        # both of them need the context of the request
        # return Response(
        #     CommentSerializer(comment).data,
        #     status=status.HTTP_200_OK,
        # )
        return Response(
            CommentSerializer(comment, context={'request': self.request}).data,
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        comment = self.get_object()
        comment.delete()
        return Response({
            'success': True,
        }, status=status.HTTP_200_OK)

    @required_params(params=['tweet_id'])
    def list(self, request, *args, **kwargs):
        """
        replace by decorator, required_params
        if 'tweet_id' not in request.query_params:
            return Response({
                'message': 'missing tweet_id in request',
                'success': False,
            }, status=status.HTTP_400_BAD_REQUEST)
        """

        queryset = self.get_queryset()
        comments = self.filter_queryset(queryset).order_by('created_at')

        # update below, as CommentSerializer added fields of likes_count and has_liked
        # both of them need the context of the request
        # serializer = CommentSerializer(comments, many=True)
        serializer = CommentSerializer(
            comments,
            context={'request': self.request},
            many=True,
        )

        return Response({
            'comments': serializer.data,
        }, status=status.HTTP_200_OK)
