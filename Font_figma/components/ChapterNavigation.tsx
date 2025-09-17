import React from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from './ui/sheet';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { List, BookOpen } from 'lucide-react';
import { useApp } from '../context/AppContext';

interface ChapterNavigationProps {
  onChapterSelect: (chapterIndex: number) => void;
}

export function ChapterNavigation({ onChapterSelect }: ChapterNavigationProps) {
  const { state } = useApp();
  const book = state.currentBook;

  if (!book) return null;

  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="outline" size="sm">
          <List className="h-4 w-4 mr-2" />
          Índice
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-[300px] sm:w-[400px]">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <BookOpen className="h-5 w-5" />
            {book.title}
          </SheetTitle>
        </SheetHeader>
        <ScrollArea className="h-[calc(100vh-100px)] mt-6">
          <div className="space-y-2">
            {book.chapters.map((chapter, index) => (
              <Button
                key={chapter.id}
                variant={index === book.currentChapter ? "secondary" : "ghost"}
                className="w-full justify-start h-auto p-3"
                onClick={() => onChapterSelect(index)}
              >
                <div className="text-left">
                  <div className="font-medium">{chapter.title}</div>
                  <div className="text-xs text-muted-foreground mt-1">
                    {chapter.wordCount} palavras
                  </div>
                </div>
              </Button>
            ))}
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}