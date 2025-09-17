import React, { useState } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
import { Button } from './ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Badge } from './ui/badge';
import { Download, FileText, Headphones, Globe, Languages, ArrowLeft, Check } from 'lucide-react';
import { Book } from '../types';
import { toast } from 'sonner@2.0.3';

interface DownloadDialogProps {
  book: Book;
  children: React.ReactNode;
}

type DownloadType = 'original' | 'partial' | 'complete';

export function DownloadDialog({ book, children }: DownloadDialogProps) {
  const [step, setStep] = useState<'selection' | 'format'>('selection');
  const [downloadType, setDownloadType] = useState<DownloadType>('original');
  const [selectedLanguage, setSelectedLanguage] = useState<string>('');
  const [isOpen, setIsOpen] = useState(false);

  const resetDialog = () => {
    setStep('selection');
    setDownloadType('original');
    setSelectedLanguage('');
  };

  const handleClose = () => {
    setIsOpen(false);
    resetDialog();
  };

  const handleTypeSelection = (type: DownloadType, language?: string) => {
    setDownloadType(type);
    if (language) {
      setSelectedLanguage(language);
    }
    setStep('format');
  };

  const handleDownload = (format: 'epub' | 'pdf' | 'audio') => {
    const formatNames = {
      epub: 'EPUB',
      pdf: 'PDF', 
      audio: 'Audiobook MP3'
    };

    let typeLabel = '';
    switch (downloadType) {
      case 'original':
        typeLabel = 'Original';
        break;
      case 'partial':
        const partialLang = book.availableTranslations.find(t => t.language === selectedLanguage);
        typeLabel = `Tradução Parcial (${partialLang?.languageName})`;
        break;
      case 'complete':
        const completeLang = book.availableTranslations.find(t => t.language === selectedLanguage);
        typeLabel = `Tradução Completa (${completeLang?.languageName})`;
        break;
    }

    // Simular download
    const element = document.createElement('a');
    const content = `Livro: ${book.title}\nAutor: ${book.author}\nTipo: ${typeLabel}\nFormato: ${formatNames[format]}`;
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(content));
    element.setAttribute('download', `${book.title}_${downloadType}.${format === 'audio' ? 'mp3' : format}`);
    element.style.display = 'none';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);

    toast.success(`Download iniciado: ${book.title} - ${typeLabel} (${formatNames[format]})`);
    handleClose();
  };

  const getAvailableLanguages = (type: DownloadType) => {
    if (type === 'partial') {
      return book.availableTranslations.filter(t => t.progress > 0);
    }
    if (type === 'complete') {
      return book.availableTranslations.filter(t => t.isComplete);
    }
    return [];
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        {children}
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Download className="h-5 w-5" />
            {step === 'selection' ? `Download - ${book.title}` : 'Escolher Formato'}
          </DialogTitle>
          <DialogDescription>
            {step === 'selection' 
              ? 'Escolha o tipo de download' 
              : 'Selecione o formato para download'
            }
          </DialogDescription>
        </DialogHeader>
        
        {step === 'selection' ? (
          <div className="space-y-3 mt-4">
            {/* Original */}
            <Button 
              variant="outline" 
              className="w-full justify-start h-auto p-4"
              onClick={() => handleTypeSelection('original')}
            >
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
                  <FileText className="h-5 w-5 text-gray-600 dark:text-gray-400" />
                </div>
                <div className="text-left">
                  <div className="font-medium">Original</div>
                  <div className="text-sm text-muted-foreground">Versão em português</div>
                </div>
              </div>
            </Button>

            {/* Traduções Parciais */}
            {book.availableTranslations.filter(t => t.progress > 0 && !t.isComplete).map((translation) => (
              <Button 
                key={`partial-${translation.language}`}
                variant="outline" 
                className="w-full justify-start h-auto p-4"
                onClick={() => handleTypeSelection('partial', translation.language)}
              >
                <div className="flex items-center gap-3 w-full">
                  <div className="h-10 w-10 rounded bg-orange-100 dark:bg-orange-900 flex items-center justify-center">
                    <Languages className="h-5 w-5 text-orange-600 dark:text-orange-400" />
                  </div>
                  <div className="text-left flex-1">
                    <div className="font-medium flex items-center gap-2">
                      <span>{translation.flag}</span>
                      <span>Tradução Parcial - {translation.languageName}</span>
                      <Badge variant="secondary" className="text-xs">
                        {translation.progress}%
                      </Badge>
                    </div>
                    <div className="text-sm text-muted-foreground">Tradução em andamento</div>
                  </div>
                </div>
              </Button>
            ))}

            {/* Traduções Completas */}
            {book.availableTranslations.filter(t => t.isComplete).map((translation) => (
              <Button 
                key={`complete-${translation.language}`}
                variant="outline" 
                className="w-full justify-start h-auto p-4"
                onClick={() => handleTypeSelection('complete', translation.language)}
              >
                <div className="flex items-center gap-3 w-full">
                  <div className="h-10 w-10 rounded bg-green-100 dark:bg-green-900 flex items-center justify-center">
                    <Globe className="h-5 w-5 text-green-600 dark:text-green-400" />
                  </div>
                  <div className="text-left flex-1">
                    <div className="font-medium flex items-center gap-2">
                      <span>{translation.flag}</span>
                      <span>Tradução Completa - {translation.languageName}</span>
                      <Check className="h-4 w-4 text-green-600" />
                    </div>
                    <div className="text-sm text-muted-foreground">Tradução finalizada</div>
                  </div>
                </div>
              </Button>
            ))}

            {book.availableTranslations.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                <Languages className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">Nenhuma tradução disponível</p>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4 mt-4">
            <Button 
              variant="ghost" 
              size="sm"
              onClick={() => setStep('selection')}
              className="self-start p-0 h-auto"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Voltar
            </Button>

            <div className="space-y-3">
              <Button 
                variant="outline" 
                className="w-full justify-start h-auto p-4"
                onClick={() => handleDownload('epub')}
              >
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
                    <FileText className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div className="text-left">
                    <div className="font-medium">EPUB</div>
                    <div className="text-sm text-muted-foreground">Formato padrão para e-readers</div>
                  </div>
                </div>
              </Button>

              <Button 
                variant="outline" 
                className="w-full justify-start h-auto p-4"
                onClick={() => handleDownload('pdf')}
              >
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded bg-red-100 dark:bg-red-900 flex items-center justify-center">
                    <FileText className="h-5 w-5 text-red-600 dark:text-red-400" />
                  </div>
                  <div className="text-left">
                    <div className="font-medium">PDF</div>
                    <div className="text-sm text-muted-foreground">Documento portátil universal</div>
                  </div>
                </div>
              </Button>

              <Button 
                variant="outline" 
                className="w-full justify-start h-auto p-4"
                onClick={() => handleDownload('audio')}
              >
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded bg-green-100 dark:bg-green-900 flex items-center justify-center">
                    <Headphones className="h-5 w-5 text-green-600 dark:text-green-400" />
                  </div>
                  <div className="text-left">
                    <div className="font-medium">Audiobook</div>
                    <div className="text-sm text-muted-foreground">Versão narrada em MP3</div>
                  </div>
                </div>
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}