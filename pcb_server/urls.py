"""
URL configuration for pcb_server project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.urls import include, path
from django.views.decorators.cache import cache_page
from django.http import FileResponse, Http404
from django.shortcuts import render

import os

def index(request):
    return render(request, 'index.html')

def chat(request):
    return render(request, 'chat.html')

def about(request):
    return render(request, 'about.html')

@cache_page(60 * 60 * 24)
def serve_image(request, filename):
    image_path = os.path.join(settings.MEDIA_ROOT, 'images', filename)
    if os.path.exists(image_path):
        return FileResponse(open(image_path, 'rb'), content_type='image/jpeg')  # or use mimetypes
    else:
        raise Http404("Image not found")

urlpatterns = [
    path('', index, name='index'),
    path('chat', chat, name='chat'),
    path('about', about, name='about'),
    path('admin/', admin.site.urls),
    path('auth/', include('accounts.urls')),
    path('api/', include('pcb_manager.urls')),
    path('media/images/<str:filename>/', serve_image, name='serve_image'),
    path('/media/images/<str:filename>/', serve_image, name='serve_image_1') # bandaid - remove later
]
