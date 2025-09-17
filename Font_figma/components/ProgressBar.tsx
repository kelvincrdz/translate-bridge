import React from 'react';
import { Progress } from './ui/progress';
import { useApp } from '../context/AppContext';

export function ProgressBar() {
  const { state } = useApp();
  const book = state.currentBook;

  if (!book) return null;

  const totalChapters = book.chapters.length;
  const currentChapter = book.currentChapter;
  const chapterProgress = (currentChapter / (totalChapters - 1)) * 100;

  return (
    <div className="px-4 py-2 border-t bg-card">
      <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
        <span>Capítulo {currentChapter + 1} de {totalChapters}</span>
        <span>{Math.round(chapterProgress)}% concluído</span>
      </div>
      <Progress value={chapterProgress} className="w-full h-2" />
    </div>
  );
}