from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

class Post(models.Model):
    GENRE_CHOICES = [
        ('액션', '액션'),
        ('코미디', '코미디'),
        ('드라마', '드라마'),
        ('SF', 'SF'),
        ('로맨스', '로맨스'),
        ('스릴러', '스릴러'),
        ('호러', '호러'),
        ('애니메이션', '애니메이션'),
        ('다큐멘터리', '다큐멘터리'),
        ('판타지', '판타지'),
    ]
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.CharField(max_length=20, choices=GENRE_CHOICES, default='드라마')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    date_posted = models.DateTimeField(default=timezone.now)
    image = models.ImageField(upload_to='post_images', null=True, blank=True)
    region = models.CharField(max_length=100, null=True, blank=True)
    likes = models.ManyToManyField(User, related_name='post_likes', blank=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('post_detail', kwargs={'pk': self.pk})

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    likes = models.ManyToManyField(User, related_name='comment_likes', blank=True)
    dislikes = models.ManyToManyField(User, related_name='comment_dislikes', blank=True)

    def __str__(self):
        return f'{self.author.username}의 댓글: {self.content[:20]}'

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    region = models.CharField(max_length=100, null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    address = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return f'{self.user.username}의 프로필' 
    
class Message(models.Model):
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_messages', on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    room_name = models.CharField(max_length=200)

    def __str__(self):
        return f'{self.sender.username} -> {self.receiver.username}: {self.content[:20]}' 

class Movie(models.Model):
    title = models.CharField(max_length=200)
    overview = models.TextField()
    release_date = models.DateField(null=True, blank=True)
    poster_path = models.CharField(max_length=200, null=True, blank=True)
    vote_average = models.FloatField()
    tmdb_id = models.IntegerField(unique=True)
    
    def __str__(self):
        return self.title 

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('comment', '댓글'),
        ('like', '좋아요'),
    )
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    post = models.ForeignKey('Post', on_delete=models.CASCADE, null=True, blank=True)
    comment = models.ForeignKey('Comment', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def get_absolute_url(self):
        if self.post:
            return self.post.get_absolute_url()
        return '/'

    class Meta:
        ordering = ['-created_at'] 