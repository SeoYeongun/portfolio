from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.base, name='base'),
    path('blog/', views.blog, name='blog'),
    path('post/new/', views.post_create, name='post_new'),
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
    path('get_address/', views.get_address_from_coords, name='get_address'),
    path('map/', views.map_view, name='map'),
    path('signup/', views.signup, name='signup'),
    path('chat/<str:username>/', views.start_chat, name='start_chat'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 