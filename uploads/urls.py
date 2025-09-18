from django.urls import path
from . import views
from .views import EpubReaderView, ReadingProgressView, AO3ImportView, ReaderImageView, BooksListView, ReaderPreferenceView, DiagnosticsView

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('user/', views.UserInfoView.as_view(), name='user-info'),
    path('refresh/', views.RefreshTokenView.as_view(), name='refresh-token'),
    path('languages/', views.SupportedLanguagesView.as_view(), name='supported-languages'),
    path('upload/', views.UploadFileView.as_view(), name='upload'),
    path('files/', views.FileListView.as_view(), name='file-list'),
    path('files/<int:pk>/delete/', views.DeleteFileView.as_view(), name='delete-file'),
    path('books/delete-all/', views.DeleteAllBooksView.as_view(), name='delete-all-books'),
    path('translations/<int:pk>/delete/', views.DeleteTranslationView.as_view(), name='delete-translation'),
    path('extract/<int:pk>/', views.ExtractEpubView.as_view(), name='extract-epub'),
    path('translate/<int:pk>/', views.TranslateEpubView.as_view(), name='translate-epub'),
    path('downloads/', views.DownloadsView.as_view(), name='downloads'),
    path('audit-logs/', views.AuditLogsView.as_view(), name='audit-logs'),
    path('download/original/<int:pk>/', views.DownloadOriginalView.as_view(), name='download-original'),
    path('download/translation/<int:pk>/', views.DownloadTranslatedView.as_view(), name='download-translation'),
    path('download/mixed/<int:pk>/', views.DownloadMixedView.as_view(), name='download-mixed'),
    path('reader/<int:file_id>/', EpubReaderView.as_view(), name='epub-reader'),
    path('reader/<int:file_id>/images/<str:image_name>', ReaderImageView.as_view(), name='reader-image'),
    path('reading-progress/<int:extracted_epub_id>/', ReadingProgressView.as_view(), name='reading-progress'),
    path('books/', BooksListView.as_view(), name='books-list'),
    path('import-ao3/', AO3ImportView.as_view(), name='import-ao3'),
    path('reader-preferences/', ReaderPreferenceView.as_view(), name='reader-preferences'),
    path('diagnostics/', DiagnosticsView.as_view(), name='diagnostics'),
]
