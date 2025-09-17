export interface Book {
  id: string;
  title: string;
  author: string;
  cover: string;
  chapters: Chapter[];
  currentChapter: number;
  progress: number;
  translationAvailable: boolean;
  translationProgress: number;
  availableTranslations: TranslationInfo[];
}

export interface Chapter {
  id: string;
  title: string;
  content: string;
  wordCount: number;
  isTranslated: boolean;
}

export interface TranslationInfo {
  language: string;
  languageName: string;
  flag: string;
  progress: number; // 0-100
  isComplete: boolean;
}

export interface User {
  id: string;
  email: string;
  name: string;
}

export interface ReaderSettings {
  fontSize: number;
  theme: 'light' | 'dark' | 'sepia';
  fontFamily: string;
}

export interface AppState {
  user: User | null;
  currentBook: Book | null;
  books: Book[];
  readerSettings: ReaderSettings;
  currentView: 'login' | 'library' | 'reader';
  globalTheme: 'light' | 'dark';
}