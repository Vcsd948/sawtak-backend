from django.contrib import admin
from .models import Claim, ClaimHistory, Service, ResolutionProofImage

class ClaimHistoryInline(admin.TabularInline):
    model = ClaimHistory
    extra = 0
    readonly_fields = ('old_status', 'new_status', 'created_at')
    can_delete = False

@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ('reference', 'title', 'citizen', 'assigned_to', 'status', 'priority', 'created_at')
    list_filter = ('status', 'priority', 'category', 'assigned_to')
    search_fields = ('reference', 'title', 'description', 'citizen__username')
    readonly_fields = ('reference', 'created_at', 'updated_at')
    inlines = [ClaimHistoryInline]

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'is_active')
    list_filter = ('is_active', 'category')

@admin.register(ResolutionProofImage)
class ResolutionProofImageAdmin(admin.ModelAdmin):
    list_display = ('claim', 'image', 'uploaded_at')