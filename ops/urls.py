from django.contrib import admin
from django.urls import path,include
from rest_framework_swagger.views import get_swagger_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('v1/cmdb/docs/', get_swagger_view(title='API文档')),
    path('v1/cmdb/', include('assets.urls',namespace='api-assets')),
    path('api-auth/', include('rest_framework.urls',namespace='rest_framework')),
]