import React from 'react';
import { Button } from './ui/button';
import { Moon, Sun } from 'lucide-react';
import { useApp } from '../context/AppContext';

export function ThemeToggle() {
  const { state, toggleGlobalTheme } = useApp();

  return (
    <Button 
      variant="outline" 
      size="sm"
      onClick={toggleGlobalTheme}
      className="h-9 w-9 px-0"
    >
      {state.globalTheme === 'light' ? (
        <Moon className="h-4 w-4" />
      ) : (
        <Sun className="h-4 w-4" />
      )}
      <span className="sr-only">Alternar tema</span>
    </Button>
  );
}