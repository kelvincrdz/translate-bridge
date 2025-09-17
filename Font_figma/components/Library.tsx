import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from './ui/alert-dialog';
import { BookOpen, Download, Trash2, LogOut, User, Languages, BookOpenCheck } from 'lucide-react';
import { ImageWithFallback } from './figma/ImageWithFallback';
import { DownloadDialog } from './DownloadDialog';
import { ThemeToggle } from './ThemeToggle';
import { useApp } from '../context/AppContext';

export function Library() {
  const { state, logout, setCurrentBook, deleteBook, deleteAllBooks } = useApp();

  const handleReadBook = (book: any) => {
    setCurrentBook(book);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <BookOpen className="h-8 w-8 text-blue-600" />
            <div>
              <h1>Minha Biblioteca</h1>
              <p className="text-sm text-muted-foreground">
                {state.books.length} livros disponíveis
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <User className="h-4 w-4" />
              <span className="text-sm">{state.user?.name}</span>
            </div>
            <ThemeToggle />
            <Button variant="outline" onClick={logout}>
              <LogOut className="h-4 w-4 mr-2" />
              Sair
            </Button>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="p-6">
        {/* Actions */}
        <div className="flex justify-between items-center mb-6">
          <h2>Seus Livros</h2>
          {state.books.length > 0 && (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive" size="sm">
                  <Trash2 className="h-4 w-4 mr-2" />
                  Apagar Todos
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Tem certeza?</AlertDialogTitle>
                  <AlertDialogDescription>
                    Esta ação não pode ser desfeita. Todos os seus livros serão removidos permanentemente.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancelar</AlertDialogCancel>
                  <AlertDialogAction onClick={deleteAllBooks}>
                    Sim, apagar todos
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
        </div>

        {/* Books Grid */}
        {state.books.length === 0 ? (
          <Card className="text-center py-12">
            <CardContent>
              <BookOpen className="h-16 w-16 mx-auto mb-4 text-muted-foreground" />
              <h3>Nenhum livro encontrado</h3>
              <p className="text-muted-foreground mt-2">
                Adicione alguns livros EPUB para começar a ler
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {state.books.map((book) => (
              <Card key={book.id} className="overflow-hidden">
                <div className="aspect-[3/4] relative">
                  <ImageWithFallback
                    src={book.cover}
                    alt={book.title}
                    className="w-full h-full object-cover"
                  />
                  
                  {/* Delete button */}
                  <div className="absolute top-2 right-2">
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button variant="destructive" size="sm" className="h-8 w-8 p-0">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Remover livro</AlertDialogTitle>
                          <AlertDialogDescription>
                            Tem certeza que deseja remover "{book.title}" da sua biblioteca?
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancelar</AlertDialogCancel>
                          <AlertDialogAction onClick={() => deleteBook(book.id)}>
                            Remover
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>

                  {/* Status indicators */}
                  <div className="absolute top-2 left-2 flex flex-col gap-1">
                    {book.translationAvailable && (
                      <Badge variant="secondary" className="text-xs bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900 dark:text-blue-100 dark:border-blue-800">
                        <Languages className="h-3 w-3 mr-1" />
                        Tradução
                      </Badge>
                    )}
                    {book.progress > 0 && (
                      <Badge variant="secondary" className="text-xs bg-green-100 text-green-800 border-green-200 dark:bg-green-900 dark:text-green-100 dark:border-green-800">
                        <BookOpenCheck className="h-3 w-3 mr-1" />
                        {Math.round(book.progress)}%
                      </Badge>
                    )}
                  </div>

                  {/* Translation progress */}
                  {book.translationAvailable && book.translationProgress > 0 && (
                    <div className="absolute bottom-2 left-2 right-2">
                      <div className="bg-black/50 rounded p-2 text-white text-xs">
                        <div className="flex items-center justify-between mb-1">
                          <span className="flex items-center gap-1">
                            <Languages className="h-3 w-3" />
                            Tradução
                          </span>
                          <span>{Math.round(book.translationProgress)}%</span>
                        </div>
                        <div className="w-full bg-white/20 rounded-full h-1">
                          <div 
                            className="bg-blue-400 h-1 rounded-full transition-all"
                            style={{ width: `${book.translationProgress}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  )}
                </div>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base line-clamp-2">{book.title}</CardTitle>
                  <p className="text-sm text-muted-foreground">{book.author}</p>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="flex gap-2">
                    <Button 
                      className="flex-1"
                      onClick={() => handleReadBook(book)}
                    >
                      <BookOpen className="h-4 w-4 mr-2" />
                      Ler
                    </Button>
                    <DownloadDialog book={book}>
                      <Button variant="outline">
                        <Download className="h-4 w-4" />
                      </Button>
                    </DownloadDialog>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}