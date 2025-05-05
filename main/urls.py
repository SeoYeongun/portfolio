from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.base, name='base'),
    path('blog/', views.blog, name='blog'),
    path('post/new/', views.post_new, name='post_new'),
    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('post/<int:pk>/edit/', views.post_edit, name='post_edit'),
    path('post/<int:pk>/delete/', views.post_delete, name='post_delete'),
    path('post/<int:pk>/like/', views.post_like, name='post_like'),
    path('post/<int:pk>/comment/', views.comment_create, name='comment_create'),
    path('comment/<int:comment_id>/delete/', views.comment_delete, name='comment_delete'),
    path('comment/<int:comment_id>/edit/', views.comment_edit, name='comment_edit'),
    path('comment/<int:pk>/like/', views.comment_like, name='comment_like'),
    path('comment/<int:pk>/dislike/', views.comment_dislike, name='comment_dislike'),
    path('user/<str:username>/', views.user_profile, name='user_profile'),
    path('signup/', views.signup, name='signup'),
    path('chat/lobby/', views.lobby_view, name='lobby'),
    path('chat/<str:room_name>/', views.chat_view, name='chat'),
    path('movies/search/', views.movie_search, name='movie_search'),
    path('movies/popular/', views.popular_movies, name='popular_movies'),
    path('movies/latest/', views.movie_list, name='movie_list'),
    path('movies/<int:movie_id>/', views.movie_detail, name='movie_detail'),
    path('alert/', views.alert, name='alert'),
    path('notification/<int:notification_id>/read/', views.mark_notification_as_read, name='mark_notification_as_read'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 