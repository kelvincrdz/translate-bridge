import React from 'react';
import { Button } from './ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Slider } from './ui/slider';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from './ui/sheet';
import { Separator } from './ui/separator';
import { Label } from './ui/label';
import { Settings, Type, Palette, Languages, ChevronLeft, ChevronRight, ArrowLeft } from 'lucide-react';
import { TranslationDialog } from './TranslationDialog';
import { useApp } from '../context/AppContext';
import { toast } from 'sonner@2.0.3';

interface ReaderControlsProps {
  onPreviousChapter: () => void;
  onNextChapter: () => void;
  onTranslateChapter: () => void;
  onTranslateAll: () => void;
}

export function ReaderControls({ 
  onPreviousChapter, 
  onNextChapter, 
  onTranslateChapter, 
  onTranslateAll 
}: ReaderControlsProps) {
  const { state, updateReaderSettings, setCurrentView } = useApp();
  const { readerSettings } = state;

  const handleFontSizeChange = (value: number[]) => {
    updateReaderSettings({ fontSize: value[0] });
  };

  const handleThemeChange = (theme: 'light' | 'dark' | 'sepia') => {
    updateReaderSettings({ theme });
  };

  const handleFontFamilyChange = (fontFamily: string) => {
    updateReaderSettings({ fontFamily });
  };

  const handleTranslateChapter = (language: string) => {
    onTranslateChapter();
  };

  const handleTranslateAll = (language: string) => {
    onTranslateAll();
  };

  return (
    <div className="flex items-center justify-between p-4 border-t bg-card">
      <div className="flex items-center gap-2">
        <Button 
          variant="outline" 
          size="sm"
          onClick={() => setCurrentView('library')}
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Biblioteca
        </Button>
        
        <Button 
          variant="outline" 
          size="sm"
          onClick={onPreviousChapter}
          disabled={state.currentBook?.currentChapter === 0}
        >
          <ChevronLeft className="h-4 w-4 mr-2" />
          Anterior
        </Button>
        
        <Button 
          variant="outline" 
          size="sm"
          onClick={onNextChapter}
          disabled={state.currentBook && state.currentBook.currentChapter >= state.currentBook.chapters.length - 1}
        >
          Próximo
          <ChevronRight className="h-4 w-4 ml-2" />
        </Button>
      </div>

      <div className="flex items-center gap-2">
        <TranslationDialog
          title="Traduzir Capítulo"
          onTranslate={handleTranslateChapter}
        >
          <Button variant="outline" size="sm">
            <Languages className="h-4 w-4 mr-2" />
            Traduzir Capítulo
          </Button>
        </TranslationDialog>
        
        <TranslationDialog
          title="Traduzir Livro Completo"
          onTranslate={handleTranslateAll}
        >
          <Button variant="outline" size="sm">
            <Languages className="h-4 w-4 mr-2" />
            Traduzir Tudo
          </Button>
        </TranslationDialog>

        <Sheet>
          <SheetTrigger asChild>
            <Button variant="outline" size="sm">
              <Settings className="h-4 w-4 mr-2" />
              Configurações
            </Button>
          </SheetTrigger>
          <SheetContent>
            <SheetHeader>
              <SheetTitle>Configurações de Leitura</SheetTitle>
            </SheetHeader>
            
            <div className="space-y-6 mt-6">
              {/* Tamanho da Fonte */}
              <div className="space-y-3">
                <Label className="flex items-center gap-2">
                  <Type className="h-4 w-4" />
                  Tamanho da Fonte
                </Label>
                <div className="px-3">
                  <Slider
                    value={[readerSettings.fontSize]}
                    onValueChange={handleFontSizeChange}
                    max={24}
                    min={12}
                    step={1}
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-muted-foreground mt-1">
                    <span>12px</span>
                    <span>{readerSettings.fontSize}px</span>
                    <span>24px</span>
                  </div>
                </div>
              </div>

              <Separator />

              {/* Tema */}
              <div className="space-y-3">
                <Label className="flex items-center gap-2">
                  <Palette className="h-4 w-4" />
                  Tema
                </Label>
                <Select value={readerSettings.theme} onValueChange={handleThemeChange}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="light">Claro</SelectItem>
                    <SelectItem value="dark">Escuro</SelectItem>
                    <SelectItem value="sepia">Sépia</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Separator />

              {/* Fonte */}
              <div className="space-y-3">
                <Label>Família da Fonte</Label>
                <Select value={readerSettings.fontFamily} onValueChange={handleFontFamilyChange}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="serif">Serif</SelectItem>
                    <SelectItem value="sans-serif">Sans Serif</SelectItem>
                    <SelectItem value="monospace">Monospace</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </div>
  );
}