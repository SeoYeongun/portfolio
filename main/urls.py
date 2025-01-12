from django.urls import path
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from main.views import base, blog, PostDetailView, PostCreateView, SignUpView, CustomLoginView, CustomLogoutView, PostDeleteView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', base, name='base'),
    path('blog/', blog, name='blog'),
    path('blog/<int:pk>/',PostDetailView.as_view() , name='post_detail'),
    path('blog/post_new/', PostCreateView.as_view(), name='post_new'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('blog/<int:pk>/delete/', PostDeleteView.as_view(), name='post_delete'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

