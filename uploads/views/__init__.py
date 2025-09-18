# Imports from modularized views
from .auth import (
    RegisterView,
    LoginView,
    UserInfoView,
    RefreshTokenView,
)

from .preferences import (
    ReaderPreferenceView,
    ReadingProgressView,
)

from .utils import (
    SupportedLanguagesView,
    AuditLogsView,
    DeleteTranslationView,
    cleanup_orphaned_records,
    DiagnosticsView,
    ReaderImageView,
)

from .files import (
    UploadFileView,
    FileListView,
    DeleteFileView,
    DeleteAllBooksView,
)

from .download import (
    DownloadsView,
    DownloadOriginalView,
    DownloadTranslatedView,
    DownloadMixedView,
)

from .epub import (
    ExtractEpubView,
    TranslateEpubView,
    BooksListView,
    EpubReaderView,
)

from .import_views import (
    AO3ImportView,
)

# Keep all legacy imports available for backward compatibility
__all__ = [
    # Authentication
    'RegisterView',
    'LoginView', 
    'UserInfoView',
    'RefreshTokenView',
    
    # Preferences
    'ReaderPreferenceView',
    'ReadingProgressView',
    
    # Utils
    'SupportedLanguagesView',
    'AuditLogsView',
    'DeleteTranslationView',
    'cleanup_orphaned_records',
    'DiagnosticsView',
    'ReaderImageView',
    
    # Files
    'UploadFileView',
    'FileListView',
    'DeleteFileView',
    'DeleteAllBooksView',
    
    # Downloads
    'DownloadsView',
    'DownloadOriginalView',
    'DownloadTranslatedView',
    'DownloadMixedView',
    
    # EPUB Processing
    'ExtractEpubView',
    'TranslateEpubView',
    'BooksListView',
    'EpubReaderView',
    
    # Import
    'AO3ImportView',
]