from django.contrib import admin
from assets.models.server import *
from assets.models.db import *

admin.site.register(Server)
admin.site.register(DBServer)
admin.site.register(ServerGroup)
admin.site.register(ServerAuthRule)
admin.site.register(Tag)
admin.site.register(AdminUser)

admin.site.register(Log)
admin.site.register(TtyLog)
admin.site.register(RecorderLog)