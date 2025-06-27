from django.urls import path
from . import views

urlpatterns = [
    # Matches /api/analyze-pcb/
    path('devices/analyze-pcb/', views.analyze_and_save_device, name='device-analyze-save'),

    # Matches /api/devices/
    path('devices/', views.list_all_devices, name='device-list'),

    # Matches /api/devices/5/
    path('devices/<int:device_id>/', views.get_device_by_id, name='device-detail'),
    path('devices/<int:device_id>/delete/', views.delete_device, name='device-delete'),

    # Matches /api/devices/5/chat/
    path('devices/<int:device_id>/chat/', views.chat_with_device, name='device-chat'),
    path('test-llm/', views.test_llm_connection, name='test_llm'),
]