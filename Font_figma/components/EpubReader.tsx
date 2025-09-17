import React, { useEffect } from 'react';
import { ScrollArea } from './ui/scroll-area';
import { ChapterNavigation } from './ChapterNavigation';
import { ReaderControls } from './ReaderControls';
import { ProgressBar } from './ProgressBar';
import { useApp } from '../context/AppContext';
import { toast } from 'sonner@2.0.3';

export function EpubReader() {
  const { state, updateBookProgress } = useApp();
  const book = state.currentBook;
  const { readerSettings } = state;

  useEffect(() => {
    if (book) {
      updateBookProgress(book.id, book.currentChapter, (book.currentChapter / (book.chapters.length - 1)) * 100);
    }
  }, [book?.currentChapter, book?.id, book?.chapters.length, updateBookProgress]);

  if (!book) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p>Nenhum livro selecionado</p>
      </div>
    );
  }

  const currentChapter = book.chapters[book.currentChapter];

  const handleChapterSelect = (chapterIndex: number) => {
    if (book) {
      updateBookProgress(book.id, chapterIndex, (chapterIndex / (book.chapters.length - 1)) * 100);
    }
  };

  const handlePreviousChapter = () => {
    if (book && book.currentChapter > 0) {
      handleChapterSelect(book.currentChapter - 1);
    }
  };

  const handleNextChapter = () => {
    if (book && book.currentChapter < book.chapters.length - 1) {
      handleChapterSelect(book.currentChapter + 1);
    }
  };

  const handleTranslateChapter = () => {
    // Simulação de tradução
    toast.loading('Traduzindo capítulo...', { id: 'translate-chapter' });
    setTimeout(() => {
      toast.success('Capítulo traduzido!', { id: 'translate-chapter' });
    }, 2000);
  };

  const handleTranslateAll = () => {
    // Simulação de tradução completa
    toast.loading('Traduzindo livro completo...', { id: 'translate-all' });
    setTimeout(() => {
      toast.success('Livro completo traduzido!', { id: 'translate-all' });
    }, 3000);
  };

  const getThemeClasses = () => {
    switch (readerSettings.theme) {
      case 'dark':
        return 'bg-gray-900 text-gray-100';
      case 'sepia':
        return 'bg-amber-50 text-amber-900';
      default:
        return 'bg-white text-gray-900';
    }
  };

  const getFontFamily = () => {
    switch (readerSettings.fontFamily) {
      case 'sans-serif':
        return 'font-sans';
      case 'monospace':
        return 'font-mono';
      default:
        return 'font-serif';
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b bg-card px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg">{book.title}</h1>
            <p className="text-sm text-muted-foreground">{book.author}</p>
          </div>
          <ChapterNavigation onChapterSelect={handleChapterSelect} />
        </div>
      </header>

      {/* Reading Area */}
      <div className="flex-1 flex flex-col">
        <ScrollArea className="flex-1">
          <div className={`min-h-full ${getThemeClasses()}`}>
            <div className="max-w-4xl mx-auto px-8 py-12">
              <article 
                className={`prose prose-lg max-w-none ${getFontFamily()}`}
                style={{ fontSize: `${readerSettings.fontSize}px` }}
              >
                <header className="mb-8">
                  <h1 className="mb-2">{currentChapter.title}</h1>
                  <div className="text-sm text-muted-foreground">
                    Capítulo {book.currentChapter + 1} de {book.chapters.length}
                  </div>
                </header>
                
                <div
                  className="chapter-content prose prose-lg max-w-none leading-relaxed text-justify"
                  style={{ 
                    hyphens: 'auto',
                    wordSpacing: '0.05em',
                    lineHeight: '1.7'
                  }}
                  // Renderizar HTML do EPUB; pressupõe conteúdo já confiável/sanitizado no backend
                  dangerouslySetInnerHTML={{ __html: currentChapter.content }}
                />
              </article>
            </div>
          </div>
        </ScrollArea>
        
        <ProgressBar />
        
        <ReaderControls
          onPreviousChapter={handlePreviousChapter}
          onNextChapter={handleNextChapter}
          onTranslateChapter={handleTranslateChapter}
          onTranslateAll={handleTranslateAll}
        />
      </div>
    </div>
  );
}