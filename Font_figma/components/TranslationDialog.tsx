import React, { useState } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
import { Button } from './ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Label } from './ui/label';
import { Languages, Globe } from 'lucide-react';
import { toast } from 'sonner@2.0.3';

interface TranslationDialogProps {
  children: React.ReactNode;
  onTranslate: (targetLanguage: string) => void;
  title: string;
}

const languages = [
  { code: 'en', name: 'Inglês', flag: '🇺🇸' },
  { code: 'es', name: 'Espanhol', flag: '🇪🇸' },
  { code: 'fr', name: 'Francês', flag: '🇫🇷' },
  { code: 'de', name: 'Alemão', flag: '🇩🇪' },
  { code: 'it', name: 'Italiano', flag: '🇮🇹' },
  { code: 'ja', name: 'Japonês', flag: '🇯🇵' },
  { code: 'ko', name: 'Coreano', flag: '🇰🇷' },
  { code: 'zh', name: 'Chinês', flag: '🇨🇳' },
  { code: 'ru', name: 'Russo', flag: '🇷🇺' },
  { code: 'ar', name: 'Árabe', flag: '🇸🇦' }
];

export function TranslationDialog({ children, onTranslate, title }: TranslationDialogProps) {
  const [selectedLanguage, setSelectedLanguage] = useState<string>('');
  const [isOpen, setIsOpen] = useState(false);

  const handleTranslate = () => {
    if (!selectedLanguage) {
      toast.error('Selecione um idioma de destino');
      return;
    }

    const language = languages.find(lang => lang.code === selectedLanguage);
    onTranslate(selectedLanguage);
    toast.loading(`Traduzindo para ${language?.name}...`, { id: 'translation' });
    
    // Simular tradução
    setTimeout(() => {
      toast.success(`${title} traduzido para ${language?.name}!`, { id: 'translation' });
    }, 2000);
    
    setIsOpen(false);
    setSelectedLanguage('');
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        {children}
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Languages className="h-5 w-5" />
            {title}
          </DialogTitle>
          <DialogDescription>
            Selecione o idioma para tradução
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 mt-4">
          <div className="space-y-2">
            <Label htmlFor="language">Idioma de destino</Label>
            <Select value={selectedLanguage} onValueChange={setSelectedLanguage}>
              <SelectTrigger>
                <SelectValue placeholder="Selecione um idioma" />
              </SelectTrigger>
              <SelectContent>
                {languages.map((language) => (
                  <SelectItem key={language.code} value={language.code}>
                    <div className="flex items-center gap-2">
                      <span>{language.flag}</span>
                      <span>{language.name}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex gap-2 pt-4">
            <Button variant="outline" className="flex-1" onClick={() => setIsOpen(false)}>
              Cancelar
            </Button>
            <Button 
              className="flex-1" 
              onClick={handleTranslate}
              disabled={!selectedLanguage}
            >
              <Languages className="h-4 w-4 mr-2" />
              Traduzir
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}