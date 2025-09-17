import React, { createContext, useContext, useReducer, ReactNode } from 'react';
import { AppState, Book, User, ReaderSettings } from '../types';

interface AppContextType {
  state: AppState;
  login: (user: User) => void;
  logout: () => void;
  setCurrentView: (view: 'login' | 'library' | 'reader') => void;
  setCurrentBook: (book: Book | null) => void;
  deleteBook: (bookId: string) => void;
  deleteAllBooks: () => void;
  updateReaderSettings: (settings: Partial<ReaderSettings>) => void;
  updateBookProgress: (bookId: string, chapter: number, progress: number) => void;
  toggleGlobalTheme: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

type Action = 
  | { type: 'LOGIN'; payload: User }
  | { type: 'LOGOUT' }
  | { type: 'SET_VIEW'; payload: 'login' | 'library' | 'reader' }
  | { type: 'SET_CURRENT_BOOK'; payload: Book | null }
  | { type: 'DELETE_BOOK'; payload: string }
  | { type: 'DELETE_ALL_BOOKS' }
  | { type: 'UPDATE_READER_SETTINGS'; payload: Partial<ReaderSettings> }
  | { type: 'UPDATE_BOOK_PROGRESS'; payload: { bookId: string; chapter: number; progress: number } }
  | { type: 'TOGGLE_GLOBAL_THEME' };

const mockBooks: Book[] = [
  {
    id: '1',
    title: 'Dom Casmurro',
    author: 'Machado de Assis',
    cover: 'https://images.unsplash.com/photo-1543002588-bfa74002ed7e?w=300&h=400&fit=crop',
    currentChapter: 1,
    progress: 45,
    translationAvailable: true,
    translationProgress: 80,
    availableTranslations: [
      {
        language: 'en',
        languageName: 'Inglês',
        flag: '🇺🇸',
        progress: 100,
        isComplete: true
      },
      {
        language: 'fr',
        languageName: 'Francês',
        flag: '🇫🇷',
        progress: 75,
        isComplete: false
      },
      {
        language: 'es',
        languageName: 'Espanhol',
        flag: '🇪🇸',
        progress: 100,
        isComplete: true
      }
    ],
    chapters: [
      {
        id: '1-1',
        title: 'Capítulo I - Do título',
        content: 'Uma noite destas, vindo da cidade para o Engenho Novo, encontrei no trem da Central um rapaz aqui do bairro, que eu conheço de vista e de chapéu. Cumprimentou-me, sentou-se ao pé de mim, falou da lua e dos ministros, e acabou recitando-me versos. A viagem era curta, e os versos pode ser que não fossem inteiramente maus. Sucedeu, porém, que, como eu estava cansado, fechei os olhos três ou quatro vezes; tanto bastou para que ele interrompesse a leitura e metesse os versos no bolso.',
        wordCount: 98,
        isTranslated: true
      },
      {
        id: '1-2',
        title: 'Capítulo II - Do livro',
        content: '— Agora que expliquei o título, passo a escrever o livro. Antes disso, porém, digamos os motivos que me põem a pena na mão. Vivo só, com um criado. A casa em que moro é própria; fi-la construir de propósito, levado de um desejo tão particular que me vexa imprimi-lo, mas vá lá.',
        wordCount: 50,
        isTranslated: true
      }
    ]
  },
  {
    id: '2',
    title: 'O Cortiço',
    author: 'Aluísio Azevedo',
    cover: 'https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=300&h=400&fit=crop',
    currentChapter: 0,
    progress: 15,
    translationAvailable: true,
    translationProgress: 30,
    availableTranslations: [
      {
        language: 'en',
        languageName: 'Inglês',
        flag: '🇺🇸',
        progress: 30,
        isComplete: false
      }
    ],
    chapters: [
      {
        id: '2-1',
        title: 'Capítulo I',
        content: 'João Romão foi, dos treze aos vinte e cinco anos, empregado de um vendeiro que enriqueceu entre as quatro paredes de uma suja e obscura taverna nos refolhos do bairro do Botafogo; e tanto economizou do pouco que ganhava, que, ao sair de lá, pode meter-se num pequeno negócio de secos e molhados.',
        wordCount: 52,
        isTranslated: false
      }
    ]
  },
  {
    id: '3',
    title: 'Iracema',
    author: 'José de Alencar',
    cover: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=300&h=400&fit=crop',
    currentChapter: 0,
    progress: 0,
    translationAvailable: false,
    translationProgress: 0,
    availableTranslations: [],
    chapters: [
      {
        id: '3-1',
        title: 'I',
        content: 'Verdes mares bravios de minha terra natal, onde canta a jandaia nas frondes da carnaúba; Verdes mares, que brilhais como líquida esmeralda aos raios do sol nascente, perlongando as alvas praias ensombradas de coqueiros.',
        wordCount: 34,
        isTranslated: false
      }
    ]
  }
];

const initialState: AppState = {
  user: null,
  currentBook: null,
  books: mockBooks,
  readerSettings: {
    fontSize: 16,
    theme: 'light',
    fontFamily: 'serif'
  },
  currentView: 'login',
  globalTheme: 'light'
};

function appReducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'LOGIN':
      return {
        ...state,
        user: action.payload,
        currentView: 'library'
      };
    case 'LOGOUT':
      return {
        ...state,
        user: null,
        currentBook: null,
        currentView: 'login'
      };
    case 'SET_VIEW':
      return {
        ...state,
        currentView: action.payload
      };
    case 'SET_CURRENT_BOOK':
      return {
        ...state,
        currentBook: action.payload,
        currentView: action.payload ? 'reader' : 'library'
      };
    case 'DELETE_BOOK':
      return {
        ...state,
        books: state.books.filter(book => book.id !== action.payload),
        currentBook: state.currentBook?.id === action.payload ? null : state.currentBook
      };
    case 'DELETE_ALL_BOOKS':
      return {
        ...state,
        books: [],
        currentBook: null
      };
    case 'UPDATE_READER_SETTINGS':
      return {
        ...state,
        readerSettings: {
          ...state.readerSettings,
          ...action.payload
        }
      };
    case 'UPDATE_BOOK_PROGRESS':
      return {
        ...state,
        books: state.books.map(book => 
          book.id === action.payload.bookId 
            ? { ...book, currentChapter: action.payload.chapter, progress: action.payload.progress }
            : book
        ),
        currentBook: state.currentBook?.id === action.payload.bookId
          ? { ...state.currentBook, currentChapter: action.payload.chapter, progress: action.payload.progress }
          : state.currentBook
      };
    case 'TOGGLE_GLOBAL_THEME':
      return {
        ...state,
        globalTheme: state.globalTheme === 'light' ? 'dark' : 'light'
      };
    default:
      return state;
  }
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, initialState);

  const login = (user: User) => {
    dispatch({ type: 'LOGIN', payload: user });
  };

  const logout = () => {
    dispatch({ type: 'LOGOUT' });
  };

  const setCurrentView = (view: 'login' | 'library' | 'reader') => {
    dispatch({ type: 'SET_VIEW', payload: view });
  };

  const setCurrentBook = (book: Book | null) => {
    dispatch({ type: 'SET_CURRENT_BOOK', payload: book });
  };

  const deleteBook = (bookId: string) => {
    dispatch({ type: 'DELETE_BOOK', payload: bookId });
  };

  const deleteAllBooks = () => {
    dispatch({ type: 'DELETE_ALL_BOOKS' });
  };

  const updateReaderSettings = (settings: Partial<ReaderSettings>) => {
    dispatch({ type: 'UPDATE_READER_SETTINGS', payload: settings });
  };

  const updateBookProgress = (bookId: string, chapter: number, progress: number) => {
    dispatch({ type: 'UPDATE_BOOK_PROGRESS', payload: { bookId, chapter, progress } });
  };

  const toggleGlobalTheme = () => {
    dispatch({ type: 'TOGGLE_GLOBAL_THEME' });
  };

  return (
    <AppContext.Provider value={{
      state,
      login,
      logout,
      setCurrentView,
      setCurrentBook,
      deleteBook,
      deleteAllBooks,
      updateReaderSettings,
      updateBookProgress,
      toggleGlobalTheme
    }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}